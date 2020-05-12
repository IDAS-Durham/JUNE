
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
geography = Geography.from_file({"msoa" : ["E02001697"]})
demography = Demography.for_geography(geography)
geography.hospitals = Hospitals.for_geography(geography)
geography.companies = Companies.for_geography(geography)
geography.schools = Schools.for_geography(geography)
geography.carehomes = CareHomes.for_geography(geography)
geography.cemeteries = Cemeteries()

world = World(geography, demography, include_households=True)
t2 = time.time()
print(f"Took {t2 -t1} seconds to run.")
print("Saving pickle...")
world.to_pickle("test.pkl")
