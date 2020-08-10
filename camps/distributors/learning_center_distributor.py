import logging
from typing import List, Tuple, Dict

import numpy as np
import random
import yaml
from scipy import stats

from june import paths
from june.utils import parse_age_probabilities


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
        self.neighbour_centers = neighbour_centers
        self.n_shifts = n_shifts

    def distribute_kids(self, areas: List["Area"]):

        for area in areas:
            closest_centers_idx = self.learning_centers.get_closest(
                coordinates = area.coordinates,
                k=self.neighbour_centers
            )
            for person in area.people:
                if person.sex == "m" and self.male_enrollment_rates[person.age] != 0:
                    if random.random() <= self.male_enrollment_rates[person.age]:
                        self.send_kid_to_closest_center_with_availability(
                            person, closest_centers_idx
                        )
                elif (
                    person.sex == "f"
                    and self.female_enrollment_rates[person.age] != 0
                ):
                    if random.random() <= self.female_enrollment_rates[person.age]:
                        self.send_kid_to_closest_center_with_availability(
                            person, closest_centers_idx
                        )
                else:
                    continue

    def send_kid_to_closest_center_with_availability(self, person, closest_centers_idx):
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
