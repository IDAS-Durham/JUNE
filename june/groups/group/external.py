class ExternalGroup:
    external = True
    __slots__ = "spec", "id", "domain_id"
    def __init__(self, id, spec, domain_id):
        self.spec = spec
        self.id = id
        self.domain_id = domain_id

class ExternalSubgroup:
    external = True
    __slots__ = ("subgroup_type", "group")
    """
    This is a place holder group for groups that live in other domains.
    """
    def __init__(self, domain_id, group_spec, group_id, subgroup_type):
        self.group = ExternalGroup(id=group_id, spec=group_spec, domain_id=domain_id)
        self.subgroup_type = subgroup_type
    
    @property
    def group_id(self):
        return self.group.id

    @property
    def group_spec(self):
        return self.group.spec

    @property
    def domain_id(self):
        return self.group.domain_id

    @classmethod
    def from_external_group(self, group, subgroup_type):
        self.group = group
