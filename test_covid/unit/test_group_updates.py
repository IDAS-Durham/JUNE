def test__everyone_is_in_household(world_ne):
    world_ne.set_active_group_to_people(["households"])
    for person in world_ne.people.members:
        if person.carehome is not None:
            continue
        assert person.active_group == "household"
    world_ne.set_allpeople_free()


def test__everyone_is_freed(world_ne):
    world_ne.set_active_group_to_people(["households"])
    world_ne.set_allpeople_free()
    for person in world_ne.people.members:
        assert person.active_group == None
    world_ne.set_allpeople_free()


def test__everyone_is_in_school_household(world_ne):
    world_ne.set_active_group_to_people(["schools", "households"])
    for person in world_ne.people.members:
        if person.carehome is not None:
            continue
        should_be_active = "school" if person.school is not None else "household"
        assert person.active_group == should_be_active
    world_ne.set_allpeople_free()


# def test__everyone_is_in_company(world_ne):
#    world_ne.set_active_group_to_people(["companies"])
#    for person in world_ne.people.members:
#        should_be_active = "company" if person.industry is not None else None
#        assert person.active_group == should_be_active
#    world_ne.set_allpeople_free()


def test__everyone_is_active_somewhere(world_ne):
    world_ne.set_active_group_to_people(["schools", "carehomes", "households"])
    for person in world_ne.people.members:
        assert person.active_group is not None
    world_ne.set_allpeople_free()


def find_random_in_school(world_ne):
    for person in world_ne.people.members:
        if person.school is not None:
            selected_person = person
            break
    return selected_person


def find_random_in_company(world_ne):
    for person in world_ne.people.members:
        if person.industry is not None:
            selected_person = person
            break
    print(f"Selected person industry : {selected_person.industry}")
    return selected_person


'''
def test__follow_a_worker(world_ne):
    selected_person = find_random_in_company(world_ne)
    print(f"Industry : {selected_person.industry}")
    world_ne.set_allpeople_free()
    for day in world_ne.timer:
        active_groups = world_ne.timer.active_groups()
        world_ne.set_active_group_to_people(active_groups)
        should_be_active = "company" if "companies" in active_groups else "household"
        assert selected_person.active_group == should_be_active
        world_ne.set_allpeople_free()
        assert selected_person.active_group == None
        if day > 10:
            break
    world_ne.set_allpeople_free()
'''


def test__follow_a_pupil(world_ne):
    selected_person = find_random_in_school(world_ne)
    world_ne.set_allpeople_free()
    for day in world_ne.timer:
        active_groups = world_ne.timer.active_groups()
        world_ne.set_active_group_to_people(active_groups)
        should_be_active = "school" if "schools" in active_groups else "household"
        assert selected_person.active_group == should_be_active
        world_ne.set_allpeople_free()
        assert selected_person.active_group == None
        if day > 10:
            break
    world_ne.set_allpeople_free()


class MockHealthInformation:
    def __init__(self, tag):
        self.tag = tag

    @property
    def in_hospital(self) -> bool:
        return self.tag in ("hospitalised", "intensive care")


# TODO: this tests needs adapting now that people do not hospitalise themselves. May be a nicer
# TODO: implementation once everything is more loosely coupled
def _test__sick_gets_to_hospital_recovers_and_leaves(world_ne):
    # sick goes to hospital
    dummy_person = world_ne.people.members[0]
    dummy_person.health_information = MockHealthInformation('hospitalised')
    dummy_person.get_into_hospital()
    print('in hospital : ', dummy_person.in_hospital)
    world_ne.set_active_group_to_people(["schools", "hospitals", "households"])
    assert dummy_person.active_group == 'hospital'
    world_ne.set_allpeople_free()

    # recovered, leaves hospital
    dummy_person.health_information = MockHealthInformation('asymptomatic')
    # TODO: we should really test that recovering = leaving hospital
    # dummy_person.in_hospital.update_status_lists()
    dummy_person.in_hospital.release_as_patient(dummy_person)
    world_ne.set_active_group_to_people(["schools", "hospitals", "households"])
    assert dummy_person.active_group != 'hospital'
    world_ne.set_allpeople_free()
