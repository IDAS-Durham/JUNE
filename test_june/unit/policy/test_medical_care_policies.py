from june.epidemiology.infection import SymptomTag
from june.policy import (
    Policies,
    Hospitalisation,
)


def test__hospitalise_the_sick(setup_policy_world, selector):
    world, pupil, student, worker, sim = setup_policy_world
    hospitalisation = Hospitalisation()
    policies = Policies([hospitalisation])
    sim.activity_manager.policies = policies
    sim.epidemiology.set_medical_care(
        world=world, activity_manager=sim.activity_manager
    )
    selector.infect_person_at_time(worker, 0.0)
    worker.infection.symptoms.tag = SymptomTag.hospitalised
    assert worker.infection.should_be_in_hospital
    sim.epidemiology.update_health_status(world, 0.0, 0.0)
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
    sim.epidemiology.set_medical_care(
        world=world, activity_manager=sim.activity_manager
    )
    worker.infection.symptoms.tag = SymptomTag.hospitalised
    assert worker.infection.should_be_in_hospital
    sim.epidemiology.update_health_status(world, 0.0, 0.0)
    assert worker.medical_facility == hospital[hospital.SubgroupType.patients]
    sim.clear_world()
    worker.infection.symptoms.tag = SymptomTag.intensive_care
    sim.epidemiology.update_health_status(world, 0.0, 0.0)
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
    sim.epidemiology.set_medical_care(
        world=world, activity_manager=sim.activity_manager
    )
    worker.infection.symptoms.tag = SymptomTag.intensive_care
    assert worker.infection.should_be_in_hospital
    hospital = world.hospitals[0]
    sim.epidemiology.update_health_status(world, 0.0, 0.0)
    assert worker.medical_facility == hospital[hospital.SubgroupType.icu_patients]
    sim.clear_world()
    worker.infection.symptoms.tag = SymptomTag.hospitalised
    sim.epidemiology.update_health_status(world, 0.0, 0.0)
    hospital = worker.medical_facility.group
    sim.activity_manager.move_people_to_active_subgroups(
        ["medical_facility", "residence"]
    )
    assert worker.medical_facility == hospital[hospital.SubgroupType.patients]
    sim.clear_world()
