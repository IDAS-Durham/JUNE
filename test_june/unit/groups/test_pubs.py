import os
from pathlib import Path

import numpy as np
import random
import pandas as pd
import pytest

from june.time       import Timer
from june.geography  import Geography
from june.geography  import Area
from june.demography import Person
from june.groups     import Pub, Pubs

@pytest.fixture(name="carehomes_df")
def load_pubs_data():
    pubs_path = Path(__file__).parent.parent.parent.parent / "data/geographical_data/pubs_uk24727_latlong.txt"
    return pd.read_csv(pubs_path)

class MockArea:
    def __init__(self):
        self.coordinates = np.array([0.,0.])
        self.adult_active_females = []
        self.adult_active_males   = []
        self.fill_lists(1000)
        self.timer = Timer() 
        pass

    def fill_lists(self,N):
        while len(self.adult_active_females)+len(self.adult_active_males)<N:
            age = 18.+70.*random.random()
            sex = random.random()>0.5
            person = Person(age=age,sex=sex)
            if sex==0:
                self.adult_active_males.append(person)
            else:
                self.adult_active_females.append(person)
            
class TestPub:
    def __init__(self):
        pass
    #@pytest.fixture(name="pub", scope="session")
    def create_pub(self):
        return Pub(pub_id=1, position=(0., 0.))
    
    def test__pub_grouptype(self, pub):
        assert pub.GroupType.workers == 0
        assert pub.GroupType.guests == 1

    def test__empty_pub(self, pub):
        assert bool(pub.subgroups[pub.GroupType.workers].people) is False
        assert bool(pub.subgroups[pub.GroupType.guests].people) is False

class TestPubs:
    def __init__(self):
        pass

    def test__create_pubs_in_mockarea(self,area):
        pubs = Pubs(geography = area,
                    pub_df    = None,
                    box_mode  = True)
        assert len(pubs.members[area])==2
        return pubs

    def test_sending_people_to_pub(self,area,pubs):
        N = [0.,0.,0.,0.,0.]
        Nruns = 100
        count = 0
        while count<Nruns:
            pubs.send_people_to_pub()
            for pub in pubs.members[area]:
                N[0] += len(pub.subgroups[pub.GroupType.guests].people)
                for person in pub.subgroups[pub.GroupType.guests].people:
                    if person.sex==0:
                        N[1] += 1
                    else:
                        N[2] += 1
                    if person.age>=55:
                        N[3] += 1
                    elif person.age<=35:
                        N[4] += 1
                pub.subgroups[pub.GroupType.guests].people.clear()
            count += 1
            
        for i in range(len(N)):
            N[i] /= Nruns
        #print ("Overall statistics: ",N[0]," people in pub:")
        #print ("   ",float(N[1]/N[0]*100.)," % male,",
        #       float(N[3]/N[0]*100.)," % over 55, and",
        #       float(N[4]/N[0]*100.)," % under 35.")
        
if __name__=="__main__":
    area      = MockArea()
    testpub   = TestPub()
    pub       = testpub.create_pub()
    testpub.test__pub_grouptype(pub)
    testpub.test__empty_pub(pub)
    testpubs  = TestPubs()
    pubs      = testpubs.test__create_pubs_in_mockarea(area)
    testpubs.test_sending_people_to_pub(area,pubs)
