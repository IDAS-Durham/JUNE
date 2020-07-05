from june.world import World
from june.demography.geography import Geography
from june.demography import Demography
from june.groups import (
    Hospitals,
    Schools,
    Companies,
    Households,
    CareHomes,
    Cemeteries,
    Universities,
)
from june.world import generate_world_from_hdf5, generate_world_from_geography
import pickle
import sys
import time

msoaslist = [
    "E02005702",
    "E02005704",
    "E02005736",
    "E02005734",
    "E02001697",
    "E02001701",
    "E02001704",
    "E02001702",
    "E02001812",
    "E02001803",
    "E02001806",
    "E02001796",
    "E02001801",
    "E02001802",
    "E02001795",
    "E02001818",
    "E02001821",
    "E02001814",
    "E02001808",
    "E02001817",
    "E02001816",
    "E02001819",
    "E02001813",
    "E02001804",
    "E02001811",
    "E02001805",
    "E02001791",
    "E02001794",
    "E02001792",
    "E02004320",
    "E02004321",
    "E02004322",
    "E02004325",
    "E02004327",
    "E02004329",
    "E02004330",
    "E02004328",
    "E02001798",
    "E02001793",
    "E02005706",
    "E02002496",
    "E02002498",
    "E02002500",
    "E02002503",
    "E02002504",
    "E02002515",
    "E02002516",
    "E02006910",
    "E02002518",
    "E02002519",
    "E02002513",
    "E02002550",
    "E02002555",
    "E02002549",
    "E02002542",
    "E02002547",
    "E02002545",
    "E02002543",
    "E02002537",
    "E02002544",
    "E02002541",
    "E02002523",
    "E02002540",
    "E02002536",
    "E02002538",
    "E02002535",
    "E02006909",
    "E02002489",
    "E02002484",
    "E02002487",
    "E02002485",
    "E02002483",
    "E02002493",
    "E02002490",
    "E02002492",
    "E02002494",
    "E02002488",
    "E02002491",
    "E02004332",
    "E02002505",
    "E02002497",
    "E02002502",
    "E02006812",
    "E02002499",
    "E02002506",
    "E02006811",
    "E02002509",
    "E02002501",
    "E02002508",
    "E02002507",
    "E02002529",
    "E02002514",
    "E02002512",
]

t1 = time.time()

# we have two options, we can take the list of areas above and select a few:
geography = Geography.from_file({"super_area": msoaslist[:20]})
# or select an entire region:
#geography = Geography.from_file({"region" : ["North East", "Yorkshire and The Humber"]})
#geography = Geography.from_file({"region" : ["London"]})

demography = Demography.for_geography(geography)
# then this automatically creates the world and saves it to world.hdf5
geography.hospitals = Hospitals.for_geography(geography)
geography.companies = Companies.for_geography(geography)
geography.schools = Schools.for_geography(geography)
geography.universities = Universities.for_super_areas(geography.super_areas)
geography.care_homes = CareHomes.for_geography(geography)
geography.cemeteries = Cemeteries()
#
world = generate_world_from_geography(
    geography, include_households=True, include_commute=False
)

empty_households = 0
for household in world.households:
    if len(household.people) == 0:
        empty_households+= 1

t2 = time.time()
print(f"Took {t2 -t1} seconds to run.")
print("Saving hdf5...")
world.to_hdf5("small_test_04_07.hdf5")
print("Done :)")
