from enum import IntEnum
from itertools import count

from june.groups.group import Group


class CareHome(Group):
    """
    The Carehome class represents a carehome and contains information about 
    its residents, workers and visitors.
    We assume three subgroups:
    0 - workers
    1 - residents 
    2 - visitors 
    """

    spec = "carehome"

    _id = count()

    class GroupType(IntEnum):
        workers = 0
        residents = 1
        visitors = 2

    def __init__(self, area, n_residents):
        super().__init__()
        self.n_residents = n_residents
        self.area = area


class CareHomes:
    def __init__(self):
        self.members = []
