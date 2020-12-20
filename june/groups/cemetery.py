from june.groups import Supergroup, Group


class Cemetery(Group):
    def add(self, person):
        self[0].people.append(person)

class Cemeteries(Supergroup):
    def __init__(self):
        super().__init__([Cemetery()])

    def get_nearest(self, person):
        return self.members[0]
