from covid.groups import Group


class Household(Group):
    """
    The Household class represents a household and contains information about 
    its residents.
    We assume four subgroups:
    0 - kids
    1 - young adults
    2 - adults
    3 - old adults
    """

    def __init__(self, house_id, composition, area):
        super().__init__("Household_%03d" % house_id, "household", 4)
        self.id = house_id
        self.area = area
        self.household_composition = composition

    def add(self,person,qualifier="adult"):
        if qualifier=="kid":
            self.groups[0].people.append(person)
        elif qualifier=="young adult":
            self.groups[1].people.append(person)
        elif qualifier=="adult":
            self.groups[2].people.append(person)
        elif qualifier=="old adult":
            self.groups[3].people.append(person)
        else:
            print ("qualifier = ",qualifer," not known in household")
            return
        person.household = self
            
    def set_active_members(self):
        for group in self.groups:
            for person in group.people:
                if person.active_group is None:
                    person.active_group = "household"


class Households:
    """
    Contains all households for the given area, and information about them.
    """

    def __init__(self, world):
        self.world = world
        self.members = []
