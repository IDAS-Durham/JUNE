import numpy as np
import pandas as pd
import datetime
from collections import Counter
from june import paths
from typing import List, Tuple, Optional
from june.demography.geography import SuperAreas
from june.infection.infection import InfectionSelector
from june.infection.health_index import HealthIndexGenerator

default_n_cases_region_filename = paths.data_path / "input/seed/n_cases_region.csv"
default_msoa_region_filename = (
    paths.data_path / "input/geography/area_super_area_region.csv"
)


class InfectionSeed:
    def __init__(
        self,
        super_areas: SuperAreas,
        selector: InfectionSelector,
        n_cases_region: Optional[pd.DataFrame] = None,
        msoa_region: Optional[pd.DataFrame] = None,
        dates: Optional[List["datetime"]] = None,
        seed_strength: float = 1.0,
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
        self.selector = selector
        self.n_cases_region = n_cases_region
        self.msoa_region = msoa_region
        self.super_area_names = [
            super_area.name for super_area in self.super_areas.members
        ]
        self.dates = dates
        self.min_date = min(self.dates) if self.dates else None
        self.max_date = max(self.dates) if self.dates else None
        self.seed_strength = seed_strength
        self.dates_seeded = []

    @classmethod
    def from_file(
        self,
        super_areas: "SuperAreas",
        selector: "InfectionSelector",
        n_cases_region,
        msoa_region_filename: str = default_msoa_region_filename,
        seed_strength: float = 1.0,
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
        n_cases_region:
            pandas dataframe with number of cases per region.
        msoa_region:
            path to csv file containing mapping between super areas and regions.
        seed_strengh:
            seed only a ```seed_strength``` percent of the original cases
        
        Returns
        -------
        Seed instance
        """

        dates = n_cases_region.index.tolist() 
        msoa_region = pd.read_csv(msoa_region_filename)[["super_area", "region"]]
        return InfectionSeed(
            super_areas,
            selector,
            n_cases_region,
            msoa_region.drop_duplicates(),
            dates,
            seed_strength=seed_strength,
        )

    def _filter_region(self, region: str = "North East") -> List["SuperArea"]:
        """
        Given a region, return a list of super areas belonging to that region

        Parameters
        ----------
        region:
            name of the region
        """
        if "North East" in region:
            msoa_region_filtered = self.msoa_region[
                (self.msoa_region.region == "North East")
                | (self.msoa_region.region == "Yorkshire and The Humber")
            ]
        else:
            msoa_region_filtered = self.msoa_region[self.msoa_region.region == region]
        filter_region = list(
            map(
                lambda x: x in msoa_region_filtered["super_area"].values,
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
        weights = [
            len(super_area.people) / n_people_region for super_area in super_areas
        ]
        chosen_super_areas = np.random.choice(
            super_areas, size=n_cases, replace=True, p=weights
        )
        n_cases_dict = Counter(chosen_super_areas)
        for super_area, n_cases_super_area in n_cases_dict.items():
            if super_area in self.super_areas.members:
                if n_cases_super_area > 0:
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
        susceptible_in_area = [
            person for person in super_area.people if person.susceptible
        ]
        choices = np.random.choice(len(susceptible_in_area), n_cases, replace=False)
        for choice in choices:
            person = list(susceptible_in_area)[choice]
            self.selector.infect_person_at_time(person=person, time=1.0)

    def unleash_virus_per_region(self, date):
        """
        Seed the infection per region, using data on number of infected people/region

        """
        date_str = date.strftime("%Y-%m-%d 00:00:00")
        n_cases_region = self.n_cases_region.loc[date_str]
        if date.date() not in self.dates_seeded:
            for region, n_cases in n_cases_region.iteritems():
                super_areas = self._filter_region(region=region)
                if len(super_areas) > 0:
                    self.infect_super_areas(
                        super_areas, int(self.seed_strength * n_cases)
                    )
            self.dates_seeded.append(date.date())

    def unleash_virus_per_day(self, area, n_cases, date):
        """
        Seed the infection in a given area, over several days

        """
        date_str = date.strftime("%Y-%m-%d 00:00:00")
        if date.date() not in self.dates_seeded:
            self.infect_super_area(self, n_cases)
            self.dates_seeded.append(date.date())


    def unleash_virus(self, n_cases, box_mode=False):
        """
        Seed the infection with n_cases random people being infected,
        proportionally place more cases in the more populated super areas.
        """
        if box_mode:
            self.infect_super_area(self.super_areas.members[0], n_cases)
        else:
            self.infect_super_areas(
                self.super_areas.members, int(self.seed_strength * n_cases)
            )

    def filter_trajectories(self, trajectories, symptoms_to_keep=('dead_hospital', 'dead_icu')):
        filtered_trajectories=[]
        for trajectory in trajectories:
            symptom_tags = [stage['symptom_tag'] for stage in trajectory['stages']]
            if set(symptom_tags).intersection(symptoms_to_keep):
                filtered_trajectories.append(trajectory)
        return filtered_trajectories

    def get_mean_completion_time(self, stage):
        if hasattr(stage.completion_time,'distribution'):
            return stage.completion_time.distribution.mean() 
        else:
            return stage.completion_time.value    

