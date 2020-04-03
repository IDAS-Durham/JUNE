class School:
    """
    The School class represents a household and contains information about 
    its pupils (6 - 14 years old).
    """

    def __init__(self, school_id, loc, n_pupils):
        self.id = school_id
        self.pupils= {}
        #self.residents = group(self.id,"household")
        self.loc = loc 
        self.n_pupils = n_pupils 

class PrimarySchool(School):
    def __init__(self, school_id, loc, n_pupils):
        super.__init__(school_id, loc, n_pupils)

class SecondarySchool(School):
    def __init__(self, school_id, loc, n_pupils):
        super.__init__(school_id, loc, n_pupils)
