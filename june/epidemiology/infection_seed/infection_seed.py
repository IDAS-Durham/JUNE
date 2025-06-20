import numpy as np
import sys
import pandas as pd
from random import random
import datetime
import logging
import csv
import os
from collections import defaultdict
from typing import List, Optional

from june.records import Record
from june.epidemiology.infection import InfectionSelector
from june.epidemiology.epidemiology import Epidemiology
from june.utils import parse_age_probabilities
from june.mpi_wrapper import mpi_rank, mpi_comm

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from june.world import World

seed_logger = logging.getLogger("seed")


class InfectionSeed:
    """
    The infection seed takes a dataframe of cases to seed per capita, per age, and per region.
    There are multiple ways to construct the dataframe, from deaths, tests, etc. Each infection seed
    is associated to one infection selector, so if we run multiple infection types, there could be multiple infection
    seeds for each infection type.
    """

    def __init__(
        self,
        world: "World",
        infection_selector: InfectionSelector,
        daily_cases_per_capita_per_age_per_region: pd.DataFrame,
        seed_past_infections: bool = True,
        seed_strength=1.0,
        account_secondary_infections=False,
    ):
        """
        Class that generates the seed for the infection.

        Parameters
        ----------
        world:
            world to infect
        infection_selector:
            selector to generate infections
        daily_cases_per_capita_per_region:
            Double indexed dataframe. First index: date, second index: age in brackets "0-100",
            columns: region names, use "all" as placeholder for whole England.
            Example:
                date,age,North East,London
                2020-07-01,0-100,0.05,0.1
        seed_past_infections:
            whether to seed infections that started past the initial simulation point.
        """
        self.world = world
        self.infection_selector = infection_selector
        self.daily_cases_per_capita_per_age_per_region = self._parse_input_dataframe(
            df=daily_cases_per_capita_per_age_per_region, seed_strength=seed_strength
        )
        self.min_date = (
            self.daily_cases_per_capita_per_age_per_region.index.get_level_values(
                "date"
            ).min()
        )
        self.max_date = (
            self.daily_cases_per_capita_per_age_per_region.index.get_level_values(
                "date"
            ).max()
        )
        self.dates_seeded = set()
        self.past_infections_seeded = not (seed_past_infections)
        self.seed_past_infections = seed_past_infections
        self.seed_strength = seed_strength
        self.account_secondary_infections = account_secondary_infections
        self.last_seeded_cases = defaultdict(int)
        self.current_seeded_cases = defaultdict(int)
        self.initial_infected_ids = set()

    def _parse_input_dataframe(self, df, seed_strength=1.0):
        """
        Parses ages by expanding the intervals.
        """
        multi_index = pd.MultiIndex.from_product(
            [df.index.get_level_values("date").unique(), range(0, 100)],
            names=["date", "age"],
        )
        ret = pd.DataFrame(index=multi_index, columns=df.columns, dtype=float)
        for date in df.index.get_level_values("date"):
            for region in df.loc[date].columns:
                cases_per_age = parse_age_probabilities(
                    df.loc[date, region].to_dict(), fill_value=0.0
                )
                ret.loc[date, region] = np.array(cases_per_age)
        ret *= seed_strength
        return ret

    @classmethod
    def from_global_age_profile(
        cls,
        world: "World",
        infection_selector: InfectionSelector,
        daily_cases_per_region: pd.DataFrame,
        seed_past_infections: bool,
        seed_strength: float = 1.0,
        age_profile: Optional[dict] = None,
        account_secondary_infections=False,
    ):
        """
        seed_strength:
            float that controls the strength of the seed
        age_profile:
            dictionary with weight on age groups. Example:
            age_profile = {'0-20': 0., '21-50':1, '51-100':0.}
            would only infect people aged between 21 and 50
        """
        if age_profile is None:
            age_profile = {"0-100": 1.0}
        multi_index = pd.MultiIndex.from_product(
            [daily_cases_per_region.index.values, age_profile.keys()],
            names=["date", "age"],
        )
        df = pd.DataFrame(
            index=multi_index, columns=daily_cases_per_region.columns, dtype=float
        )
        for region in daily_cases_per_region.columns:
            for age_key, age_value in age_profile.items():
                df.loc[(daily_cases_per_region.index, age_key), region] = (
                    age_value * daily_cases_per_region[region].values
                )
        return cls(
            world=world,
            infection_selector=infection_selector,
            daily_cases_per_capita_per_age_per_region=df,
            seed_past_infections=seed_past_infections,
            seed_strength=seed_strength,
            account_secondary_infections=account_secondary_infections,
        )

    @classmethod
    def from_uniform_cases(
        cls,
        world: "World",
        infection_selector: InfectionSelector,
        cases_per_capita: float,
        date: str,
        seed_past_infections,
        seed_strength=1.0,
        account_secondary_infections=False,
    ):
        date = pd.to_datetime(date)
        mi = pd.MultiIndex.from_product([[date], ["0-100"]], names=["date", "age"])
        df = pd.DataFrame(index=mi, columns=["all"])
        df[:] = cases_per_capita

        infection_seed = cls(world=world,
            infection_selector=infection_selector,
            daily_cases_per_capita_per_age_per_region=df,
            seed_past_infections=seed_past_infections,
            seed_strength=seed_strength,
            account_secondary_infections=account_secondary_infections,)
        
        # World and Infection Selector Information
        print("=== Infection Seed Overview ===")
        print(f"World ID (or description): {infection_seed.world}")
        print(f"Infection Selector Class: {infection_seed.infection_selector.__class__.__name__}")

        # Seeding Dates and Parameters
        print("\n=== Seeding Dates and Parameters ===")
        print(f"Start Date of Seeding: {infection_seed.min_date}")
        print(f"End Date of Seeding: {infection_seed.max_date}")
        print(f"Seed Past Infections: {infection_seed.seed_past_infections}")
        print(f"Seed Strength: {infection_seed.seed_strength}")
        print(f"Account Secondary Infections: {infection_seed.account_secondary_infections}")

        # Seeded Cases Tracking
        print("\n=== Seeded Cases Tracking ===")
        print(f"Dates Seeded: {infection_seed.dates_seeded}")
        print("Last Seeded Cases:")
        for age_group, count in infection_seed.last_seeded_cases.items():
            print(f"  Age Group {age_group}: {count} cases")

        print("Current Seeded Cases:")
        for age_group, count in infection_seed.current_seeded_cases.items():
            print(f"  Age Group {age_group}: {count} cases")

        return infection_seed

    def infect_person(self, person, time, record):
        self.infection_selector.infect_person_at_time(person=person, time=time)
        self.initial_infected_ids.add(person.id)

        if record:
            record.accumulate(
                table_name="infections",
                location_spec="infection_seed",
                region_name=person.super_area.region.name,
                location_id=0,
                infected_ids=[person.id],
                infector_ids=[person.id],
                infection_ids=[person.infection.infection_id()],
            ) 

    def infect_super_area(
        self, super_area, cases_per_capita_per_age, time, record=None
    ):
        print(f"\n=== Infecting Super Area: {super_area.name} ===")
        
        people = super_area.people
        infection_id = self.infection_selector.infection_class.infection_id()
        n_people_by_age = defaultdict(int)
        susceptible_people_by_age = defaultdict(list)

        # Count total people and susceptible people by age
        for person in people:
            n_people_by_age[person.age] += 1
            if person.immunity.get_susceptibility(infection_id) > 0:
                susceptible_people_by_age[person.age].append(person)

        print(f"Total People in Super Area: {len(people)}")
        total_susceptible = sum(len(susceptible) for susceptible in susceptible_people_by_age.values())
        print(f"Total Susceptible People: {total_susceptible}")
   
        # Prepare to track infected individuals
        infected_summary = []  # Stores tuples of (person_id, person_age, symptoms)
        total_infected = 0

        # Infect susceptible people based on probability
        for age, susceptible in susceptible_people_by_age.items():
            rescaling = n_people_by_age[age] / len(susceptible_people_by_age[age])
            if rescaling != 1:  # Print only if rescaling is not 1
                print(f"\nAge Group: {age} | Rescaling Factor: {rescaling:.2f}")
            for person in susceptible:
                prob = cases_per_capita_per_age.loc[age] * rescaling
                if random() < prob:
                    self.infect_person(person=person, time=time, record=record)

                    # Add the infected person's ID to initial_infected_ids

                    # Extract symptoms from the person's infection
                    symptoms = getattr(person.infection, "symptoms", "Unknown")
                    if symptoms != "Unknown":
                        symptoms_details = {
                            "tag": getattr(symptoms, "tag", "Unknown"),
                            "max_tag": getattr(symptoms, "max_tag", "Unknown"),
                            "max_severity": getattr(symptoms, "max_severity", "Unknown"),
                            "time_of_symptoms_onset": getattr(symptoms, "time_of_symptoms_onset", "Unknown"),
                        }
                    else:
                        symptoms_details = "Unknown"
                        
                    # Track infected person with symptoms details
                    infected_summary.append((person.id, person.age, symptoms_details))
                    self.current_seeded_cases[super_area.region.name] += 1
                    total_infected += 1
                    if time < 0:
                        self.bring_infection_up_to_date(
                            person=person, time_from_infection=-time, record=record
                        )

        # Print final summary of infections
        print(f"\nTotal Infected in {super_area.name}: {total_infected}")
        print(f"Current Seeded Cases in Region '{super_area.region.name}': {self.current_seeded_cases[super_area.region.name]}")
        print("Infected People Summary:")
        for person_id, person_age, person_symptoms in infected_summary:
            if isinstance(person_symptoms, dict):
                symptoms_str = ", ".join(f"{key}: {value}" for key, value in person_symptoms.items())
            else:
                symptoms_str = person_symptoms
            print(f"  Person ID: {person_id}, Age: {person_age}, Symptoms: {symptoms_str}")
        print(f"=== Finished Infecting Super Area: {super_area.name} ===\n")

        #self.export_infected_cases_to_csv("seeded_infections.csv", include_all_infections=False)

    def _share_initial_infected_ids_across_ranks(self):
        """
        Share initial infected IDs across all MPI ranks using allgather.
        After this method, all ranks will have access to the complete list of initial infected IDs.
        """
        from june.mpi_wrapper import mpi_comm, mpi_rank, mpi_size, mpi_available
        
        # In non-MPI mode, just return - nothing to share
        if not mpi_available:
            print(f"[Single Process] Initial infected IDs: {len(self.initial_infected_ids)}")
            return
            
        print(f"[Rank {mpi_rank}] Sharing {len(self.initial_infected_ids)} initial infected IDs across all ranks")
        
        # Convert set to list for MPI communication (sets are not directly serialisable)
        local_infected_ids = list(self.initial_infected_ids)
        
        # Gather all infected IDs from all ranks
        all_rank_infected_ids = mpi_comm.allgather(local_infected_ids)
        
        # Merge all IDs into a single set to avoid duplicates
        merged_infected_ids = set()
        total_ids_before_merge = 0
        
        for rank_idx, rank_ids in enumerate(all_rank_infected_ids):
            rank_count = len(rank_ids)
            total_ids_before_merge += rank_count
            print(f"[Rank {mpi_rank}] Received {rank_count} infected IDs from Rank {rank_idx}")
            merged_infected_ids.update(rank_ids)
        
        # Update the local initial_infected_ids with the merged set
        self.initial_infected_ids = merged_infected_ids
        
        print(f"[Rank {mpi_rank}] Total IDs before merge: {total_ids_before_merge}")
        print(f"[Rank {mpi_rank}] Total unique IDs after merge: {len(self.initial_infected_ids)}")
        print(f"[Rank {mpi_rank}] All ranks now have access to {len(self.initial_infected_ids)} initial infected IDs")
    
    def get_all_initial_infected_ids(self):
        """
        Get the complete list of initial infected IDs that have been shared across all ranks.
        
        Returns
        -------
        set
            Set of all initial infected person IDs from all ranks
        """
        return self.initial_infected_ids.copy()

    def bring_infection_up_to_date(self, person, time_from_infection, record):
        
        # Update transmission probability
        person.infection.transmission.update_infection_probability(
            time_from_infection=time_from_infection
        )
        # Need to update trajectories to current stage
        symptoms = person.symptoms
        while time_from_infection > symptoms.trajectory[symptoms.stage + 1][0]:
            symptoms.stage += 1
            symptoms.tag = symptoms.trajectory[symptoms.stage][1]
            if symptoms.stage == len(symptoms.trajectory) - 1:
                break   
        # Need to check if the person has already recovered or died
        if symptoms.dead:  # Use the property instead of checking tag.name
            Epidemiology.bury_the_dead(world=self.world, person=person, record=record)
        elif symptoms.recovered:  # Use the property instead of checking tag.name
            Epidemiology.recover(person=person, record=record)

    def infect_super_areas(
        self,
        cases_per_capita_per_age_per_region: pd.DataFrame,
        time: float,
        date: datetime.datetime,
        record: Optional[Record] = None,
    ):
        """
        Infect super areas with number of cases given by data frame

        Parameters
        ----------
        cases_per_capita_per_age_per_region:
            DataFrame containing the number of cases per super area
        time:
            Time where infections start (could be negative if they started before the simulation)
        """
        print(f"\n=== Infecting Super Areas on {date} at time {time} ===")

        for region in self.world.regions:
            print(f"\nProcessing Region: {region.name}")

            # Check if secondary infections already provide seeding
            if "all" in cases_per_capita_per_age_per_region.columns:
                cases_per_capita_per_age = cases_per_capita_per_age_per_region["all"]
                print(f"Using 'all' column for cases per capita.")
            else:
                cases_per_capita_per_age = cases_per_capita_per_age_per_region[region.name]
                print(f"Using region-specific data for {region.name}.")

            # Adjust for secondary infections if needed
            if self._need_to_seed_accounting_secondary_infections(date=date):
                print(f"Adjusting cases for secondary infections in {region.name}.")
                cases_per_capita_per_age = self._adjust_seed_accounting_secondary_infections(
                    cases_per_capita_per_age=cases_per_capita_per_age,
                    region=region,
                    date=date,
                    time=time,
                )
                print(f"Adjusted cases per capita for {region.name}:")
                print(cases_per_capita_per_age)

            # Infect super areas within the region
            for super_area in region.super_areas:
                print(f"  Infecting Super Area: {super_area.name}")
                self.infect_super_area(
                    super_area=super_area,
                    cases_per_capita_per_age=cases_per_capita_per_age,
                    time=time,
                    record=record,
                )

        print(f"=== Finished Infecting Super Areas for {date} ===")

    def unleash_virus_per_day( 
    self, date: datetime, time, record: Optional[Record] = None
    ):
        """
        Infect super areas at a given ```date```

        Parameters
        ----------
        date:
        current date
        time:
        time since start of the simulation
        record:
        Record object to record infections
        """
        from june.global_context import GlobalContext
        
        print(f"[Rank {mpi_rank}] InfectionSeed: Unleashing virus for {date}")

        # Seed past infections if applicable
        if (not self.past_infections_seeded) and self.seed_past_infections:
            print("Seeding past infections...")
            self._seed_past_infections(date=date, time=time, record=record)
            self.past_infections_seeded = True
            print("Past infections seeded successfully.")

        # Determine if the current date qualifies for seeding
        is_seeding_date = self.max_date >= date >= self.min_date
        print(f"Min date : {self.min_date}. Max Date: {self.max_date}")
        date_str = date.date().strftime("%Y-%m-%d")
        not_yet_seeded_date = (
            date_str not in self.dates_seeded
            and date_str
            in self.daily_cases_per_capita_per_age_per_region.index.get_level_values(
                "date"
            )
        )

        print(f"Is seeding date: {is_seeding_date}")
        print(f"Not yet seeded on this date: {not_yet_seeded_date}")
    
        # Perform seeding if applicable
        if is_seeding_date and not_yet_seeded_date:
            
            seed_logger.info(
                f"Seeding {self.infection_selector.infection_class.__name__} infections at date {date.date()}"
            )
            print(
                f"Seeding {self.infection_selector.infection_class.__name__} for date {date.date()}"
            )

            # Retrieve and print cases per capita
            cases_per_capita_per_age_per_region = (
                self.daily_cases_per_capita_per_age_per_region.loc[date]
            )
            print("Cases per capita per age per region:")
            print(cases_per_capita_per_age_per_region)

            
            # Infect super areas
            self.infect_super_areas(
                cases_per_capita_per_age_per_region=cases_per_capita_per_age_per_region,
                time=time,
                record=record,
                date=date,
            )
            
            # Mark this date as seeded
            self.dates_seeded.add(date_str)
            
            # Share initial infected IDs across all ranks after seeding
            print(f"[Rank {mpi_rank}] Completed seeding for {date.date()}, sharing initial infected IDs")
            self._share_initial_infected_ids_across_ranks()
        else:
            print(f"[Rank {mpi_rank}] No seeding required for {date.date()}")

    def _seed_past_infections(self, date, time, record):
        past_dates = []
        for (
            past_date
        ) in self.daily_cases_per_capita_per_age_per_region.index.get_level_values(
            "date"
        ).unique():
            if past_date.date() < date.date():
                past_dates.append(past_date)
        for past_date in past_dates:
            seed_logger.info(f"Seeding past infections at {past_date.date()}")
            past_time = (past_date.date() - date.date()).days
            past_date_str = past_date.date().strftime("%Y-%m-%d")
            self.dates_seeded.add(past_date_str)
            self.infect_super_areas(
                cases_per_capita_per_age_per_region=self.daily_cases_per_capita_per_age_per_region.loc[
                    past_date
                ],
                time=past_time,
                record=record,
                date=past_date,
            )
            self.last_seeded_cases = self.current_seeded_cases.copy()
            self.current_seeded_cases = defaultdict(int)
            if record:
                # record past infections and deaths.
                record.time_step(timestamp=past_date)
        
        # Share initial infected IDs across all ranks after seeding all past infections
        if past_dates:  # Only share if we actually seeded past infections
            print(f"Sharing initial infected IDs after seeding {len(past_dates)} past infection dates")
            self._share_initial_infected_ids_across_ranks()

    def _need_to_seed_accounting_secondary_infections(self, date):
        if self.account_secondary_infections:
            yesterday = date - datetime.timedelta(days=1)
            if yesterday not in self.daily_cases_per_capita_per_age_per_region.index:
                return False
            return True
        return False

    def _adjust_seed_accounting_secondary_infections(
        self, cases_per_capita_per_age, region, date, time
    ):
        people_by_age = defaultdict(int)
        for person in region.people:
            people_by_age[person.age] += 1
        yesterday_seeded_cases = self.last_seeded_cases[region.name]
        today_df = self.daily_cases_per_capita_per_age_per_region.loc[date]
        today_seeded_cases = sum(
            [
                today_df.loc[age, region.name] * people_by_age[age]
                for age in people_by_age
            ]
        )
        yesterday_total_cases = len(
            [
                p
                for p in region.people
                if p.infected
                and (time - p.infection.start_time)
                <= 1  # infection starting time less than one day ago
                and p.infection.__class__.__name__
                == self.infection_selector.infection_class.__name__
            ]
        )
        secondary_infs = yesterday_total_cases - yesterday_seeded_cases
        toseed = max(0, today_seeded_cases - secondary_infs)
        previous = sum(
            [
                cases_per_capita_per_age.loc[age] * people_by_age[age]
                for age in people_by_age
            ]
        )
        cases_per_capita_per_age = cases_per_capita_per_age * toseed / previous
        return cases_per_capita_per_age

    def export_infected_cases_to_csv(self, output_file_path: str, include_all_infections: bool = False):
        """
        Export all infected cases to a CSV file with MPI rank information.
        
        Parameters
        ----------
        output_file_path : str
            Path where the CSV file will be saved
        include_all_infections : bool, default False
            If True, includes all currently infected people in the world.
            If False, only includes initially seeded infections from this seed.
        
        Returns
        -------
        str
            Path to the created CSV file with rank suffix if in MPI mode
        """
        from datetime import datetime
        
        # Import MPI rank information
        try:
            from june.mpi_wrapper import mpi_rank, mpi_available
        except ImportError:
            mpi_rank = 0
            mpi_available = False
        
        # Add rank suffix to filename if in MPI mode
        if mpi_available and mpi_rank > 0:
            base_name, ext = os.path.splitext(output_file_path)
            output_file_path = f"{base_name}_rank_{mpi_rank}{ext}"
        
        # Collect infected cases data
        infected_cases = []
        
        if include_all_infections:
            # Get all infected people from the world
            for region in self.world.regions:
                for super_area in region.super_areas:
                    for person in super_area.people:
                        if person.infected:
                            case_data = self._extract_person_infection_data(person, region.name, super_area.name)
                            infected_cases.append(case_data)
        else:
            # Get only initially seeded infections
            from june.demography import Person
            for person_id in self.initial_infected_ids:
                if person_id in Person._persons:
                    person = Person._persons[person_id]
                    if person.infected:  # Check if still infected
                        region_name = person.super_area.region.name if person.super_area and person.super_area.region else "Unknown"
                        super_area_name = person.super_area.name if person.super_area else "Unknown"
                        case_data = self._extract_person_infection_data(person, region_name, super_area_name)
                        case_data['initially_seeded'] = True
                        infected_cases.append(case_data)
        
        # Define CSV headers
        headers = [
            'person_id',
            'age', 
            'mpi_rank',
            'region_name',
            'super_area_name',
            'infection_type',
            'infection_id',
            'infection_start_time',
            'transmission_probability',
            'symptoms_tag',
            'symptoms_max_tag', 
            'symptoms_max_severity',
            'symptoms_stage',
            'time_of_symptoms_onset',
            'is_dead',
            'is_recovered',
            'initially_seeded',
            'export_timestamp'
        ]
        
        # Write to CSV
        with open(output_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for case in infected_cases:
                # Add export metadata
                case['mpi_rank'] = mpi_rank
                case['export_timestamp'] = datetime.now().isoformat()
                case['initially_seeded'] = case.get('initially_seeded', False)
                
                writer.writerow(case)
        
        print(f"Exported {len(infected_cases)} infected cases to {output_file_path}")
        print(f"MPI Rank: {mpi_rank}")
        
        return output_file_path

    def _extract_person_infection_data(self, person, region_name: str, super_area_name: str) -> dict:
        """
        Extract infection data from a person object.
        
        Parameters
        ----------
        person : Person
            The infected person object
        region_name : str
            Name of the region
        super_area_name : str
            Name of the super area
            
        Returns
        -------
        dict
            Dictionary containing person's infection data
        """
        # Basic person information
        case_data = {
            'person_id': person.id,
            'age': person.age,
            'region_name': region_name,
            'super_area_name': super_area_name,
        }
        
        # Infection information
        if person.infected and person.infection:
            infection = person.infection
            
            # Basic infection data
            case_data.update({
                'infection_type': infection.__class__.__name__,
                'infection_id': getattr(infection, 'infection_id', lambda: 'Unknown')(),
                'infection_start_time': getattr(infection, 'start_time', 'Unknown'),
            })
            
            # Transmission data
            if hasattr(infection, 'transmission'):
                case_data['transmission_probability'] = getattr(infection.transmission, 'probability', 'Unknown')
            else:
                case_data['transmission_probability'] = 'Unknown'
            
            # Symptoms data
            if hasattr(person, 'symptoms') and person.symptoms:
                symptoms = person.symptoms
                case_data.update({
                    'symptoms_tag': getattr(symptoms, 'tag', 'Unknown'),
                    'symptoms_max_tag': getattr(symptoms, 'max_tag', 'Unknown'),
                    'symptoms_max_severity': getattr(symptoms, 'max_severity', 'Unknown'),
                    'symptoms_stage': getattr(symptoms, 'stage', 'Unknown'),
                    'time_of_symptoms_onset': getattr(symptoms, 'time_of_symptoms_onset', 'Unknown'),
                    'is_dead': getattr(symptoms, 'dead', False),
                    'is_recovered': getattr(symptoms, 'recovered', False),
                })
            else:
                case_data.update({
                    'symptoms_tag': 'Unknown',
                    'symptoms_max_tag': 'Unknown', 
                    'symptoms_max_severity': 'Unknown',
                    'symptoms_stage': 'Unknown',
                    'time_of_symptoms_onset': 'Unknown',
                    'is_dead': False,
                    'is_recovered': False,
                })
        else:
            # Person not infected (shouldn't happen in this context, but handle gracefully)
            case_data.update({
                'infection_type': 'None',
                'infection_id': 'None',
                'infection_start_time': 'None',
                'transmission_probability': 'None',
                'symptoms_tag': 'None',
                'symptoms_max_tag': 'None',
                'symptoms_max_severity': 'None', 
                'symptoms_stage': 'None',
                'time_of_symptoms_onset': 'None',
                'is_dead': False,
                'is_recovered': False,
            })
        
        return case_data


class InfectionSeeds:
    """
    Groups infection seeds and applies them sequentially.
    """

    def __init__(self, infection_seeds: List[InfectionSeed]):
        self.infection_seeds = infection_seeds

    def unleash_virus_per_day(
        self, date: datetime, time, record: Optional[Record] = None
    ):
        # Track if any actual seeding occurs in this timestep
        any_seeding_occurred = False
        
        for idx, seed in enumerate(self.infection_seeds):
            # Store initial count before seeding
            initial_ids_count = len(seed.initial_infected_ids)
            
            seed.unleash_virus_per_day(date=date, record=record, time=time)
            
            # Check if this seed actually added new infections
            if len(seed.initial_infected_ids) > initial_ids_count:
                any_seeding_occurred = True
        
        # Only share IDs if actual seeding occurred in this timestep
        if any_seeding_occurred:
            print(f"[Rank {mpi_rank}] New seeding detected, sharing initial infected IDs across ranks")
            self._share_all_initial_infected_ids_across_ranks()
        else:
            print(f"[Rank {mpi_rank}] No new seeding this timestep, skipping ID sharing")
    
    def _share_all_initial_infected_ids_across_ranks(self):
        """
        Share initial infected IDs from all infection seeds across all ranks.
        This ensures that all ranks have complete knowledge of all initially infected individuals
        from all infection types/seeds.
        """
        from june.mpi_wrapper import mpi_comm, mpi_rank, mpi_available
        
        # In non-MPI mode, just print summary
        if not mpi_available:
            total_ids = set()
            for seed in self.infection_seeds:
                total_ids.update(seed.initial_infected_ids)
            print(f"[Single Process] Total initial infected IDs across all seeds: {len(total_ids)}")
            return
        
        # Collect all initial infected IDs from all seeds
        all_local_ids = set()
        for seed in self.infection_seeds:
            all_local_ids.update(seed.initial_infected_ids)
        
        print(f"[Rank {mpi_rank}] Sharing {len(all_local_ids)} total initial infected IDs from {len(self.infection_seeds)} infection seeds")
        
        # Convert to list for MPI communication
        local_infected_ids = list(all_local_ids)
        
        # Gather from all ranks
        all_rank_infected_ids = mpi_comm.allgather(local_infected_ids)
        
        # Merge all IDs
        merged_infected_ids = set()
        for rank_idx, rank_ids in enumerate(all_rank_infected_ids):
            merged_infected_ids.update(rank_ids)
        
        # Update all seeds with the complete merged set
        for seed in self.infection_seeds:
            seed.initial_infected_ids = merged_infected_ids
        
        print(f"[Rank {mpi_rank}] All infection seeds now have access to {len(merged_infected_ids)} initial infected IDs")
    
    def get_all_initial_infected_ids(self):
        """
        Get the complete list of initial infected IDs from all infection seeds.
        
        Returns
        -------
        set
            Set of all initial infected person IDs from all infection seeds and all ranks
        """
        all_ids = set()
        for seed in self.infection_seeds:
            all_ids.update(seed.initial_infected_ids)
        return all_ids

    def __iter__(self):
        return iter(self.infection_seeds)

    def __getitem__(self, item):
        return self.infection_seeds[item]
