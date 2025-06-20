import logging
from pathlib import Path
import h5py
import numpy as np
from june.domains.domain_decomposition import DomainSplitter
from june.geography.geography import Geography
from june.world import World

from . import (
    load_geography_from_hdf5,
    load_hospitals_from_hdf5,
    load_schools_from_hdf5,
    load_companies_from_hdf5,
    load_population_from_hdf5,
    load_care_homes_from_hdf5,
    load_households_from_hdf5,
    load_universities_from_hdf5,
    load_stations_from_hdf5,
    load_cities_from_hdf5,
    load_social_venues_from_hdf5,
    save_geography_to_hdf5,
    save_population_to_hdf5,
    save_schools_to_hdf5,
    save_hospitals_to_hdf5,
    save_companies_to_hdf5,
    save_universities_to_hdf5,
    save_cities_to_hdf5,
    save_stations_to_hdf5,
    save_care_homes_to_hdf5,
    save_social_venues_to_hdf5,
    save_households_to_hdf5,
    save_data_for_domain_decomposition,
    restore_population_properties_from_hdf5,
    restore_households_properties_from_hdf5,
    restore_care_homes_properties_from_hdf5,
    restore_cities_and_stations_properties_from_hdf5,
    restore_geography_properties_from_hdf5,
    restore_companies_properties_from_hdf5,
    restore_school_properties_from_hdf5,
    restore_social_venues_properties_from_hdf5,
    restore_universities_properties_from_hdf5,
    restore_hospital_properties_from_hdf5,
)

logger = logging.getLogger("world_saver")

