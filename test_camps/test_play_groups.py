from camps.groups import PlayGroup
from june.demography import Person


def test__comoposition_play_groups():

    kid_young = Person.from_attributes(age=3)
    kid_middle = Person.from_attributes(age=8)
    kid_old = Person.from_attributes(age=13)
    play_group = PlayGroup()
    subgroup = play_group.get_leisure_subgroup(person=kid_young)
    assert subgroup.subgroup_type == 0
    subgroup = play_group.get_leisure_subgroup(person=kid_middle)
    assert subgroup.subgroup_type == 1
    subgroup = play_group.get_leisure_subgroup(person=kid_old)
    assert subgroup.subgroup_type == 2
    not_kid = Person.from_attributes(age=50)
    subgroup = play_group.get_leisure_subgroup(person=not_kid)
    assert subgroup is None
