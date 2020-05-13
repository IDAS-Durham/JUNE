import os
from pathlib import Path

import numpy as np
import random
import pandas as pd
import pytest

from june.time       import Timer
from june.geography  import Geography, SuperArea, Area
from june.demography import Demography, Person
from june.groups     import Cinema, Cinemas, CinemaFiller
from june.distributors import HouseholdDistributor

@pytest.fixture(name="")
def load_cinemas_data():
    path = Path(__file__).parent.parent.parent.parent / "data/gmapi/cinemas_England.csv"
    return pd.read_csv(path)

            
class TestCinema:
    def test__create_cinema():
        cinema = Cinema(cinema_id=1, position=(0., 0.))
        assert bool(len(cinema.subgroups[cinema.GroupType.workers].people)>0) is False
        assert bool(len(cinema.subgroups[cinema.GroupType.guests].people)>0) is False
        return cinema
        
    def test__cinema_grouptype(cinema):
        assert cinema.GroupType.workers == 0
        assert cinema.GroupType.guests == 1

    def test__empty_cinema(cinema):
        assert bool(cinema.subgroups[cinema.GroupType.workers].people) is False
        assert bool(cinema.subgroups[cinema.GroupType.guests].people) is False

class TestCinemas:
    def test__create_cinemas_in_geography(self,geography,cinemas_df):
        cinemas = Cinemas(geography=geography,
                          cinemas_df=cinemas_df)
        super_area = geography.super_areas.members[0]
        assert len(cinemas.members[super_area])==1
        return cinemas

    def init_stats(self):
        self.N = [0.,0.,0.,0.,0.]
        return 100
        
    def finish_stats(self,Nruns):
        for i in range(len(self.N)):
            self.N[i] /= Nruns
        print ("Overall statistics after ",Nruns," runs: ",self.N[0]," people in cinema:")
        print ("   ",round(float(self.N[1]/self.N[0]*100.),1)," % kids,",
               round(float(self.N[2]/self.N[0]*100.),1)," % 15-25, ",
               round(float(self.N[3]/self.N[0]*100.),1)," % adults",
               round(float(self.N[4]/self.N[0]*100.),1)," % old adults.")
        
    def update_stats(self,cinema):
        self.N[0] += len(cinema.subgroups[cinema.GroupType.guests].people)
        for person in cinema.subgroups[cinema.GroupType.guests].people:
            if person.age<15:
                self.N[1] += 1
            elif person.age<25:
                self.N[2] += 1
            elif person.age<65:
                self.N[3] += 1
            else:
                self.N[4] += 1

    def test_sending_people_to_cinema(self,super_area,cinemafiller,make_stats=False):
        Nruns   = 1
        count   = 0
        Nadults = len(super_area.adult_active_females)+len(super_area.adult_active_males) 
        if make_stats:
            Nruns = self.init_stats()
        while count<Nruns:
            cinemafiller.send_people_to_cinemas()
            for cinema in cinemafiller.cinemas.members[super_area]:
                cinema.set_active_members()
                for person in cinema.subgroups[cinema.GroupType.guests].people:
                    assert bool(person.active_group=="cinema") is True
                if make_stats:
                    self.update_stats(cinema)
                for person in cinema.subgroups[cinema.GroupType.guests].people:
                    person.active_group=None
                cinema.subgroups[cinema.GroupType.guests].people.clear()
            count += 1
        if make_stats:
            self.finish_stats(Nruns)
        assert bool(len(super_area.adult_active_females)+
                    len(super_area.adult_active_males)==Nadults) is True
    
        
if __name__=="__main__":
    cinema        = TestCinema.test__create_cinema()
    TestCinema.test__cinema_grouptype(cinema)
    TestCinema.test__empty_cinema(cinema)

    testcinemas   = TestCinemas()
    geography     = Geography.from_file({"msoa": ["E02000140"]})
    area_names    = [area.name for area in geography.areas]
    demography    = Demography.for_areas(area_names)
    population    = demography.populate(geography.areas)
    household_distributor = HouseholdDistributor.from_file()
    households = household_distributor.distribute_people_and_households_to_areas(
        geography.areas
    )

    pathPost      = "../../../data/geographical_data/ukpostcodes_coordinates.csv"
    postcodes_df  = pd.read_csv(pathPost, sep=",")
    pathE         = "../../../data/gmapi/cinemas_England.csv"
    pathW         = "../../../data/gmapi/cinemas_Wales.csv"
    cinemas_p_df  = pd.read_csv(pathE, sep=",")
    help_df       = pd.read_csv(pathW, sep=",")
    cinemas_p_df.append(help_df,ignore_index=True)
    cinemas_df    = pd.merge(cinemas_p_df, postcodes_df,
                             left_on="postcode", right_on="postcode")
    cinemas       = testcinemas.test__create_cinemas_in_geography(geography=geography,
                                                                  cinemas_df=cinemas_df)
    timer      = Timer() 
    cinemafiller  = CinemaFiller(cinemas,timer)
    super_area = geography.super_areas.members[0]
    testcinemas.test_sending_people_to_cinema(super_area,cinemafiller,True)
