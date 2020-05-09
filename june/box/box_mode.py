from june.groups.group import Group


class Boxes:
    def __init__(self):
        self.members = []


class Box(Group):
    def __init__(self):
        super().__init__(None, "box")
