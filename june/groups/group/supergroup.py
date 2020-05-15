from typing import List
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

    def __init__(self, references_to_people=None):
        """
        Parameters
        ----------
        references_to_people
            a list of attributes that contain references to people. This is
            used to erase circular information before using pickle.
        """
        self.members = []
        self.references_to_people = references_to_people
        self.group_type = self.__class__.__name__

    def __iter__(self):
        return iter(self.members)

    def __len__(self):
        return len(self.members)

    def __getitem__(self, item):
        return self.members[item]

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

    @classmethod
    def for_box_mode(cls):
        raise NotImplementedError("Supergroup not available in box mode")

    def erase_people_from_groups_and_subgroups(self):
        """
        Sets all attributes in self.references_to_people to None for all groups.
        Erases all people from subgroups.
        """
        for group in self:
            group.subgroups = [subgroup.__class__(subgroup.spec) for subgroup in group.subgroups] 
            if self.references_to_people is not None:
                for reference in self.references_to_people:
                    setattr(group, reference, None)

