from covid.groups import Group

class Household(Group):
    """
    The Household class represents a household and contains information about 
    its residents.
    """

    def __init__(self, house_id=None, composition=None, area=None):
        if house_id is None:
            super().__init__(None, "household") 
        else:
            super().__init__("Household_%03d"%house_id, "household") 
        self.id = house_id
        self.area = area
        self.people = []
        #self.residents = group(self.id,"household")
        self.household_composition = composition
    
    def set_active_members(self):
        for person in self.people:
            if person.active_group is None:
                person.active_group = "household"

    def update_status_lists(self, time=0):
        self.susceptible.clear()
        self.infected.clear()
        self.recovered.clear()
        for person in self.people:
            person.health_information.update_health_status()
            if person.health_information.susceptible:
                self.susceptible.append(person)
            if person.health_information.infected:
                if person.health_information.in_hospital:
                    continue
                elif person.health_information.dead:
                    continue
                else:
                    self.infected.append(person)
            elif person.health_information.recovered:
                self.recovered.append(person)
                if person in self.infected:
                    self.infected.remove(person)

class Households:
    """
    Contains all households for the given area, and information about them.
    """
    def __init__(self, world):
        self.world = world
        self.members = []

