class School:
    """
    The School class represents a household and contains information about 
    its pupils (6 - 14 years old).
    """

    def __init__(self, school_id, coordinates, n_pupils, urn):
        self.id = school_id
        self.pupils= {}
        self.urn = urn
        self.coordinates = coordinates
        #self.residents = group(self.id,"household")
        self.n_pupils_max = n_pupils
        self.n_pupils = 0

class PrimarySchool(School):
    def __init__(self, school_id, coordinates, n_pupils, urn):
        super.__init__(school_id, coordinates, n_pupils, urn)

class SecondarySchool(School):
    def __init__(self, school_id, coordinates, n_pupils, urn):
        super.__init__(school_id, coordinates, n_pupils, urn)
