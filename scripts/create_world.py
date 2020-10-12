from june.world import World
from june.geography import Geography
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
from june.groups.leisure import Pubs, Cinemas, Groceries, generate_leisure_for_config
from june.groups.travel import Travel
from june.world import generate_world_from_geography
from june import paths

from pathlib import Path
import pickle
import sys
import time
import numpy as np

scripts_path = Path(__file__).parent 

# load london super areas
london_areas_path = scripts_path / "london_areas.txt"
london_areas = np.loadtxt(london_areas_path, dtype=np.str_)[45:50]

# add King's cross area for station
if "E00004734" not in london_areas:
    london_areas = np.append(london_areas, "E02000187")

## add some people commuting from Cambridge
#london_areas = np.concatenate((london_areas, ["E02003719", "E02003720", "E02003721"]))

## add Bath as well to have a city with no stations
#london_areas = np.concatenate(
#    (london_areas, ["E02002988", "E02002989", "E02002990", "E02002991", "E02002992",],)
#)


t1 = time.time()

# default config path
config_path = scripts_path / "config_simulation.yaml"

# define geography, let's run the first 20 super areas of london
geography = Geography.from_file({"super_area": london_areas})
#geography = Geography.from_file({"region": ["North East"]})

# add buildings
geography.hospitals = Hospitals.for_geography(geography)
geography.companies = Companies.for_geography(geography)
geography.schools = Schools.for_geography(geography)
geography.universities = Universities.for_super_areas(geography.super_areas)
geography.care_homes = CareHomes.for_geography(geography)
## generate world
world = generate_world_from_geography(geography, include_households=True)

## some leisure activities
world.pubs = Pubs.for_geography(geography)
world.cinemas = Cinemas.for_geography(geography)
world.groceries = Groceries.for_geography(geography)
leisure = generate_leisure_for_config(world, config_filename=config_path)
leisure.distribute_social_venues_to_areas(
    areas=world.areas, super_areas=world.super_areas
)  # this assigns possible social venues to people.
travel = Travel()
travel.initialise_commute(world)
t2 = time.time()
print(f"Took {t2 -t1} seconds to run.")
# save the world to hdf5 to load it later
world_name = "tiny_world"
world.to_hdf5(f"{world_name}.hdf5")


print("Done :)")

default_super_areas_foldername = (
    paths.data_path / "plotting/super_area_boundaries/"
)

def plot_map(
    super_areas,
    world_name=world_name,
    super_areas_foldername=default_super_areas_foldername

):

    import matplotlib.pyplot as plt

    import geopandas as gp
    import geoplot as gplt
    import geoplot.crs as gcrs

    map_super_areas = gp.read_file(default_super_areas_foldername)
    map_super_areas = map_super_areas.to_crs(epsg=4326)

    map_super_areas["contained"] = np.in1d(map_super_areas["msoa11cd"], super_areas).astype(int)

    fig, ax = plt.subplots()
    gplt.choropleth(
        map_super_areas, hue="contained",
        cmap="Reds", legend=True, edgecolor="black", ax=ax, linewidth=0.2
    )

    plt.savefig(f"{world_name}.png")

try:
    plot_map(london_areas)
except Exception as e:
    print(e)
    print("Can\'t save map")