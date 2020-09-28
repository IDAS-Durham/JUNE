import numpy as np
from june.groups import University, Universities
from june.geography import Area, SuperArea, Geography, SuperAreas


def test__university_init():
    university = University(coordinates = np.array([1, 2]), n_students_max = 500)
    assert (university.coordinates == np.array([1,2])).all()
    assert university.n_students_max == 500

def test__university_for_super_areas():
    super_area = SuperArea(name="durham", areas=None, coordinates=[54.768, -1.571868])
    super_areas = SuperAreas([super_area])
    unis  = Universities.for_super_areas(super_areas)
    durham_uni = unis[0]
    assert durham_uni.n_students_max == 19025


