import logging
import yaml
from random import shuffle, randint
from collections import OrderedDict, defaultdict
from itertools import chain

import numpy as np
import pandas as pd

from june import paths
from june.geography import Area, Areas, SuperArea, SuperAreas
from june.groups import CareHome

logger = logging.getLogger("care_home_distributor")

care_homes_per_area_filename = paths.data_path / "input/care_homes/care_homes_ew.csv"

default_config_filename = paths.configs_path / "defaults/groups/care_home.yaml"
default_communal_men_by_super_area = (
    paths.data_path / "input/care_homes/communal_male_residents_by_super_area.csv"
)
default_communal_women_by_super_area = (
    paths.data_path / "input/care_homes/communal_female_residents_by_super_area.csv"
)


class CareHomeError(BaseException):
    pass


class CareHomeDistributor:
    def __init__(
        self,
        communal_men_by_super_area: dict,
        communal_women_by_super_area: dict,
        n_residents_per_worker: int = 10,
        workers_sector="Q",
    ):
        """
        Tool to distribute people from a certain area into a care home, if there is one.

        Parameters
        ----------
        min_age_in_care_home
            minimum age to put people in care home.
        """
        self.communal_men_by_super_area = communal_men_by_super_area
        self.communal_women_by_super_area = communal_women_by_super_area
        self.n_residents_per_worker = n_residents_per_worker
        self.workers_sector = workers_sector

    @classmethod
    def from_file(
        cls,
        communal_men_by_super_area_filename: str = default_communal_men_by_super_area,
        communal_women_by_super_area_filename: str = default_communal_women_by_super_area,
        config_filename: str = default_config_filename,
    ):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        communal_men_df = pd.read_csv(communal_men_by_super_area_filename, index_col=0)
        communal_women_df = pd.read_csv(
            communal_women_by_super_area_filename, index_col=0
        )
        return cls(
            communal_men_by_super_area=communal_men_df.T.to_dict(),
            communal_women_by_super_area=communal_women_df.T.to_dict(),
            n_residents_per_worker=config["n_residents_per_worker"],
            workers_sector=config["workers_sector"],
        )

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

    def _find_person_in_age_range(self, people_by_age: dict, age_1, age_2):
        available_people = []
        for age in range(age_1, age_2 + 1):
            available_people += people_by_age[age]
        if not available_people:
            return None
        chosen_person_idx = randint(0, len(available_people) - 1)
        chosen_person = available_people[chosen_person_idx]
        people_by_age[chosen_person.age].remove(chosen_person)
        if not people_by_age[chosen_person.age]:
            del people_by_age[chosen_person.age]
        return chosen_person

    def _sort_dictionary_by_age_range_key(self, d: dict):
        """
        Sorts a dictionary by decreasing order of the age range in the keys.
        """
        ret = OrderedDict()
        ages = [age_range[0] for age_range in d.keys()]
        men_age_ranges_sorted = np.array(list(d.keys()))[np.argsort(ages)[::-1]]
        for key in men_age_ranges_sorted:
            ret[key] = d[key]
        return ret

    def populate_care_homes_in_super_areas(self, super_areas: SuperAreas):
        """
        Populates care homes in the super areas. For each super area, we look into the
        population that lives in communal establishments, from there we pick the oldest ones
        to live in care homes.
        """
        logger.info(f"Populating care homes")
        total_care_home_residents = 0
        for super_area in super_areas:
            men_communal_residents = self.communal_men_by_super_area[super_area.name]
            women_communal_residents = self.communal_women_by_super_area[
                super_area.name
            ]
            communal_men_sorted = self._sort_dictionary_by_age_range_key(
                men_communal_residents
            )
            communal_women_sorted = self._sort_dictionary_by_age_range_key(
                women_communal_residents
            )
            areas_with_care_homes = [
                area for area in super_area.areas if area.care_home is not None
            ]
            # now we need to choose from each area population which people go to the care home based on
            # the super area statistics. Check who goes first.
            shuffle(areas_with_care_homes)
            areas_dicts = [
                self._create_people_dicts(area) for area in areas_with_care_homes
            ]
            found_person = True
            assert communal_men_sorted.keys() == communal_women_sorted.keys()
            while found_person:
                found_person = False
                for i, area in enumerate(areas_with_care_homes):
                    care_home = area.care_home
                    if len(care_home.residents) < care_home.n_residents:
                        # look for men first
                        for age_range in communal_men_sorted:
                            age1, age2 = list(map(int, age_range.split("-")))
                            if communal_men_sorted[age_range] <= 0:
                                if communal_women_sorted[age_range] <= 0:
                                    continue
                                # find woman
                                person = self._find_person_in_age_range(
                                    areas_dicts[i][1], age1, age2
                                )
                                if person is None:
                                    continue
                                care_home.add(person)
                                communal_women_sorted[age_range] -= 1
                                total_care_home_residents += 1
                                found_person = True
                                break
                            person = self._find_person_in_age_range(
                                areas_dicts[i][0], age1, age2
                            )
                            if person is None:
                                # find woman
                                person = self._find_person_in_age_range(
                                    areas_dicts[i][1], age1, age2
                                )
                                if person is None:
                                    continue 
                                care_home.add(person)
                                communal_women_sorted[age_range] -= 1
                                total_care_home_residents += 1
                                found_person = True
                                break
                            care_home.add(person)
                            communal_men_sorted[age_range] -= 1
                            total_care_home_residents += 1
                            found_person = True
                            break
        logger.info(
            f"This world has {total_care_home_residents} people living in care homes."
        )

    def distribute_workers_to_care_homes(self, super_areas: SuperAreas):
        for super_area in super_areas:
            care_homes = [
                area.care_home
                for area in super_area.areas
                if area.care_home is not None
            ]
            if not care_homes:
                continue
            carers = [
                person
                for person in super_area.workers
                if (
                    person.sector == "Q"
                    and person.primary_activity is None
                    and person.sub_sector is None
                )
            ]
            shuffle(carers)
            for care_home in care_homes:
                while len(care_home.workers) < care_home.n_workers:
                    try:
                        carer = carers.pop()
                    except:
                        logger.info(
                            f"Care home in area {care_home.area.name} has not enough workers!"
                        )
                        break
                    care_home.add(
                        person=carer,
                        subgroup_type=care_home.SubgroupType.workers,
                        activity="primary_activity",
                    )
                    carer.lockdown_status = "key_worker"
