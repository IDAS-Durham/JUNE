import logging
import yaml
from collections import OrderedDict, defaultdict

import numpy as np
import pandas as pd

from june import paths
from june.demography.geography import Area, Areas
from june.groups import CareHome

logger = logging.getLogger(__name__)

default_data_path = (
    paths.data_path / "input/care_homes/care_homes_ew.csv"
)
default_config_filename = paths.configs_path / "defaults/groups/carehome.yaml"


class CareHomeError(BaseException):
    pass


class CareHomeDistributor:
    def __init__(
        self,
        min_age_in_care_home: int = 65,
        config_file: str = default_config_filename,
    ):
        """
        Tool to distribute people from a certain area into a care home, if there is one.

        Parameters
        ----------
        min_age_in_care_home
            minimum age to put people in care home.
        """
        self.min_age_in_care_home = min_age_in_care_home
        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        self.sector = list(config["sector"].keys())[0]

    def _create_people_dicts(self, area: Area):
        """
        Creates dictionaries with the men and women per age key living in the area.
        """
        men_by_age = defaultdict(list)
        women_by_age = defaultdict(list)
        for person in area.people:
            if person.sex == "m":
                men_by_age[person.age].append(person)
            else:
                women_by_age[person.age].append(person)
        return men_by_age, women_by_age

    def populate_care_home_in_areas(
        self, areas: Areas, data_filename: str = default_data_path
    ):
        """
        Creates care homes in areas from dataframe.
        """
        care_homes_df = pd.read_csv(data_filename, index_col=0)
        area_names = [area.name for area in areas]
        care_homes_df = care_homes_df.loc[area_names]
        for area in areas:
            care_home_residents_number = care_homes_df.loc[area.name].values
            if care_home_residents_number != 0:
                self.populate_care_home_in_area(area)

    def populate_care_home_in_area(self, area: Area):
        """
        Crates care home in area, if there needs to be one, and fills it with the
        oldest people in that area.

        Parameters
        ----------
        area:
            area in which to create the care home
        care_home_residents_number:
            number of people to put in the care home.
        """
        men_by_age, women_by_age = self._create_people_dicts(area)
        n_residents = area.care_home.n_residents
        if n_residents == 0:
            raise CareHomeError("No care home residents in this area.")
        self.populate_care_home(area.care_home, men_by_age, women_by_age)
        self.assign_workers(area, area.care_home)

    def _get_person_of_age(self, people_dict: dict, age: int):
        person = people_dict[age].pop()
        if len(people_dict[age]) == 0:  # delete age key if empty list
            del people_dict[age]
        return person

    def populate_care_home(
        self, care_home: CareHome, men_by_age: OrderedDict, women_by_age: OrderedDict
    ):
        """
        Takes the oldest men and women from men_by_age and women_by_age dictionaries,
        and puts them into the care home until max capacity is reached.

        Parameters
        ----------
        care_home:
            care home where to put people
        men_by_age:
            dictionary containing age as keys and lists of men as values.
        women_by_age:
            dictionary containing age as keys and lists of women as values.
        """
        current_age_to_fill = max(
            np.max(list(men_by_age.keys())), np.max(list(women_by_age.keys()))
        )
        people_counter = 0
        while people_counter < care_home.n_residents:
            # fill until no old people or care home full
            next_age = True
            for people_dict in [men_by_age, women_by_age]:
                if current_age_to_fill in people_dict.keys():
                    person = self._get_person_of_age(people_dict, current_age_to_fill)
                    care_home.add(
                        person,
                        activity="residence",
                        subgroup_type=care_home.SubgroupType.residents,
                    )
                    people_counter += 1
                    if people_counter == care_home.n_residents:
                        break
                    next_age = next_age and False
                else:
                    next_age = (
                        next_age and True
                    )  # only decrease age if there are no man nor women left

            if next_age:
                current_age_to_fill -= 1
                if current_age_to_fill < self.min_age_in_care_home:
                    break

    def assign_workers(self, area: Area, care_home: CareHome):
        """
        Healthcares sector
            Q: Carers
        """
        carers = [
            person
            for person in area.super_area.workers
            if (person.sector == self.sector 
            and person.primary_activity is None
            and person.sub_sector is None)
        ]
        if len(carers) == 0:
            logger.info(
                f"\n The SuperArea {area.super_area.name} has no health-care workers in it!"
            )
            return
        else:
            n_assigned = 0
            for carer in carers:
                if n_assigned >= care_home.n_workers:
                    break
                care_home.add(
                    person=carer,
                    subgroup_type=care_home.SubgroupType.workers,
                    activity="primary_activity",
                )
                carer.lockdown_status = 'key_worker'
                n_assigned += 1
            if care_home.n_workers > n_assigned:
                logger.info(
                    f"\n There are {care_home.n_workers - n_assigned} carers missing"
                    + "in care_home.id = {care_home.id}"
                )
