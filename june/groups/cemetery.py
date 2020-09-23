from june.groups.group import Supergroup


class Cemetery:
    def __init__(self):
        self.people = []
        self.spec = 'cemetery'

    def add(self, person):
        self.people.append(person)


class Cemeteries(Supergroup):
    def __init__(self):
        super().__init__()
        self.members = [Cemetery()]

    def get_nearest(self, person):
        return self.members[0]
