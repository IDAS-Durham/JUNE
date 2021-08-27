import re
from collections import OrderedDict

from june.exc import GroupException


class Supergroup:
    """
    A group containing a collection of groups of the same specification,
    like households, carehomes, etc.
    This class is meant to be used as template to inherit from, and it
    integrates basic functionality like iteration, etc.
    It also includes a method to delete information about people in the
    groups.
    """

    def __init__(self, members):
        self.group_type = self.__class__.__name__
        self.spec = self.get_spec()
        self.members = members
        self.members_by_id = self._make_member_ids_dict(members)

    def _make_member_ids_dict(self, members):
        """
        Makes a dictionary with the ids of the members.
        """
        ret = OrderedDict()
        for member in members:
            ret[member.id] = member
        return ret

    def __iter__(self):
        return iter(self.members)

    def __len__(self):
        return len(self.members)

    def __getitem__(self, item):
        return self.members[item]

    def get_from_id(self, id):
        return self.members_by_id[id]

    def __add__(self, supergroup: "Supergroup"):
        for group in supergroup:
            self.add(group)
        return self

    def clear(self):
        self.members_by_id.clear()

    def add(self, group):
        self.members_by_id[group.id] = group
        self.members.append(group)

    @property
    def member_ids(self):
        return list(self.members_by_id.keys())

    def get_spec(self) -> str:
        """
        Returns the speciailization of the super group.
        """
        return re.sub(r"(?<!^)(?=[A-Z])", "_", self.__class__.__name__).lower()

    @property
    def group_spec(self):
        return self.members[0].spec

    @classmethod
    def for_geography(cls):
        raise NotImplementedError(
            "Geography initialization not available for this supergroup."
        )

    @classmethod
    def from_file(cls):
        raise NotImplementedError(
            "From file initialization not available for this supergroup."
        )
