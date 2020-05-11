import numpy as np
from pathlib import Path

n_cases_region_filename = Path(__file__).parent / "data/processed/seed/"
msoa_region_filename = Path(__file__).parent / "data/processed/geographical_data/oa_msoa_region.csv"

class Seed:
    def __init__(self, geography, msoa_region):

        self.geography = geography
        self.msoa_region = msoa_region
        self.super_area_names = [super_area.name for super_area in geography.super_areas.members]

    @classmethod
    def from_file(self, 
            n_cases_region_filename: str = default_n_cases_region_filename
            msoa_region_filename: str = default_msoa_region
            ):


    def _filter_region(self, region='North East'):
        msoa_region_filtered = self.msoa_region[self.msoa_region.region == region]
        filter_region = list(map(lambda x: x in msoa_region_filtered['msoa'].values, self.super_area_names))
        return np.array(self.geography.super_areas.members)[filter_region]

    def get_n_people_region(self, super_areas):
        return np.sum([len(area.people) for super_area in super_areas for area in super_area.areas.members])


    def infect_region(self, n_cases, super_areas):

        n_people_region = self.get_n_people_region(super_areas)
        n_cases_homogeneous = n_cases/n_people_region
        for super_area in super_areas:
            n_cases_super_area = int(n_cases_homogeneous * len(super_area.people))

    def infect_super_area(self, super_area, n_cases):
        # randomly select people to infect within the super area
        choices = np.random.choice(len(super_area.people), n_cases, replace=False)

        for choice in choices:
            infection.infect_person_at_time(
                    list(super_area.people)[choice],
                    health_index_generator,
                    0.
                    )

        # CALL UPDATE HEALTH STATUS from simulator
        


