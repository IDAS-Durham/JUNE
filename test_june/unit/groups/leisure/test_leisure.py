import numpy as np
from pytest import fixture

from june.groups.leisure import (
    Leisure,
    Pub,
    Pubs,
    Cinemas,
    Cinema,
    PubDistributor,
    CinemaDistributor,
)
from june.demography.geography import Geography
from june.demography import Person


@fixture(name="geography")
def make_geography():
    geography = Geography.from_file({"msoa": ["E02000140"]})
    return geography


@fixture(name="leisure")
def make_leisure():
    pubs = Pubs([Pub()],)
    pub_distributor = PubDistributor(pubs, male_age_probabilities={"18-50": 0.5})
    cinemas = Cinemas([Cinema()])
    cinema_distributor = CinemaDistributor(
        cinemas, male_age_probabilities={"10-40": 0.2}
    )
    leisure = Leisure(leisure_distributors=[pub_distributor, cinema_distributor])
    # leisure = Leisure.from_geography(["pubs", "cinemas"], geography)
    return leisure


def test__probability_of_leisure(leisure):
    person = Person(sex="m", age=26)
    estimated_time_for_activity = 1 / (0.5 + 0.2)
    delta_time = 0.01
    times = []
    times_goes_pub = 0
    times_goes_cinema = 0
    for _ in range(0, 100):
        counter = 0
        while True:
            counter += delta_time
            activity_distributor = leisure.get_leisure_distributor_for_person(
                person, delta_time
            )
            if activity_distributor is None:
                continue
            if activity_distributor.spec == "pub":
                times_goes_pub += 1
            elif activity_distributor.spec == "cinema":
                times_goes_cinema += 1
            else:
                raise ValueError
            times.append(counter)
            break
    assert np.isclose(np.mean(times), estimated_time_for_activity, atol=0, rtol=0.1)
    assert np.isclose(times_goes_pub / times_goes_cinema, 0.5 / 0.2, atol=0, rtol=0.1)
