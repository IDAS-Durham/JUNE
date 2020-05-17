
from june import World
from june.geography import Geography
from june.demography import Demography
from june.groups import Hospitals, Schools, Companies, Households, CareHomes, Cemeteries
import dill
import pickle
import sys
import time
sys.setrecursionlimit(100000)

t1 = time.time()
#geography = Geography.from_file({"region" : ["North East"]})
geography = Geography.from_file({"msoa" : ["E02001697", "E02001731"]})
demography = Demography.for_geography(geography)
geography.hospitals = Hospitals.for_geography(geography)
geography.companies = Companies.for_geography(geography)
geography.schools = Schools.for_geography(geography)
geography.carehomes = CareHomes.for_geography(geography)
geography.cemeteries = Cemeteries()

world = World(geography, demography, include_households=True, include_commute=True)

print(len(world.commutecityunits.members))
print(world.commutecityunits.members[0].people)
print(world.people.members[0].mode_of_transport)
t2 = time.time()
print(f"Took {t2 -t1} seconds to run.")
print("Saving pickle...")
world.to_pickle("test.pkl")
