import copy
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from june import paths
from june.demography import Person, Population
from june.geography import Geography
from june.groups import Hospital, School, Company, Household, University
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
