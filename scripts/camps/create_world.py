import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from june.demography.geography import Geography
from june.demography.demography import (
    load_age_and_sex_generators_for_bins,
    Demography,
    Population,
)
from june.paths import data_path, camp_data_path
from june import World
from june.world import generate_world_from_hdf5
from june.distributors import HouseholdDistributor
from june.groups import Households


# area coding example CXB-219-056
# super area coding example CXB-219-C
# region coding example CXB-219

area_mapping_filename = camp_data_path / "input/geography/area_super_area_region.csv"
area_coordinates_filename = camp_data_path / "input/geography/area_coordinates.csv"
super_area_coordinates_filename = (
    camp_data_path / "input/geography/super_area_coordinates.csv"
)
age_structure_filename = (
    camp_data_path / "input/demography/age_structure_super_area.csv"
)
area_residents_families = (
    camp_data_path / "input/demography/area_residents_families.csv"
)
area_residents_families_df = pd.read_csv(area_residents_families)
area_residents_families_df.set_index("area", inplace=True)


geography = Geography.from_file(
    filter_key=None,#{"region": ["CXB-219"]},
    hierarchy_filename=area_mapping_filename,
    area_coordinates_filename=area_coordinates_filename,
    super_area_coordinates_filename=super_area_coordinates_filename,
)

super_area_names = [super_area.name for super_area in geography.super_areas]
age_sex_generators = load_age_and_sex_generators_for_bins(age_structure_filename)

demography = Demography(
    age_sex_generators=age_sex_generators, area_names=super_area_names
)

world = World()
world.areas = geography.areas
world.super_areas = geography.super_areas
world.people = Population()

# populate area with generators from super areas
for super_area in world.super_areas:
    population = demography.populate(
        super_area.name, ethnicity=False, socioecon_index=False
    )
    np.random.shuffle(population.people)
    world.people.extend(population)
    population_super_area = len(population)
    total_residents_in_super_area = 0
    n_residents_area = []
    for area in super_area.areas:
        n_residents = area_residents_families_df.loc[area.name, "residents"]
        n_residents_area.append(n_residents)
        total_residents_in_super_area += n_residents
    for i, area in enumerate(super_area.areas):
        n_residents = min(
            int(
                np.round(
                    n_residents_area[i]
                    / total_residents_in_super_area
                    * population_super_area
                )
            ),
            len(population),
        )
        for _ in range(n_residents):
            area.add(population.people.pop())
    if population.people:
        areas = np.random.choice(super_area.areas, size=len(population.people))
        for area in areas:
            area.add(population.people.pop())


# household population
household_distributor = HouseholdDistributor.from_file()
households_total = []
for area in world.areas:
    men_by_age, women_by_age = household_distributor._create_people_dicts(area)
    area_data = area_residents_families_df.loc[area.name]
    families = area_data["families"]
    residents = area_data["residents"]
    number_households = {
        "1 0 >=0 1 0": int(families), #int(families // 2),
        #">=2 0 >=0 2 0": int(families - families // 2),
    }
    area.households = household_distributor.distribute_people_to_households(
        men_by_age=men_by_age,
        women_by_age=women_by_age,
        area=area,
        number_households_per_composition=number_households,
        n_students=0,
        n_people_in_communal=0,
    )
    households_total += area.households
world.households = Households(households_total)
world.to_hdf5("camp.hdf5")

world = generate_world_from_hdf5("camp.hdf5")
