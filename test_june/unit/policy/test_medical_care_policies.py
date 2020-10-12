import copy
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from june import paths
from june.demography import Person, Population
from june.geography import Geography
from june.groups import Hospital, School, Company, Household, University, CareHome
from june.groups import (
    Hospitals,
    Schools,
    Companies,
    Households,
    Universities,
    Cemeteries,
)
from june.groups.leisure import leisure, Cinemas, Pubs, Cinema, Pub
from june.infection import SymptomTag
from june.infection.infection_selector import InfectionSelector
from june.interaction import Interaction
from june.policy import (
    Policy,
    Policies,
    Hospitalisation,
    MedicalCarePolicies,
)
from june.simulator import Simulator
from june.world import World


def test__hospitalise_the_sick(setup_policy_world, selector):
    world, pupil, student, worker, sim = setup_policy_world
    hospitalisation = Hospitalisation()
    policies = Policies([hospitalisation])
    sim.activity_manager.policies = policies
    selector.infect_person_at_time(worker, 0.0)
    worker.infection.symptoms.tag = SymptomTag.hospitalised
    assert worker.infection.should_be_in_hospital
    sim.update_health_status(0.0, 0.0)
    assert worker.medical_facility is not None
    sim.activity_manager.move_people_to_active_subgroups(
        ["medical_facility", "residence"]
    )
    assert worker in worker.medical_facility.people
    sim.clear_world()


def test__move_people_from_hospital_to_icu(setup_policy_world, selector):
    world, pupil, student, worker, sim = setup_policy_world
    hospital = world.hospitals[0]
    selector.infect_person_at_time(worker, 0.0)
    hospitalisation = Hospitalisation()
    policies = Policies([hospitalisation])
    sim.activity_manager.policies = policies
    worker.infection.symptoms.tag = SymptomTag.hospitalised
    assert worker.infection.should_be_in_hospital
    sim.update_health_status(0.0, 0.0)
    assert worker.medical_facility == hospital[hospital.SubgroupType.patients]
    sim.clear_world()
    worker.infection.symptoms.tag = SymptomTag.intensive_care
    sim.update_health_status(0.0, 0.0)
    hospital = worker.medical_facility.group
    sim.activity_manager.move_people_to_active_subgroups(
        ["medical_facility", "residence"]
    )
    assert worker.medical_facility == hospital[hospital.SubgroupType.icu_patients]
    sim.clear_world()


def test__move_people_from_icu_to_hospital(setup_policy_world, selector):
    world, pupil, student, worker, sim = setup_policy_world
    selector.infect_person_at_time(worker, 0.0)
    hospitalisation = Hospitalisation()
    policies = Policies([hospitalisation])
    sim.activity_manager.policies = policies
    worker.infection.symptoms.tag = SymptomTag.intensive_care
    assert worker.infection.should_be_in_hospital
    hospital = world.hospitals[0]
    sim.update_health_status(0.0, 0.0)
    assert worker.medical_facility == hospital[hospital.SubgroupType.icu_patients]
    sim.clear_world()
    worker.infection.symptoms.tag = SymptomTag.hospitalised
    sim.update_health_status(0.0, 0.0)
    hospital = worker.medical_facility.group
    sim.activity_manager.move_people_to_active_subgroups(
        ["medical_facility", "residence"]
    )
    assert worker.medical_facility == hospital[hospital.SubgroupType.patients]
    sim.clear_world()

#def test__care_home_residents_denied_treatment(setup_policy_world, selector):
#    world, pupil, student, worker, sim = setup_policy_world
#    person = Person.from_attributes()
#    person.area = world.areas[0]
#    care_home = CareHome()
#    care_home.add(person)
#    assert person.residence.group == care_home
#    selector.infect_person_at_time(person, 0.0)
#    person.infection.symptoms.tag = SymptomTag.hospitalised
#    assert person.infection.should_be_in_hospital
#    hospitalisation = Hospitalisation(probability_of_care_home_resident_admission=0.4)
#
#    times_admitted = 0
#    N = 1000
#    for _ in range(N):
#        hospitalisation.apply(person=person, hospitals=None, record = None)
#        if person.medical_facility is not None:
#            assert person.id in person.medical_facility.group.ward_ids
#            times_admitted += 1
#            person.medical_facility.group.ward_ids = set()
#            person.subgroups.medical_facility = None
#            continue
#        world.hospitals[0].denied_treatment_ids = set()
#    assert np.isclose(times_admitted, 0.4 * N, rtol=0.1)
#
