import os
from pathlib import Path

import numpy as np
import random
import pandas as pd
import pytest

from june.time       import Timer
from june.geography  import Geography, SuperArea, Area
from june.demography import Demography, Person
from june.groups     import Pub, Pubs, PubFiller

@pytest.fixture(name="pub_coordinates_df")
def load_pubs_data():
    path = Path(__file__).parent.parent.parent.parent / "data/geographical_data/pubs_uk24727_latlong.txt"
    return pd.read_csv(path)

            
class TestPub:
    def test__create_pub():
        pub = Pub(pub_id=1, position=(0., 0.))
        assert bool(len(pub.subgroups[pub.GroupType.workers].people)>0) is False
        assert bool(len(pub.subgroups[pub.GroupType.guests].people)>0) is False
        return pub
        
    def test__pub_grouptype(pub):
        assert pub.GroupType.workers == 0
        assert pub.GroupType.guests == 1

    def test__empty_pub(pub):
        assert bool(pub.subgroups[pub.GroupType.workers].people) is False
        assert bool(pub.subgroups[pub.GroupType.guests].people) is False

class TestPubs:
    def test__create_pubs_in_geography(self,geography,pub_coordinates):
        pubs = Pubs(geography = geography,
                    pub_df    = pub_coordinates,
                    box_mode  = False)
        super_area = geography.super_areas.members[0]
        assert len(pubs.members[super_area])==20
        return pubs

    def init_stats(self):
        self.N = [0.,0.,0.,0.,0.]
        return 100
        
    def finish_stats(self,Nruns):
        for i in range(len(self.N)):
            self.N[i] /= Nruns
        print ("Overall statistics: ",self.N[0]," people in pub:")
        print ("   ",float(self.N[1]/self.N[0]*100.)," % male,",
               float(self.N[3]/self.N[0]*100.)," % over 55, and",
               float(self.N[4]/self.N[0]*100.)," % under 35.")
        
    def update_stats(self,pub):
        self.N[0] += len(pub.subgroups[pub.GroupType.guests].people)
        for person in pub.subgroups[pub.GroupType.guests].people:
            if person.sex=="m":
                self.N[1] += 1
            else:
                self.N[2] += 1
            if person.age>=55:
                self.N[3] += 1
            elif person.age<=35:
                self.N[4] += 1

    def test_sending_people_to_pub(self,super_area,pubfiller,make_stats=False):
        Nruns   = 1
        count   = 0
        Nadults = len(super_area.adult_active_females)+len(super_area.adult_active_males) 
        if make_stats:
            Nruns = self.init_stats()
        while count<Nruns:
            pubfiller.send_people_to_pub()
            for pub in pubfiller.pubs.members[super_area]:
                pub.set_active_members()
                for person in pub.subgroups[pub.GroupType.guests].people:
                    assert bool(person.active_group=="pub") is True
                if make_stats:
                    self.update_stats(pub)
                for person in pub.subgroups[pub.GroupType.guests].people:
                    person.active_group=None
                pub.subgroups[pub.GroupType.guests].people.clear()
            count += 1
        if make_stats:
            self.finish_stats(Nruns)
        assert bool(len(super_area.adult_active_females)+
                    len(super_area.adult_active_males)==Nadults) is True
    
        
if __name__=="__main__":
    pub        = TestPub.test__create_pub()
    TestPub.test__pub_grouptype(pub)
    TestPub.test__empty_pub(pub)

    testpubs   = TestPubs()
    geography  = Geography.from_file({"msoa": ["E02000140"]})
    print(geography)
    area_names = [area.name for area in geography.areas]
    demography = Demography.for_areas(area_names)
    population = demography.populate(geography.areas)
    path       = "../../../data/geographical_data/pubs_uk24727_latlong.txt"
    pub_df     = pd.read_csv(path, sep=" ", header=None)
    print(len(pub_df.columns))
    pub_df.columns = ["latitude","longitude"]
    pubs       = testpubs.test__create_pubs_in_geography(geography=geography,
                                                         pub_coordinates=pub_df)
    timer      = Timer() 
    pubfiller  = PubFiller(pubs,timer)
    super_area = geography.super_areas.members[0]
    testpubs.test_sending_people_to_pub(super_area,pubfiller,True)
