from covid.groups import Group

class CareHome(Group):
    def __init__(self, carehome_id, area, n_residents):
        super().__init__("CareHome_%04d"%carehome_id, "carehome")
        self.id = carehome_id
        self.area = area
        self.n_residents = n_residents
        self.people = []


class CareHomes:
    def __init__(self, world):
        self.world = world
        self.members = []
