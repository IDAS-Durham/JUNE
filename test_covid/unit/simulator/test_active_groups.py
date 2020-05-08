


def test__right_group_hierarchy(simulator):
    permanent_group_hierarchy = simulator.permanent_group_hierarchy.copy()
    active_groups = permanent_group_hierarchy.reverse()
    ordered_active_groups = simulator.apply_group_hierarchy(active_groups)

    assert ordered_active_groups == simulator.permanent_group_hierarchy

    # Add some random groups
    active_groups += ['pubs']
    ordered_active_groups = simulator.apply_group_hierarchy(active_groups)
    true_ordered_active_groups = permanent_group_hierarchy.remove(['carehome', 'household'])
    true_ordered_active_groups.append('pubs')
    true_ordered_active_groups += ['carehome', 'household']

    assert  ordered_active_groups == true_ordered_active_groups


def test__right_group_hierarchy_in_box(simulator_box):
    ordered_active_groups = simulator.apply_group_hierarchy(['box'])

    assert ordered_active_groups == ['box']

'''
def test__everyone_is_freed(simulator):
    simulator.set_active_group_to_people(["households"])
    simulator.set_allpeople_free()
    for person in simulator.people.members:
        assert person.active_group == None
    simulator.set_allpeople_free()


def test__everyone_is_in_household(world_ne):
    world_ne.set_active_group_to_people(["households"])
    for person in world_ne.people.members:
        assert person.active_group == "household"
    world_ne.set_allpeople_free()


def test__everyone_is_in_school_household(world_ne):
    world_ne.set_active_group_to_people(["schools", "households"])
    for person in world_ne.people.members:
        should_be_active = "school" if person.school is not None else "household"
        assert person.active_group == should_be_active
    world_ne.set_allpeople_free()



def test__everyone_is_active_somewhere(world_ne):
    world_ne.set_active_group_to_people(["schools", "households"])
    for person in world_ne.people.members:
        assert person.active_group is not None
    world_ne.set_allpeople_free()

'''

