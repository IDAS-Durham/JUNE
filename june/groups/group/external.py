class ExternalGroup:
    external = True
    __slots__ = "spec", "id", "domain_id"

    def __init__(self, id, spec, domain_id):
        self.spec = spec
        self.id = id
        self.domain_id = domain_id

    def clear(self):
        pass

    def get_leisure_subgroup(self, person, subgroup_type, to_send_abroad):
        return ExternalSubgroup(group=self, subgroup_type=subgroup_type)


class ExternalSubgroup:
    external = True
    __slots__ = ("subgroup_type", "group")
    """
    This is a place holder group for groups that live in other domains.
    """

    def __init__(self, group, subgroup_type):
        self.group = group
        self.subgroup_type = subgroup_type

    @property
    def group_id(self):
        return self.group.id

    @property
    def domain_id(self):
        return self.group.domain_id

    def clear(self):
        pass
    
    @property
    def spec(self):
        return self.group.spec
