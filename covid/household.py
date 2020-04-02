class Household:
    """
    The Household class represents a household and contains information about 
    its residents.
    """

    def __init__(self, house_id, composition, area):
        self.id = house_id
        self.residents = {}
        #self.residents = group(self.id,"household")
        self.area = area
        self.household_composition = composition 

