from covid.groups import Group

class Household(Group):
    """
    The Household class represents a household and contains information about 
    its residents.
    """

    def __init__(self, house_id, composition, area):
        super().__init__("Household_%03d"%house_id, "household") 
        self.id = house_id
        self.area = area
        self.people = []
        #self.residents = group(self.id,"household")
        self.area = area
        self.household_composition = composition 

class Households:
    """
    Contains all households for the given area, and information about them.
    """
    def __init__(self, world):
        self.world = world
        self.members = []

