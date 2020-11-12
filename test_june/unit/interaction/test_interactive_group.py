import pytest
import numpy as np

from june.groups import Group
from june.demography.person import Person
from june.infection.infection_selector import InfectionSelector
from june.groups import Hospital, School, Pub
from june.interaction.interactive_group import InteractiveGroup, InteractiveSchool


def test__substract_information_from_group():
    hospital = Hospital(n_beds=None, n_icu_beds=None)
    person1 = Person.from_attributes()
    person2 = Person.from_attributes()
    person3 = Person.from_attributes()
    person4 = Person.from_attributes()
    person1.susceptibility = 1
    person2.susceptibility = 2
    person3.susceptibility = 3
    person4.susceptibility = 4
    infection_selector = InfectionSelector.from_file()
    hospital.add(person1, subgroup_type=0)
    hospital.add(person2, subgroup_type=0)
    hospital.add(person3, subgroup_type=1)
    hospital.add(person4, subgroup_type=2)
    infection_selector.infect_person_at_time(person1, 1)
    person1.infection.update_health_status(5, 5)
    person3.susceptibility = 0.0
    interactive_group = InteractiveGroup(hospital)
    assert len(interactive_group.infector_ids) == 1
    assert interactive_group.infector_ids[0][0] == person1.id
    assert (
        interactive_group.transmission_probabilities[0]
        == person1.infection.transmission.probability
    )
    assert len(interactive_group.susceptible_ids) == 2
    assert interactive_group.susceptible_ids[0][0] == person2.id
    assert interactive_group.susceptible_ids[1][0] == person4.id
    assert interactive_group.susceptibilities[0][0] == 2
    assert interactive_group.susceptibilities[1][0] == 4


class TestDispatchOnGroupSpec:
    def test__dispatch(self):
        pub = Pub() 
        interactive_pub = InteractiveGroup(pub)
        assert interactive_pub.__class__ == InteractiveGroup
        school = School()
        interactive_school = InteractiveGroup(school)
        assert interactive_school == InteractiveSchool

class TestSchoolInteractiveGroup:
    def test__school_contacts(self):

        pass


