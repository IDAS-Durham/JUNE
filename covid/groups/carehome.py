from covid.groups import Group
from itertools import count

class CareHome(Group):

    _id = count()

    def __init__(self, area, n_residents):
        carehome_id = next(self._id)
        super().__init__(f"Carehome_{carehome_id}", "household")
        self.n_residents = n_residents
        self.area = area

class CareHomes:
    def __init__(self):
        self.members = []
