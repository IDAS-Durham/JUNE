import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from june.demography import Person, Population
from june.demography.geography import Area, Areas
from camps.distributors import LearningCenterDistributor
from camps.groups import LearningCenter, LearningCenters


def test__age_distribution():
    dummy_area = Area(name="dummy", super_area=None, coordinates=(12.0, 15.0))
    dummy_areas = Areas(areas=[dummy_area],)
    people = [Person.from_attributes(sex="f", age=age) for age in range(100)]
    for person in people:
        person.area = dummy_area
    dummy_area.people = people
    male_enrollment_rates = {
        "dummy_region":
        {
        "0-4": 0.0,
        "4-6": 0.5,
        "6-12": 0.3,
        "12-16": 0.2,
        "16-21": 0.1,
        "21-100": 0.0,
        }
    }

    female_enrollment_rates = {
        "dummy_region":
        {
        "0-4": 0.0,
        "4-6": 0.0,
        "6-12": 1.0,
        "12-16": 0.0,
        "16-21": 0.0,
        "21-100": 0.0,
        }
    }

    area_region_df = pd.DataFrame({'area': ['dummy'], 'region': ['dummy_region']})

    coordinates_1 = (12.3, 15.6)
    learning_center_1 = LearningCenter(coordinates=coordinates_1, n_pupils_max=20)
    coordinates_2 = (120.3, 150.6)
    learning_center_2 = LearningCenter(coordinates=coordinates_2, n_pupils_max=20)
    coordinates = np.vstack((np.array(coordinates_1), np.array(coordinates_2))).T
    learning_centers_tree = BallTree(np.deg2rad(coordinates), metric="haversine")

    learning_centers = LearningCenters(
        learning_centers=[learning_center_1, learning_center_2],
        learning_centers_tree=learning_centers_tree,
    )

    learning_center_distributor = LearningCenterDistributor(
        learning_centers=learning_centers,
        female_enrollment_rates=female_enrollment_rates,
        male_enrollment_rates=male_enrollment_rates,
        area_region_df=area_region_df
    )
    learning_center_distributor.distribute_kids_to_learning_centers(areas=dummy_areas)

    for kid in people:
        if kid.age < 6 or kid.age >= 12:
            assert kid.primary_activity is None
        else:
            assert kid.primary_activity.group.spec == "learning_center"


def test__distribute_teachers():
    dummy_area = Area(name="dummy", super_area=None, coordinates=(12.0, 15.0))
    dummy_areas = Areas(areas=[dummy_area],)
    people = [Person.from_attributes(sex="f", age=age) for age in range(100)]
    for person in people:
        person.area = dummy_area
    dummy_area.people = people
    male_enrollment_rates = {
        "dummy_region":
        {
        "0-4": 0.0,
        "4-6": 0.5,
        "6-12": 0.3,
        "12-16": 0.2,
        "16-21": 0.1,
        "21-100": 0.0,
        }
    }

    female_enrollment_rates = {
        "dummy_region":
        {
        "0-4": 0.0,
        "4-6": 0.0,
        "6-12": 1.0,
        "12-16": 0.0,
        "16-21": 0.0,
        "21-100": 0.0,
        }
    }

    area_region_df = pd.DataFrame({'area': ['dummy'], 'region': ['dummy_region']})

 
    coordinates_1 = (12.3, 15.6)
    learning_center_1 = LearningCenter(coordinates=coordinates_1, n_pupils_max=20)
    coordinates_2 = (120.3, 150.6)
    learning_center_2 = LearningCenter(coordinates=coordinates_2, n_pupils_max=20)
    coordinates = np.vstack((np.array(coordinates_1), np.array(coordinates_2))).T
    learning_centers_tree = BallTree(np.deg2rad(coordinates), metric="haversine")

    learning_centers = LearningCenters(
        learning_centers=[learning_center_1, learning_center_2],
        learning_centers_tree=learning_centers_tree,
        n_shifts=3
    )

    learning_center_distributor = LearningCenterDistributor(
        learning_centers=learning_centers,
        female_enrollment_rates=female_enrollment_rates,
        male_enrollment_rates=male_enrollment_rates,
        area_region_df = area_region_df
    )
    learning_center_distributor.distribute_teachers_to_learning_centers(
        areas=dummy_areas
    )

    for learning_center in learning_centers:
        assert len(learning_center.teachers) == 3
        assert len(learning_center.ids_per_shift[0]) == 1
        assert learning_center.ids_per_shift[0] == learning_center.ids_per_shift[1]
        assert learning_center.ids_per_shift[1] == learning_center.ids_per_shift[2]
        assert learning_center.teachers[0].age >= 21
