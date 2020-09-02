import numpy as np
import pandas as pd
from typing import Optional
import matplotlib.pyplot as plt

from june.demography.demography import (
    load_age_and_sex_generators_for_bins,
    Demography,
    Population,
)
from june.paths import data_path
from june.hdf5_savers import generate_world_from_hdf5
from june.groups import Households

from camps.distributors import CampHouseholdDistributor
from camps.geography import CampGeography
from camps.paths import camp_data_path
from camps.world import CampWorld


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


def generate_empty_world(filter_key: Optional[dict]=None):
    geo = CampGeography.from_file(
        filter_key=filter_key,
        hierarchy_filename=area_mapping_filename,
        area_coordinates_filename=area_coordinates_filename,
        super_area_coordinates_filename=super_area_coordinates_filename,
    )
    world = CampWorld()
    world.areas = geo.areas
    world.super_areas = geo.super_areas
    world.people = Population()
    return world

def populate_world(world: CampWorld):
    """
    Populates the world. For each super area, we initialize a population
    following the data's age and sex distribution. We then split the population
    into the areas by taking the ratio of the area residents to the total super area
    population. Kids and adults are splited separately to keep a balanced population.
    """
    super_area_names = [super_area.name for super_area in world.super_areas]
    age_sex_generators = load_age_and_sex_generators_for_bins(age_structure_filename)
    demography = Demography(
        age_sex_generators=age_sex_generators, area_names=super_area_names
    )
    for super_area in world.super_areas:
        population = demography.populate(
            super_area.name, ethnicity=False, socioecon_index=False, comorbidity=False
        )
        np.random.shuffle(population.people)
        world.people.extend(population)
        # create two lists to distribute even among areas
        adults = [person for person in population if person.age >= 17]
        kids = [person for person in population if person.age < 17]
        n_kids = len(kids)
        n_adults = len(adults)
        residents_data = {}
        total_residents = 0
        # note: the data that has age distributions and the data that has n_families does not match
        # so we need to do some rescaling
        for area in super_area.areas:
            residents_data[area.name] = area_residents_families_df.loc[area.name, "residents"]
            total_residents += residents_data[area.name]
        for area in super_area.areas:
            n_residents_data = residents_data[area.name]
            population_ratio = n_residents_data / total_residents 
            n_adults_area = int(
                np.round(population_ratio * n_adults)
            )
            n_kids_area = int(
                np.round(population_ratio * n_kids)
            )
            for _ in range(n_adults_area):
                if not adults:
                    break
                area.add(adults.pop())
            for _ in range(n_kids_area):
                if not kids:
                    break
                area.add(kids.pop())
        people_left = adults + kids
        if people_left:
            areas = np.random.choice(super_area.areas, size=len(people_left))
            for area in areas:
                area.add(people_left.pop())
    

def distribute_people_to_households(world: CampWorld):
    """
    Distributes the people in the world to households by using the CampHouseholdDistributor.
    """
    household_distributor = CampHouseholdDistributor(max_household_size=12)
    households_total = []
    for area in world.areas:
        area_data = area_residents_families_df.loc[area.name]
        n_families = int(area_data["families"])
        n_residents = int(area_data["residents"])
        n_families_adapted = int(np.round(len(area.people) / n_residents * n_families))
        area.households = household_distributor.distribute_people_to_households(
            area=area, n_families=n_families_adapted,
        )
        households_total += area.households
    world.households = Households(households_total)


def example_run(filter_key=None):
    world = generate_empty_world(filter_key=filter_key)
    populate_world(world)
    distribute_people_to_households(world)
    world.to_hdf5("camp.hdf5")

if __name__ == "__main__":
    example_run(filter_key = {"super_area" : ["CXB-219-C"]})
    # area coding example CXB-219-056
    # super area coding example CXB-219-C
    # region coding example CXB-219
