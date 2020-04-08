class CompanyError(BaseException):
    """Class for throwing company related errors."""
    pass

class Company:
    """
    The Company class represents a household and contains information about 
    its workers(19 - 74 years old).
    """

    def __init__(self, company_id, msoa, n_employees):
        self.id = company_id
        self.people = []
        self.msoa = msoa
        self.n_employees_max = n_employees
        self.n_pupils = 0

class Companies:
    pass

