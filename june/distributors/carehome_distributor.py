import logging
from collections import OrderedDict, defaultdict

import numpy as np
import pandas as pd

from june import paths
from june.geography import Area, Areas
from june.groups import CareHome

logger = logging.getLogger(__name__)

default_data_path = (
        paths.data_path
        / "processed/census_data/output_area/EnglandWales/carehomes.csv"
)


class CareHomeError(BaseException):
    pass


class CareHomeDistributor:
    def __init__(self, min_age_in_carehome: int = 65):
        """
        Tool to distribute people from a certain area into a carehome, if there is one.

        Parameters
        ----------
        min_age_in_carehome
            minimum age to put people in carehome.
        """
        self.min_age_in_carehome = min_age_in_carehome

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

    def populate_carehome_in_areas(
            self, areas: Areas, data_filename: str = default_data_path
    ):
        """
        Creates carehomes in areas from dataframe.
        """
        households_df = pd.read_csv(data_filename, index_col=0)
        area_names = [area.name for area in areas]
        households_df = households_df.loc[area_names]
        for area in areas:
            carehome_residents_number = households_df.loc[area.name].values
            if carehome_residents_number != 0:
                self.populate_carehome_in_area(area)

    def populate_carehome_in_area(
            self, area: Area
    ):
        """
        Crates carehome in area, if there needs to be one, and fills it with the
        oldest people in that area.

        Parameters
        ----------
        area:
            area in which to create the carehome
        carehome_residents_number:
            number of people to put in the carehome.
        """
        men_by_age, women_by_age = self._create_people_dicts(area)
        n_residents = area.carehome.n_residents
        if n_residents == 0:
            raise CareHomeError("No carehome residents in this area.")
        self.populate_carehome(area.carehome, men_by_age, women_by_age)

    def _get_person_of_age(self, people_dict: dict, age: int):
        person = people_dict[age].pop()
        if len(people_dict[age]) == 0:  # delete age key if empty list
            del people_dict[age]
        return person

    def populate_carehome(
            self, carehome: CareHome, men_by_age: OrderedDict, women_by_age: OrderedDict
    ):
        """
        Takes the oldest men and women from men_by_age and women_by_age dictionaries,
        and puts them into the care home until max capacity is reached.

        Parameters
        ----------
        carehome:
            carehome where to put people
        men_by_age:
            dictionary containing age as keys and lists of men as values.
        women_by_age:
            dictionary containing age as keys and lists of women as values.
        """
        current_age_to_fill = max(
            np.max(list(men_by_age.keys())), np.max(list(women_by_age.keys()))
        )
        people_counter = 0
        while people_counter < carehome.n_residents:
            # fill until no old people or care home full
            next_age = True
            for people_dict in [men_by_age, women_by_age]:
                if current_age_to_fill in people_dict.keys():
                    person = self._get_person_of_age(people_dict, current_age_to_fill)
                    person.carehome = carehome
                    carehome.add(person, carehome.GroupType.residents)
                    people_counter += 1
                    if people_counter == carehome.n_residents:
                        break
                    next_age = next_age and False
                else:
                    next_age = (
                            next_age and True
                    )  # only decrease age if there are no man nor women left

            if next_age:
                current_age_to_fill -= 1
                if current_age_to_fill < self.min_age_in_carehome:
                    break
