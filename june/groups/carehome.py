from itertools import count

from june.groups.group import Group
from june import get_creation_logger
from enum import IntEnum

class CareHome(Group):
    """
    The Carehome class represents a carehome and contains information about 
    its residents, workers and visitors.
    We assume three subgroups:
    0 - workers
    1 - residents 
    2 - visitors 
    """

    _id = count()

    class GroupType(IntEnum):
        workers = 0
        residents = 1
        visitors = 2

    def __init__(self, area, n_residents):
        carehome_id = next(self._id)
        super().__init__(f"Carehome_{carehome_id}", "household")
        self.n_residents = n_residents
        self.area = area

class CareHomes:
    def __init__(self):
        self.members = []
