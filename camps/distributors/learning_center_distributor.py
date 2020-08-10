import logging
from typing import List, Tuple, Dict

import numpy as np
import random
import yaml
from scipy import stats

from camps import paths
from june.utils import parse_age_probabilities

default_config_path = (
    paths.camp_configs_path / "defaults/distributors/learning_center_distributor.yaml"
)


class LearningCenterDistributor:
    """
    Distributes students in areas to learning centers
    """

    def __init__(
        self,
        learning_centers: "LearningCenters",
        female_enrollment_rates: Dict[str, float],
        male_enrollment_rates: Dict[str, float],
        teacher_min_age: int = 21,
        neighbour_centers: int = 5,
        n_shifts: int = 3,
    ):
        """
        Parameters
        ----------
        learning_centers:
            instance of LearningCenters, containing all learning centers in the world
        female_enrollment_rates:
            dictionary with enrollment rates as a function of age for females
        male_enrollment_rates:
            dictionary with enrollment rates as a function of age for males
        teacher_min_age:
            minimum age of teachers
        """
        self.learning_centers = learning_centers
        self.female_enrollment_rates = parse_age_probabilities(female_enrollment_rates)
        self.male_enrollment_rates = parse_age_probabilities(male_enrollment_rates)
        self.teacher_min_age = teacher_min_age
        self.neighbour_centers = neighbour_centers
        self.n_shifts = n_shifts

    @classmethod
    def from_file(
        cls,
        learning_centers: "LearningCenters",
        config_path: str = default_config_path,
    ) -> "LearningCenterDistributor":
        """
        Initialize LearningCenterDistributor from path to its config file

        Parameters
        ----------
        learning_centers:
            instance of LearningCenters, containing all learning centers in the world
        config_path:
            path to config dictionary

        Returns
        -------
        LearningCenterDistributor instance
        """
        with open(config_path) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return LearningCenterDistributor(
            learning_centers=learning_centers,
            female_enrollment_rates=config["female_enrollment_rates"],
            male_enrollment_rates=config["male_enrollment_rates"],
            teacher_min_age=config["teacher_min_age"],
            neighbour_centers=config["neighbour_centers"],
            n_shifts=config["n_shifts"],
        )

    def distribute_kids_to_learning_centers(self, areas: "Areas"):
        """
        Given a list of areas, distribute kids in the area to the ```self.neighbour_centers``` closest
        learning centers. Kids will be distributed according to the enrollment rates of their sex and age cohort.
        If a chosen learning center is already over capacity, find another one. If all the closest ones
        are full, pick one at random. Shifts are also assigned uniformly

        Parameters
        ----------
        areas:
            areas object where people to be distributed live
        """

        for area in areas.members:
            closest_centers_idx = self.learning_centers.get_closest(
                coordinates=area.coordinates, k=self.neighbour_centers
            )
            for person in area.people:
                if person.sex == "m" and self.male_enrollment_rates[person.age] != 0:
                    if random.random() <= self.male_enrollment_rates[person.age]:
                        self.send_kid_to_closest_center_with_availability(
                            person, closest_centers_idx
                        )
                elif (
                    person.sex == "f" and self.female_enrollment_rates[person.age] != 0
                ):
                    if random.random() <= self.female_enrollment_rates[person.age]:
                        self.send_kid_to_closest_center_with_availability(
                            person, closest_centers_idx
                        )
                else:
                    continue

    def send_kid_to_closest_center_with_availability(
        self, person: "Person", closest_centers_idx: List[int]
    ):
        """
        Sends a given person to one of their closest learning centers. If full, send to a 
        different one. If all full, pick one at random.

        Parameters
        ----------
        person:
            person to be sent to learning center
        closest_centers_idx:
            ids of the closest centers
        """
        for i in closest_centers_idx:
            center = self.learning_centers.members[i]
            if len(center.students) >= center.n_pupils_max:
                continue
            else:
                center.add(
                    person=person,
                    shift=random.randint(0, self.n_shifts - 1),
                    subgroup_type=center.SubgroupType.students,
                )
                return

            center = self.learning_centers[random.choice(closest_centers_idx)]
            center.add(
                person=person,
                shift=random.randint(0, self.n_shifts - 1),
                subgroup_type=center.SubgroupType.students,
            )
            return

    def distribute_teachers_to_learning_centers(self, areas: "Areas"):
        for learning_center in self.learning_centers.members:
            # Find closest area to learning center
            area = areas.get_closest_areas(
                coordinates=learning_center.coordinates, k=1, return_distance=False
            )[0]
            # get someone in working age
            old_people = [
                person for person in area.people if person.age >= self.teacher_min_age
            ]
            teacher = random.choice(old_people)
            # check whether this person already has a job
            while teacher.primary_activity is not None:
                teacher = random.choice(old_people)
            # add the teacher to all shifts in the school
            for shift in range(self.n_shifts):
                learning_center.add(
                    person=teacher,
                    shift=shift,
                    subgroup_type=learning_center.SubgroupType.teachers,
                )