class RankAwareWorldSaver:
    """
    Enhanced world saver that assigns ranks during initial save
    """
    def __init__(self, world: "World", n_ranks: int):
        self.world = world
        self.n_ranks = n_ranks
        # Get domain split
        self.super_area_to_rank = {}  # super_area -> rank mapping
        
    def save_to_hdf5(self, world: World, file_path: str, split_domains: bool = True):
        """
        Save world to HDF5 with rank assignments
        
        Parameters
        ----------
        file_path : str
            Path to save the HDF5 file
        split_domains : bool
            If True, create separate files for each domain
        """
        # First, compute domain decomposition
        domain_splitter = DomainSplitter.generate_world_split(
            number_of_domains=self.n_ranks,
            world_path=file_path
        )
        
        # Create super_area -> rank mapping
        for rank, super_areas in domain_splitter[0].items():
            for super_area in super_areas:
                self.super_area_to_rank[super_area] = rank
                
        # Save main file with rank information
        with h5py.File(file_path, "w") as f:

            geo = Geography(world.areas, world.super_areas, world.regions)
            save_geography_to_hdf5(geo, file_path)
            logger.info("saving population...")
            needs_to_be_saved = lambda x: (x is not None) and (len(x) > 0)
            save_population_to_hdf5(world.people, file_path, chunk_size)
            if needs_to_be_saved(world.hospitals):
                logger.info("saving hospitals...")
                save_hospitals_to_hdf5(world.hospitals, file_path, chunk_size)
            if needs_to_be_saved(world.schools):
                logger.info("saving schools...")
                save_schools_to_hdf5(world.schools, file_path, chunk_size)
            if needs_to_be_saved(world.companies):
                logger.info("saving companies...")
                save_companies_to_hdf5(world.companies, file_path, chunk_size)
            if needs_to_be_saved(world.households):
                logger.info("saving households...")
                save_households_to_hdf5(world.households, file_path, chunk_size)
            if needs_to_be_saved(world.care_homes):
                logger.info("saving care homes...")
                save_care_homes_to_hdf5(world.care_homes, file_path, chunk_size)
            if needs_to_be_saved(world.cities):
                logger.info("saving cities...")
                save_cities_to_hdf5(world.cities, file_path)
            if needs_to_be_saved(world.stations):
                logger.info("saving stations...")
                save_stations_to_hdf5(world.stations, file_path)
            if needs_to_be_saved(world.universities):
                logger.info("saving universities...")
                save_universities_to_hdf5(world.universities, file_path)
            social_venue_possible_specs = [
                "pubs",
                "groceries",
                "cinemas",
                "gyms",
            ]  # TODO: generalise
            social_venues_list = []
            for spec in social_venue_possible_specs:
                if hasattr(world, spec) and getattr(world, spec) is not None:
                    social_venues_list.append(getattr(world, spec))
            if social_venues_list:
                logger.info("saving social venues...")
                save_social_venues_to_hdf5(social_venues_list, file_path)
            logger.info("Saving domain decomposition data...")
            save_data_for_domain_decomposition(world, file_path)
    
    def _save_domain_decomposition(self, group):
        """Save domain decomposition data with rank assignments"""
        super_areas = list(self.super_area_to_rank.keys())
        ranks = [self.super_area_to_rank[sa] for sa in super_areas]
        
        # Store encoded names and ranks
        super_area_names = [sa.encode('utf-8') for sa in super_areas]
        group.create_dataset("super_area_names", data=super_area_names)
        group.create_dataset("super_area_ranks", data=ranks)
        
        # Store counts per super area
        population = []
        workers = []
        pupils = []
        commuters = []
        
        for sa in super_areas:
            sa_data = self.world.super_areas[sa]
            population.append(len(sa_data.people))
            workers.append(sum(1 for p in sa_data.people if p.work_group))
            pupils.append(sum(1 for p in sa_data.people if hasattr(p, 'school_group')))
            commuters.append(sa_data.n_commuters if hasattr(sa_data, 'n_commuters') else 0)
        
        group.create_dataset("super_area_population", data=population)
        group.create_dataset("super_area_workers", data=workers)
        group.create_dataset("super_area_pupils", data=pupils)
        group.create_dataset("super_area_commuters", data=commuters)
    
    def _save_population_with_ranks(self, group):
        """Save population with rank assignments"""
        people = self.world.people
        n_people = len(people)
        
        # Create datasets
        ids = np.zeros(n_people, dtype=np.int64)
        ranks = np.zeros(n_people, dtype=np.int32)
        super_areas = np.zeros(n_people, dtype='S20')
        
        # Assign people to ranks based on their super area
        for i, person in enumerate(people):
            ids[i] = person.id
            super_areas[i] = person.super_area.id.encode('utf-8')
            ranks[i] = self.super_area_to_rank[person.super_area.id]
        
        # Save datasets
        group.create_dataset("id", data=ids)
        group.create_dataset("rank", data=ranks)
        group.create_dataset("super_area", data=super_areas)
        
        # Add cross-rank reference information
        self._save_cross_rank_refs(group, people)
    
    def _save_cross_rank_refs(self, group, people):
        """Save information about objects referenced across ranks"""
        cross_refs = {}  # (from_rank, to_rank) -> {type: count}
        
        for person in people:
            person_rank = self.super_area_to_rank[person.super_area.id]
            
            # Check primary activity (work/school)
            if person.primary_activity:
                activity_rank = self.super_area_to_rank[person.primary_activity.super_area.id]
                if activity_rank != person_rank:
                    key = (person_rank, activity_rank)
                    if key not in cross_refs:
                        cross_refs[key] = {"primary_activity": 0}
                    cross_refs[key]["primary_activity"] += 1
            
            # Check household (shouldn't be cross-rank but verify)
            if person.household:
                household_rank = self.super_area_to_rank[person.household.super_area.id]
                if household_rank != person_rank:
                    key = (person_rank, household_rank)
                    if key not in cross_refs:
                        cross_refs[key] = {"household": 0}
                    cross_refs[key]["household"] += 1
        
        # Save cross-reference information
        refs_group = group.create_group("cross_rank_refs")
        for (from_rank, to_rank), type_counts in cross_refs.items():
            ref_name = f"rank_{from_rank}_to_{to_rank}"
            ref_group = refs_group.create_group(ref_name)
            for ref_type, count in type_counts.items():
                ref_group.attrs[ref_type] = count
    
    def _create_domain_files(self, main_file_path):
        """Create separate files for each domain"""
        base_path = Path(main_file_path).parent
        for rank in range(self.n_ranks):
            domain_path = base_path / f"domain_{rank}.h5"
            with h5py.File(main_file_path, "r") as src, h5py.File(domain_path, "w") as dst:
                # Copy relevant data for this rank
                self._copy_rank_data(src, dst, rank)