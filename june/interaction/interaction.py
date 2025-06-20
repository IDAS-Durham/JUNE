import numpy as np
from random import random
from typing import List, Dict
from collections import defaultdict
from june.mpi_wrapper import mpi_comm, mpi_rank, mpi_available, mpi_size

from june.global_context import GlobalContext
from june.groups.group.interactive import InteractiveGroup
from june.groups import InteractiveSchool
from june.records import Record
from june import paths

default_sector_beta_filename = (
    paths.configs_path / "defaults/interaction/sector_beta.yaml"
)


class Interaction:
    """
    Class to handle interaction in groups.

    Parameters
    ----------
    alpha_physical
        Scaling factor for physical contacts, an alpha_physical factor of 1, means that physical
        contacts count as much as non-physical contacts.
    beta
        dictionary mapping the group specs with their contact intensities
    contact_matrices
        dictionary mapping the group specs with their contact matrices
    """

    def __init__(
        self, alpha_physical: float, betas: Dict[str, float], contact_matrices: dict
    ):
        self.alpha_physical = alpha_physical
        self.betas = betas or {}
        contact_matrices = contact_matrices or {}
        self.contact_matrices = self.get_raw_contact_matrices(
            input_contact_matrices=contact_matrices,
            groups=self.betas.keys(),
            alpha_physical=alpha_physical,
        )
        self.beta_reductions = {}
        self.current_time = None  # Track current simulation time for isolation checks
        
        # Counter for initial infected IDs in transmission chains
        self.initial_infected_transmission_counts = defaultdict(int)
        self._initial_infected_ids = set()  # Cache for initial infected IDs
        self._initial_infected_ids_loaded = False
        
        # Timestep and cumulative tracking
        self.previous_transmission_counts = defaultdict(int)  # For calculating timestep differences
        self.timestep_count = 0  # Track simulation timesteps
        self.cumulative_global_stats = None  # Cache for global cumulative stats
        
        # Debug tracking for cross-rank infector detection
        self.debug_cross_rank_infectors = defaultdict(set)  # Track which ranks each infector appears on
        self.debug_timestep_infectors = defaultdict(lambda: defaultdict(int))  # Track infectors per timestep per rank
        self.debug_infector_venues = defaultdict(list)  # Track venue details for each infector
    
    def _load_initial_infected_ids(self):
        """
        Load initial infected IDs from infection seeds in the epidemiology module.
        This method tries to access the initial infected IDs through the global context.
        
        If IDs have already been loaded (e.g., from checkpoint restoration), this method
        will not override them.
        """
        if self._initial_infected_ids_loaded and len(self._initial_infected_ids) > 0:
            # Already loaded (possibly from checkpoint) - don't override
            return
        
        try:
            # Try to get epidemiology from global context
            from june.global_context import GlobalContext
            simulator = GlobalContext.get_simulator()
            
            if simulator and hasattr(simulator, 'epidemiology') and simulator.epidemiology:
                epidemiology = simulator.epidemiology
                
                # Check if epidemiology has infection_seeds
                if hasattr(epidemiology, 'infection_seeds') and epidemiology.infection_seeds:
                    # Handle both single InfectionSeed and InfectionSeeds (collection)
                    if hasattr(epidemiology.infection_seeds, 'get_all_initial_infected_ids'):
                        # InfectionSeeds collection
                        self._initial_infected_ids = epidemiology.infection_seeds.get_all_initial_infected_ids()
                    elif hasattr(epidemiology.infection_seeds, 'initial_infected_ids'):
                        # Single InfectionSeed

                        self._initial_infected_ids = epidemiology.infection_seeds.initial_infected_ids.copy()
                    
                    #print(f"[Rank {mpi_rank}] Interaction: Loaded {len(self._initial_infected_ids)} initial infected IDs")
                else:
                    print(f"[Rank {mpi_rank}] Interaction: No infection_seeds found in epidemiology")
            else:
                print(f"[Rank {mpi_rank}] Interaction: No epidemiology found in simulator")
                
        except Exception as e:
            print(f"[Rank {mpi_rank}] Interaction: Error loading initial infected IDs: {e}")
    
    def _get_transmission_statistics(self):
        """
        Get comprehensive transmission statistics for initial infected IDs.
        
        Returns
        -------
        dict
            Dictionary with transmission statistics
        """
        self._load_initial_infected_ids()
        
        total_initial_infected = len(self._initial_infected_ids)
        initial_infected_who_transmitted = len(self.initial_infected_transmission_counts)
        total_secondary_infections = sum(self.initial_infected_transmission_counts.values())
        
        stats = {
            'total_initial_infected': total_initial_infected,
            'initial_infected_who_transmitted': initial_infected_who_transmitted,
            'total_secondary_infections_by_initial': total_secondary_infections,
            'transmission_counts': dict(self.initial_infected_transmission_counts),
            'average_secondary_infections_per_transmitter': (
                total_secondary_infections / initial_infected_who_transmitted 
                if initial_infected_who_transmitted > 0 else 0
            ),
            'proportion_initial_who_transmitted': (
                initial_infected_who_transmitted / total_initial_infected 
                if total_initial_infected > 0 else 0
            )
        }
        
        return stats
    
    def _get_timestep_transmission_counts(self):
        """
        Get transmission counts for the current timestep only.
        
        Returns
        -------
        dict
            Dictionary mapping initial infected ID to count of secondary infections in this timestep
        """
        timestep_counts = {}
        for person_id, cumulative_count in self.initial_infected_transmission_counts.items():
            previous_count = self.previous_transmission_counts.get(person_id, 0)
            timestep_count = cumulative_count - previous_count
            if timestep_count > 0:
                timestep_counts[person_id] = timestep_count
        return timestep_counts
    
    def _get_global_transmission_statistics(self):
        """
        Get global transmission statistics across all MPI ranks.
        
        Returns
        -------
        dict
            Dictionary with global transmission statistics
        """
        # Get local statistics
        local_stats = self._get_transmission_statistics()
        
        if not mpi_available:
            # In non-MPI mode, local stats are global stats
            return {
                'global': local_stats,
                'by_rank': {0: local_stats}
            }
        
        # Gather statistics from all ranks
        all_rank_stats = mpi_comm.allgather(local_stats)
        
        # Aggregate global statistics
        global_transmission_counts = defaultdict(int)
        global_initial_infected = set()
        
        # First, collect ALL initial infected IDs from all ranks (not just transmitters)
        all_rank_initial_ids = mpi_comm.allgather(list(self._initial_infected_ids))
        for rank_initial_ids in all_rank_initial_ids:
            global_initial_infected.update(rank_initial_ids)
        
        # Then, aggregate transmission counts from transmitters only
        global_transmitter_ids = set()  # Track unique transmitter IDs to avoid double counting
        for rank_stats in all_rank_stats:
            for person_id, count in rank_stats['transmission_counts'].items():
                global_transmission_counts[person_id] += count
                global_transmitter_ids.add(person_id)  # Track unique transmitters
        
        # Calculate global aggregated statistics
        total_global_initial_infected = len(global_initial_infected)  # ALL initial infected
        global_initial_infected_who_transmitted = len(global_transmitter_ids)  # Unique transmitters only
        total_global_secondary_infections = sum(global_transmission_counts.values())
        
        global_stats = {
            'total_initial_infected': total_global_initial_infected,
            'initial_infected_who_transmitted': global_initial_infected_who_transmitted,
            'total_secondary_infections_by_initial': total_global_secondary_infections,
            'transmission_counts': dict(global_transmission_counts),
            'average_secondary_infections_per_initial_infected': (
                total_global_secondary_infections / total_global_initial_infected
                if total_global_initial_infected > 0 else 0
            ),
            'average_secondary_infections_per_transmitter': (
                total_global_secondary_infections / global_initial_infected_who_transmitted 
                if global_initial_infected_who_transmitted > 0 else 0
            ),
            'proportion_initial_who_transmitted': (
                global_initial_infected_who_transmitted / total_global_initial_infected 
                if total_global_initial_infected > 0 else 0
            )
        }
        
        # Create rank-specific stats dictionary
        by_rank_stats = {}
        for rank, rank_stats in enumerate(all_rank_stats):
            by_rank_stats[rank] = rank_stats
        
        return {
            'global': global_stats,
            'by_rank': by_rank_stats
        }
    
    def _get_timestep_global_statistics(self):
        """
        Get global transmission statistics for the current timestep only.
        
        Returns
        -------
        dict
            Dictionary with global timestep transmission statistics
        """
        # Get local timestep counts
        local_timestep_counts = self._get_timestep_transmission_counts()
        
        if not mpi_available:
            # In non-MPI mode, local stats are global stats
            total_timestep_transmissions = sum(local_timestep_counts.values())
            return {
                'global': {
                    'timestep_transmission_counts': local_timestep_counts,
                    'total_timestep_transmissions': total_timestep_transmissions,
                    'transmitters_this_timestep': len(local_timestep_counts)
                },
                'by_rank': {0: {
                    'timestep_transmission_counts': local_timestep_counts,
                    'total_timestep_transmissions': total_timestep_transmissions,
                    'transmitters_this_timestep': len(local_timestep_counts)
                }}
            }
        
        # Gather timestep counts from all ranks
        all_rank_timestep_counts = mpi_comm.allgather(local_timestep_counts)
        
        # Aggregate global timestep statistics
        global_timestep_counts = defaultdict(int)
        for rank_counts in all_rank_timestep_counts:
            for person_id, count in rank_counts.items():
                global_timestep_counts[person_id] += count
        
        total_global_timestep_transmissions = sum(global_timestep_counts.values())
        
        global_timestep_stats = {
            'timestep_transmission_counts': dict(global_timestep_counts),
            'total_timestep_transmissions': total_global_timestep_transmissions,
            'transmitters_this_timestep': len(global_timestep_counts)
        }
        
        # Create rank-specific timestep stats
        by_rank_timestep_stats = {}
        for rank, rank_counts in enumerate(all_rank_timestep_counts):
            total_rank_timestep_transmissions = sum(rank_counts.values())
            by_rank_timestep_stats[rank] = {
                'timestep_transmission_counts': rank_counts,
                'total_timestep_transmissions': total_rank_timestep_transmissions,
                'transmitters_this_timestep': len(rank_counts)
            }
        
        return {
            'global': global_timestep_stats,
            'by_rank': by_rank_timestep_stats
        }
    
    def print_transmission_statistics(self):
        """
        Print comprehensive transmission statistics including timestep, cumulative, and global data.
        """
        # Increment timestep counter
        self.timestep_count += 1
        
        # Get timestep and global statistics
        timestep_global_stats = self._get_timestep_global_statistics()
        cumulative_global_stats = self._get_global_transmission_statistics()
        
        # Only print from rank 0 to avoid duplicate output
        if mpi_rank == 0:
            print(f"\n{'='*80}")
            print(f"TRANSMISSION STATISTICS - TIMESTEP {self.timestep_count}")
            print(f"{'='*80}")
            
            # GLOBAL STATISTICS SECTION
            print(f"\n{'='*30} GLOBAL SUMMARY {'='*30}")
            
            # Global timestep statistics
            global_timestep = timestep_global_stats['global']
            print(f"\n--- THIS TIMESTEP (Global) ---")
            print(f"New transmissions by initial infected: {global_timestep['total_timestep_transmissions']}")
            print(f"Initial infected who transmitted this timestep: {global_timestep['transmitters_this_timestep']}")
            
            # Global cumulative statistics
            global_cumulative = cumulative_global_stats['global']
            print(f"\n--- CUMULATIVE (Global) ---")
            print(f"Total initial infected: {global_cumulative['total_initial_infected']}")
            print(f"Initial infected who have transmitted: {global_cumulative['initial_infected_who_transmitted']}")
            print(f"Total secondary infections by initial infected: {global_cumulative['total_secondary_infections_by_initial']}")
            print(f"Average secondary infections per initial infected (R0): {global_cumulative['average_secondary_infections_per_initial_infected']:.2f}")
            print(f"Average secondary infections per transmitter: {global_cumulative['average_secondary_infections_per_transmitter']:.2f}")
            print(f"Proportion of initial infected who transmitted: {global_cumulative['proportion_initial_who_transmitted']:.2%}")
            
            # RANK-BY-RANK BREAKDOWN
            print(f"\n{'='*25} BY RANK BREAKDOWN {'='*25}")
            
            # Debug: Calculate totals from rank data
            total_rank_transmissions = 0
            total_rank_transmitters = 0
            
            for rank in sorted(timestep_global_stats['by_rank'].keys()):
                rank_timestep = timestep_global_stats['by_rank'][rank]
                rank_cumulative = cumulative_global_stats['by_rank'][rank]
                
                print(f"\n--- RANK {rank} ---")
                print(f"  Timestep: {rank_timestep['total_timestep_transmissions']} new transmissions, "
                      f"{rank_timestep['transmitters_this_timestep']} transmitters")
                print(f"  Cumulative: {rank_cumulative['total_secondary_infections_by_initial']} total transmissions, "
                      f"{rank_cumulative['initial_infected_who_transmitted']} transmitters, "
                      f"avg: {rank_cumulative['average_secondary_infections_per_transmitter']:.2f}")
                
                total_rank_transmissions += rank_cumulative['total_secondary_infections_by_initial']
                total_rank_transmitters += rank_cumulative['initial_infected_who_transmitted']
            
            # TOP TRANSMITTERS (Global, cumulative)
            if global_cumulative['transmission_counts']:
                print(f"\n{'='*20} TOP TRANSMITTERS (Cumulative Global) {'='*20}")
                sorted_transmitters = sorted(
                    global_cumulative['transmission_counts'].items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:10]
                
                for person_id, count in sorted_transmitters:
                    print(f"  Person {person_id}: {count} secondary infections")
            
            # TOP TRANSMITTERS THIS TIMESTEP (Global)
            if global_timestep['timestep_transmission_counts']:
                print(f"\n{'='*15} TOP TRANSMITTERS THIS TIMESTEP (Global) {'='*15}")
                sorted_timestep_transmitters = sorted(
                    global_timestep['timestep_transmission_counts'].items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:5]
                
                for person_id, count in sorted_timestep_transmitters:
                    print(f"  Person {person_id}: {count} new secondary infections")
            
            print(f"\n{'='*80}\n")
        
        # Update previous counts for next timestep calculation
        self.previous_transmission_counts = self.initial_infected_transmission_counts.copy()
    

    @classmethod
    def from_file(cls) -> "Interaction":
        """
        Load an Interaction instance using the global disease configuration.

        Returns
        -------
        Interaction
            The interaction object initialized from the global context.
        """
        # Retrieve the global disease configuration
        disease_config = GlobalContext.get_disease_config()

        # Use the pre-extracted attributes from DiseaseConfig
        interaction = cls(
            alpha_physical=disease_config.interaction_manager.alpha_physical,
            betas=disease_config.interaction_manager.betas,
            contact_matrices=disease_config.interaction_manager.contact_matrices,
        )

        return interaction

    def get_raw_contact_matrices(
        self, groups: List[str], input_contact_matrices: dict, alpha_physical: float
    ):
        """
        Processes the input data regarding to contacts to construct the contact matrix used in the interaction.
        In particular, given a contact matrix, a matrix of physical contact ratios, and the physical contact weighting
        (alpha_physical) constructs the contact matrix via:
        $ contact_matrix = contact_matrix * (1 + (alpha_physical - 1) * physical_ratios) $

        Parameters
        ----------
        groups
            a list of group names that will be handled by the interaction
        input_contact_data
            configuration regarding contact matrices and physical contacts
        alpha_physical
            The relative weight of physical conctacts respect o non-physical ones.
        """
        contact_matrices = {}
        for group in groups:
            # school is a special case.
            contact_data = input_contact_matrices.get(group, {})
            contact_matrix = np.array(contact_data.get("contacts", [[1]]))
            proportion_physical = np.array(
                contact_data.get("proportion_physical", [[0]])
            )
            characteristic_time = contact_data.get("characteristic_time", 8)
            if group == "school":
                contact_matrix = InteractiveSchool.get_raw_contact_matrix(
                    contact_matrix=contact_matrix,
                    proportion_physical=proportion_physical,
                    alpha_physical=alpha_physical,
                    characteristic_time=characteristic_time,
                )
            else:
                contact_matrix = InteractiveGroup.get_raw_contact_matrix(
                    contact_matrix=contact_matrix,
                    proportion_physical=proportion_physical,
                    alpha_physical=alpha_physical,
                    characteristic_time=characteristic_time,
                )
            contact_matrices[group] = contact_matrix
        return contact_matrices

    def _get_interactive_group_beta(self, interactive_group):
        """Get processed beta for an interactive group, passing current time for household isolation checks."""
        # Check if this is a household group that supports isolation detection
        if hasattr(interactive_group, 'has_isolating_residents'):
            return interactive_group.get_processed_beta(
                betas=self.betas, 
                beta_reductions=self.beta_reductions,
                current_time=self.current_time
            )
        else:
            # Standard beta calculation for non-household groups
            return interactive_group.get_processed_beta(
                betas=self.betas, beta_reductions=self.beta_reductions
            )

    def create_infector_tensor(
        self,
        infectors_per_infection_per_subgroup,
        subgroup_sizes,
        contact_matrix,
        beta,
        delta_time,
    ):
        ret = {}
        for inf_id in infectors_per_infection_per_subgroup:
            infector_matrix = np.zeros_like(contact_matrix, dtype=np.float64)
            for subgroup_id in infectors_per_infection_per_subgroup[inf_id]:
                subgroup_trans_prob = sum(
                    infectors_per_infection_per_subgroup[inf_id][subgroup_id][
                        "trans_probs"
                    ]
                )
                for i in range(len(contact_matrix)):
                    subgroup_size = subgroup_sizes[subgroup_id]
                    if i == subgroup_id:
                        subgroup_size = max(1, subgroup_size - 1)
                    infector_matrix[i, subgroup_id] = (
                        contact_matrix[i, subgroup_id]
                        * subgroup_trans_prob
                        / subgroup_size
                    )
            ret[inf_id] = infector_matrix * beta * delta_time
        return ret
    
    def _count_initial_infected_transmissions(self, to_blame_ids, group=None):
        """
        Count how many times each initial infected ID appears in to_blame_ids.
        This tracks secondary infections caused by initially infected individuals.
        
        Parameters
        ----------
        to_blame_ids : list
            List of person IDs who caused infections in this timestep
        group : InteractiveGroup, optional
            The group where these transmissions occurred (for venue tracking)
        """
        # Ensure we have loaded the initial infected IDs
        self._load_initial_infected_ids()

        # Count occurrences of each initial infected ID in to_blame_ids
        for infector_id in to_blame_ids:
            if infector_id in self._initial_infected_ids:
                self.initial_infected_transmission_counts[infector_id] += 1
                
                # Debug: Track which rank this infector appears on
                self.debug_cross_rank_infectors[infector_id].add(mpi_rank)
                self.debug_timestep_infectors[self.timestep_count][infector_id] += 1
                
                # Debug: Track venue details for this transmission
                venue_info = {
                    'timestep': self.timestep_count,
                    'rank': mpi_rank,
                    'infector_id': infector_id,
                    'group_spec': group.spec if group else 'unknown',
                    'group_id': group.id if group else 'unknown',
                    'super_area_name': group.super_area.name if group and hasattr(group, 'super_area') else 'unknown',
                    'region_name': group.super_area.region.name if group and hasattr(group, 'super_area') and hasattr(group.super_area, 'region') else 'unknown'
                }
                self.debug_infector_venues[infector_id].append(venue_info)
    
    def time_step_for_group(
        self,
        group: InteractiveGroup,
        delta_time: float,
        people_from_abroad: dict = None,
        record: Record = None,
    ):
        """
        Runs an interaction time step for the given interactive group.
        """
        interactive_group = group.get_interactive_group(
            people_from_abroad=people_from_abroad
        )
        
        if not interactive_group.must_timestep:
            return [], [], interactive_group.size
        
        infected_ids = []
        infection_ids = []
        to_blame_subgroups = []

        # Process the group's beta and contact matrix
        beta = self._get_interactive_group_beta(interactive_group)
        contact_matrix_raw = self.contact_matrices[group.spec]
        contact_matrix = interactive_group.get_processed_contact_matrix(
            contact_matrix_raw
        )

        # Create the infector tensor
        infector_tensor = self.create_infector_tensor(
            interactive_group.infectors_per_infection_per_subgroup,
            interactive_group.subgroup_sizes,
            contact_matrix,
            beta,
            delta_time,
        )

        # Process susceptibles and compute infections
        for (
            susceptible_subgroup_id,
            subgroup_susceptibles,
        ) in interactive_group.susceptibles_per_subgroup.items():
            (
                new_infected_ids,
                new_infection_ids,
                new_to_blame_subgroups,
            ) = self._time_step_for_subgroup(
                infector_tensor=infector_tensor,
                susceptible_subgroup_id=susceptible_subgroup_id,
                subgroup_susceptibles=subgroup_susceptibles,
            )
            infected_ids += new_infected_ids
            infection_ids += new_infection_ids
            to_blame_subgroups += new_to_blame_subgroups

        # Determine the individuals responsible for infections
        to_blame_ids = self._blame_individuals(
            to_blame_subgroups,
            infection_ids,
            interactive_group.infectors_per_infection_per_subgroup,
        )
        
        # Count transmissions by initial infected IDs
        self._count_initial_infected_transmissions(to_blame_ids, group)

        # Log infections if a record is provided
        if record:
            self._log_infections_to_record(
                infected_ids=infected_ids,
                infection_ids=infection_ids,
                to_blame_ids=to_blame_ids,
                record=record,
                group=group,
            )

        return infected_ids, infection_ids, interactive_group.size

    
    def _time_step_for_subgroup(
        self, infector_tensor, susceptible_subgroup_id, subgroup_susceptibles
    ):
        """
        Time step for one susceptible subgroup. We first compute the combined
        effective transmission probability of all the subgroups that contain infected
        people, and then run this effective transmission over the susceptible subgroup,
        to check who got infected.

        Parameters
        ----------
        """
        new_infected_ids = []
        new_infection_ids = []
        new_to_blame_subgroups = []
        infection_ids = list(infector_tensor.keys())
        for susceptible_id, susceptibility_dict in subgroup_susceptibles.items():
            infection_transmission_parameters = []
            for infection_id in infector_tensor:
                susceptibility = susceptibility_dict.get(infection_id, 1.0)
                infector_transmission = infector_tensor[infection_id][
                    susceptible_subgroup_id
                ].sum()
                infection_transmission_parameters.append(
                    infector_transmission * susceptibility
                )
            infection_id = self._gets_infected(
                np.array(infection_transmission_parameters), infection_ids
            )
            if infection_id is not None:
                new_infected_ids.append(susceptible_id)
                new_infection_ids.append(infection_id)
                new_to_blame_subgroups.append(
                    self._blame_subgroup(
                        infector_tensor[infection_id][susceptible_subgroup_id]
                    )
                )
        return new_infected_ids, new_infection_ids, new_to_blame_subgroups


    def _gets_infected(self, infection_transmission_parameters, infection_ids):
        total_exp = infection_transmission_parameters.sum()
        if random() < 1 - np.exp(-total_exp):
            if len(infection_ids) == 1:
                return infection_ids[0]
            return np.random.choice(
                infection_ids, p=infection_transmission_parameters / total_exp
            )

    def _blame_subgroup(self, vector):
        probs = vector / vector.sum()
        return np.random.choice(len(vector), p=probs)

    def _blame_individuals(
        self, to_blame_subgroups, infection_ids, infectors_per_infection_per_subgroup
    ):
        ret = []
        for infection_id, subgroup in zip(infection_ids, to_blame_subgroups):
            candidates_ids = infectors_per_infection_per_subgroup[infection_id][
                subgroup
            ]["ids"]
            candidates_probs = np.array(
                infectors_per_infection_per_subgroup[infection_id][subgroup][
                    "trans_probs"
                ]
            )
            candidates_probs /= candidates_probs.sum()
            ret.append(np.random.choice(candidates_ids, p=candidates_probs))
        return ret

    def _log_infections_to_record(
        self,
        infected_ids: list,
        infection_ids: list,
        to_blame_ids: list,
        group: InteractiveGroup,
        record: Record,
    ):
        """
        Logs new infected people to record, and their infectors.
        """
        record.accumulate(
            table_name="infections",
            location_spec=group.spec,
            location_id=group.id,
            region_name=group.super_area.region.name,
            infected_ids=infected_ids,
            infection_ids=infection_ids,
            infector_ids=to_blame_ids,
        )