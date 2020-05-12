import os
from pathlib import Path

import numpy as np
import random
import pandas as pd
import pytest

from june.time         import Timer
from june.geography    import Geography, SuperArea, Area
from june.demography   import Demography, Person
from june.groups       import Grocery, Groceries, GroceryFiller
from june.distributors import HouseholdDistributor

class TestGrocery:
    def test__create_grocery():
        grocery = Grocery(grocery_id=1, position=(0., 0.))
        assert bool(len(grocery.subgroups[grocery.GroupType.workers].people)>0) is False
        assert bool(len(grocery.subgroups[grocery.GroupType.customers].people)>0) is False
        return grocery
        
    def test__grocery_grouptype(grocery):
        assert grocery.GroupType.workers == 0
        assert grocery.GroupType.customers == 1

    def test__empty_grocery(grocery):
        assert bool(grocery.subgroups[grocery.GroupType.workers].people) is False
        assert bool(grocery.subgroups[grocery.GroupType.customers].people) is False

class TestGroceries:
    def test__create_groceries_in_geography(self,geography,ratio):
        groceries = Groceries(geography = geography,
                              ratio     = ratio)
        super_area = geography.super_areas.members[0]
        #assert len(groceries.members[super_area])==20
        return groceries

    def init_stats(self):
        self.N = [0.,0.,0.,0.,0.]
        return 100
        
    def finish_stats(self,Nruns,norm):
        for i in range(len(self.N)):
            self.N[i] /= Nruns
        print ("Overall statistics: on average ",self.N[0]/float(norm),
               " people in each of the",norm,"groceries:")
        print ("   ",float(self.N[1]/self.N[0]*100.)," % male,",
               float(self.N[3]/self.N[0]*100.)," % over 55, and",
               float(self.N[4]/self.N[0]*100.)," % kids.")
        
    def update_stats(self,grocery):
        self.N[0] += len(grocery.subgroups[grocery.GroupType.customers].people)
        for person in grocery.subgroups[grocery.GroupType.customers].people:
            if person.sex=="m":
                self.N[1] += 1
            else:
                self.N[2] += 1
            if person.age>=55:
                self.N[3] += 1
            elif person.age<=12:
                self.N[4] += 1

    def test_sending_people_to_groceries(self,super_area,groceryfiller,make_stats=False):
        Nruns   = 1
        count   = 0
        Nadults = len(super_area.adult_active_females)+len(super_area.adult_active_males) 
        if make_stats:
            Nruns = self.init_stats()
        while count<Nruns:
            groceryfiller.send_people_to_groceries()
            for grocery in groceryfiller.groceries.members[super_area]:
                grocery.set_active_members()
                for person in grocery.subgroups[grocery.GroupType.customers].people:
                    assert bool(person.active_group=="grocery") is True
                if make_stats:
                    self.update_stats(grocery)
                for person in grocery.subgroups[grocery.GroupType.customers].people:
                    person.active_group=None
                grocery.subgroups[grocery.GroupType.customers].people.clear()
            count += 1
        if make_stats:
            self.finish_stats(Nruns,len(groceryfiller.groceries.members[super_area]))
        assert bool(len(super_area.adult_active_females)+
                    len(super_area.adult_active_males)==Nadults) is True
    
        
if __name__=="__main__":
    grocery       = TestGrocery.test__create_grocery()
    TestGrocery.test__grocery_grouptype(grocery)
    TestGrocery.test__empty_grocery(grocery)

    testgroceries   = TestGroceries()
    geography       = Geography.from_file({"msoa": ["E02000140"]})
    area_names      = [area.name for area in geography.areas]
    demography      = Demography.for_areas(area_names)
    population      = demography.populate(geography.areas)
    household_distributor = HouseholdDistributor.from_file()
    households = household_distributor.distribute_people_and_households_to_areas(
        geography.areas
    )
    print(geography)
    grocerys      = testgroceries.test__create_groceries_in_geography(geography=geography,ratio=760)
    timer         = Timer() 
    grocfiller    = GroceryFiller(grocerys,timer)
    super_area    = geography.super_areas.members[0]
    testgroceries.test_sending_people_to_groceries(super_area,grocfiller,True)
