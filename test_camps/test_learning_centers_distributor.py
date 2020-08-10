import numpy as np
from sklearn.neighbors import BallTree

from june.demography import Person, Population
from june.demography.geography import Area
from camps.distributors import LearningCenterDistributor
from camps.groups import LearningCenter, LearningCenters

def test__age_distribution():
    dummy_area = Area(name='dummy', super_area=None, coordinates = (12., 15.))
    people = [Person.from_attributes(sex='f', age=age) for age in range(100)]
    for person in people:
        person.area = dummy_area
    dummy_area.people = people
    male_enrollment_rates = {'0-4': 0.,
                    '4-6': 0.5,
                    '6-12': 0.3,
                    '12-16': 0.2,
                    '16-21': 0.1,
                    '21-100': 0.,}
                     
    female_enrollment_rates = { 
                    '0-4': 0.0,
                    '4-6': 0.0,
                    '6-12': 1.,
                    '12-16': 0.0,
                    '16-21': 0.0,
                    '21-100': 0.,
                    }

    coordinates_1 = (12.3, 15.6)
    learning_center_1 = LearningCenter(coordinates=coordinates_1, n_pupils_max=20)
    coordinates_2 = (120.3, 150.6)
    learning_center_2 = LearningCenter(coordinates=coordinates_2, n_pupils_max=20)
    coordinates = np.vstack((np.array(coordinates_1), np.array(coordinates_2))).T
    learning_centers_tree = BallTree(np.deg2rad(coordinates), metric="haversine")

    learning_centers = LearningCenters(learning_centers=[learning_center_1, learning_center_2],
        learning_centers_tree = learning_centers_tree)

    learning_center_distributor = LearningCenterDistributor(learning_centers=learning_centers,
        female_enrollment_rates = female_enrollment_rates,
        male_enrollment_rates=male_enrollment_rates)
    learning_center_distributor.distribute_kids([dummy_area])

    for kid in people:
        if kid.age < 6 or kid.age>=12:
            assert kid.primary_activity is None
        else:
            assert kid.primary_activity.group.spec == 'learning_center' 



