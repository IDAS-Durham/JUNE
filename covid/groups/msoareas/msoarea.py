import numpy as np


class MSOArea:
    """
    Stores information about the MSOA, like the total number of companies, etc.
    """

    def __init__(self, world, name, n_companies, n_companies_a, n_companies_b, n_companies_c, n_companies_d, n_companies_e, n_companies_f, n_companies_g, n_companies_h, n_companies_i, n_companies_j, n_companies_k, n_companies_l, n_companies_m, n_companies_n, n_companies_o, n_companies_p, n_companies_q, n_companies_r, n_companies_s, n_companies_t, n_companies_u):
        '''
        The n_companies_* represent the number of companies in a given msoa
        by sector - here we take the nomis definition of sector which gives
        categories such as:
            A: Agriculture, forestry and fishing
            B: Mining and quarrying
            C: Manufacturing
            ...

        This same level of detail is given at the sex-disaggregated level and can
        be used in the Person class in order to distribute jobs to people which
        can be matched up with the businesses at the msoa level.
        '''
        
        self.world = world
        self.name = name
        #self.small_areas = oares
        self.n_companies = n_companies
        self.n_companies_a = n_companies_a
        self.n_companies_a = n_companies_b
        self.n_companies_a = n_companies_c
        self.n_companies_a = n_companies_d
        self.n_companies_a = n_companies_e
        self.n_companies_a = n_companies_f
        self.n_companies_a = n_companies_g
        self.n_companies_a = n_companies_h
        self.n_companies_a = n_companies_i
        self.n_companies_a = n_companies_j
        self.n_companies_a = n_companies_k
        self.n_companies_a = n_companies_l
        self.n_companies_a = n_companies_m
        self.n_companies_a = n_companies_n
        self.n_companies_a = n_companies_o
        self.n_companies_a = n_companies_p
        self.n_companies_a = n_companies_q
        self.n_companies_a = n_companies_r
        self.n_companies_a = n_companies_s
        self.n_companies_a = n_companies_t
        self.n_companies_a = n_companies_u

class MSOAreas:

    def __init__(self, world):
        self.world = world
        self.members = []
