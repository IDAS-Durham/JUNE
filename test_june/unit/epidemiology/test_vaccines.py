from june.epidemiology.vaccines import Vaccine
from june import Person
from june.epidemiology.infection.infection import Delta, Omicron

delta_id = Delta.infection_id()
omicron_id = Omicron.infection_id()


class TestVaccine:
    def test__effective(self):
        effectiveness = [
            {"Delta": {"0-50": 0.6, "50-100": 0.7}},
            {"Delta": {"0-50": 0.8, "50-100": 0.9}},
        ]
        vaccine = Vaccine(
            "pfizer",
            days_to_effective=[0, 10],
            sterilisation_efficacies=effectiveness,
            symptomatic_efficacies=effectiveness,
        )
        person = Person(age=99)
        assert vaccine.get_efficacy(person=person, dose=0, infection_id=delta_id) == (
            0.7,
            0.7,
        )
        assert (
            vaccine.get_efficacy_for_dose_person(
                person=person,
                dose=0,
            )
            == ({delta_id: 0.7}, {delta_id: 0.7})
        )
        assert vaccine.get_efficacy(person=person, infection_id=delta_id, dose=1) == (
            0.9,
            0.9,
        )

        person = Person(age=10)
        assert vaccine.get_efficacy(person=person, infection_id=delta_id, dose=0) == (
            0.6,
            0.6,
        )
        assert vaccine.get_efficacy(person=person, infection_id=delta_id, dose=1) == (
            0.8,
            0.8,
        )

        assert set(vaccine.infection_ids) == set([delta_id])
