import numpy as np
import pandas as pd
from june.geography import SuperAreas
from june.infection.infection import InfectionSelector
from june import paths
from typing import List, Tuple
from june.infection.health_index import HealthIndexGenerator

default_n_cases_region_filename = paths.data_path / "processed/seed/n_cases_region.csv"
default_msoa_region_filename = (
    paths.data_path / "processed/geographical_data/oa_msoa_region.csv"
)

class Seed:
    def __init__(
        self,
        super_areas: SuperAreas,
        selector: InfectionSelector,
        n_cases_region: pd.DataFrame = None,
        msoa_region: pd.DataFrame = None,
    ):
        """
        Class to initialize the infection 

        Parameters
        ----------
        super_areas:
            a SuperAreas instance containing populated super_areas and areas.
        infection:
            an instance of the infection class to infect the selected seed.
        n_cases_region:
            data frame containing the number of cases per region starting at a given date.
        msoa_region:
            mapping between super areas and regions.
        """

        self.super_areas = super_areas 
        self.selector    = selector
        self.n_cases_region = n_cases_region
        self.msoa_region = msoa_region
        self.super_area_names = [
            super_area.name for super_area in self.super_areas.members
        ]

    @classmethod
    def from_file(
        self,
        super_areas: "SuperAreas",
        selector: "InfectionSelector",
        n_cases_region_filename: str = default_n_cases_region_filename,
        msoa_region_filename: str = default_msoa_region_filename,
    ) -> "Seed":
        """
        Initialize Seed from file containing the number of cases per region, and mapping
        between super areas and regions

        Parameters
        ----------
        super_areas:
            a SuperAreas instance containing populated super_areas and areas.
        infection:
            an instance of the infection class to infect the selected seed.
        health_index_generator:
            an instance of health index generator to assign symptoms to selected seed.
        n_cases_region_filename:
            path to csv file with n cases per region.
        msoa_region:
            path to csv file containing mapping between super areas and regions.
        
        Returns
        -------
        Seed instance
        """

        n_cases_region = pd.read_csv(n_cases_region_filename)
        msoa_region = pd.read_csv(msoa_region_filename)[["msoa", "region"]]
        return Seed(
            super_areas,
            selector,
            n_cases_region,
            msoa_region.drop_duplicates(),
        )

    def _filter_region(self, region: str = "North East") -> List["SuperArea"]:
        """
        Given a region, return a list of super areas belonging to that region

        Parameters
        ----------
        region:
            name of the region
        """
        msoa_region_filtered = self.msoa_region[self.msoa_region.region == region]
        filter_region = list(
            map(
                lambda x: x in msoa_region_filtered["msoa"].values,
                self.super_area_names,
            )
        )
        return np.array(self.super_areas.members)[filter_region]

    def infect_super_areas(self, super_areas: List["SuperArea"], n_cases: int):
        """
        Infect n_cases random people from a list of super_areas. It will place
        more cases in proportion to the super_area population

        Parameters
        ----------
        super_areas:
            list of super areas to seed.
        n_cases:
            number of cases to seed.
        """
        n_people_region = np.sum([len(super_area.people) for super_area in super_areas])
        n_cases_homogeneous = n_cases / n_people_region
        for super_area in super_areas:
            n_cases_super_area = int(n_cases_homogeneous * len(super_area.people))
            if n_cases_super_area >= 0:
                self.infect_super_area(super_area, n_cases_super_area)

    def infect_super_area(self, super_area: "SuperArea", n_cases: int):
        """
        Infect n_cases random people from a super_area.
        
        Parameters
        ----------
        super_area:
            SuperArea instance, **must be populated**
        n_cases:
            number of cases to seed
        """
        # randomly select people to infect within the super area
        choices = np.random.choice(len(super_area.people), n_cases, replace=False)

        for choice in choices:
            person = list(super_area.people)[choice]
            self.selector.infect_person_at_time(person = person, time = 1.0)

    def unleash_virus_per_region(self):
        """
        Seed the infection per region, using data on number of infected people/region

        """
        for region, n_cases in zip(
            self.n_cases_region["region"], self.n_cases_region["n_cases"]
        ):
            super_areas = self._filter_region(region=region)
            self.infect_super_areas(super_areas, n_cases)

    def unleash_virus(self, n_cases, box_mode=False):
        """
        Seed the infection with n_cases random people being infected,
        proportionally place more cases in the more populated super areas.
        """
        if box_mode:
            self.infect_super_area(self.super_areas.members[0], n_cases)
        else:
            self.infect_super_areas(self.super_areas.members, n_cases)
