#from june.groups.group import Group, Supergroup
#
#import numpy as np
#
#
#class CommuteCityUnit(Group):
#    def __init__(self, city, is_peak, super_area=None):
#        super().__init__()
#
#        self.city = city
#        self.super_area = super_area
#        self.is_peak = is_peak
#        self.max_passengers = 50
#        self.no_passengers = 0
#
#<<<<<<< HEAD:june/groups/commute/commutecityunit.py
#=======
#    @property
#    def n_passengers(self):
#        return len(self.people)
#
#    
#class CommuteCityUnits(Supergroup):
#
#    def __init__(self, commutecities):
#>>>>>>> refactor/commute:june/groups/travel_old/commute_old/commutecityunit.py
#
#class CommuteCityUnits(Supergroup):
#    def __init__(self, commutecities, commute_city_units=None):
#
#        if commute_city_units is None:
#            commute_city_units = []
#        super().__init__(commute_city_units)
#        self.commutecities = commutecities
#
#    def init_units(self):
#
#        ids = 0
#        for commutecity in self.commutecities:
#            no_passengers = len(commutecity.commute_internal)
#            no_units = int(float(no_passengers) / 50) + 1
#
#            peak_not_peak = np.random.choice(2, no_units, [0.8, 0.2])
#
#            for i in range(no_units):
#                commutecity_unit = CommuteCityUnit(
#                    city=commutecity.city,
#                    super_area=commutecity.super_area,
#                    is_peak=peak_not_peak[i],
#                )
#                self.add(commutecity_unit)
#                commutecity.commutecityunits.append(commutecity_unit)
#
#            ids += 1
