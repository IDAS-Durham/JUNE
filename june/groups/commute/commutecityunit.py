import logging
import os
from enum import IntEnum
from pathlib import Path
from typing import List, Dict, Optional
from june.groups.group import Group, Supergroup

import numpy as np

class CommuteCityUnit(Group):

    def __init__(self, commutecityunit_id, city, is_peak):
        self.commutecityunit_id = commutecityunit_id,
        self.city = city
        self.is_peak = is_peak
        #self.passengers = [] -> people form group inheritence
        self.max_passengers = 50

    
class CommuteCityUnits(Supergroup):

    def __init__(self, commutecities, init = False):

        self.commutecities = commutecities
        self.init = init
        self.members = []

        if self.init:
            self.init_units()

    def init_units(self):

        ids = 0
        for commutecity in self.commutecities:
            no_passengers = len(commutecity.commute_internal)
            no_units = int(float(no_passengers)/50) + 1

            peak_not_peak = np.random.choice(2,no_units,[0.8,0.2])
            
            for i in range(no_units):
                commutecity_unit = CommuteCityUnit(
                    commutecityunit_id = ids,
                    city = commutecity.city,
                    is_peak = peak_not_peak[i]
                )

                self.members.append(commutecity_unit)
                commutecity.commutecityunits.append(commutecity_unit)
                
            ids += 1
