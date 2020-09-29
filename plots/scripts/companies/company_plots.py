import numpy as np
import pandas as pd
import time
from datetime import datetime, timedelta
import argparse
import os
import mpu
import matplotlib.pyplot as plt

from june import paths

default_size_nr_file = (
    paths.data_path / "input/companies/company_size_2019.csv"
)
default_sector_nr_per_msoa_file = (
    paths.data_path / "input/companies/company_sector_2011.csv"
)

class CompanyPlots:

    def __init__(self, world):
        self.world = world

    def load_company_data(
            self,
            company_size_filename = default_size_nr_file,
            company_sector_filename = default_sector_nr_per_msoa_file,
    ):
        "Loading company data for plotting"

        self.company_sizes = pd.read_csv(company_size_filename)
        self.company_sectors = pd.read_csv(company_sector_filename)

    def plot_company_sizes(self):
        "Plotting the size of companies"

        JUNE_company_sizes = []
        for company in self.world.companies:
            JUNE_company_sizes.append(company.n_workers_max)

        size_brackets = [0]
        for size in self.company_sizes.columns[2:]:
            size_brackets.append(int(size.split('-')[0]))
        size_brackets.append(1500)

        super_areas = []
        for super_area in world.super_areas:
            super_areas.append(super_area.name)

        world_company_sizes_binned = list(self.company_sizes[self.company_sizes['MSOA'].isin(super_areas)].sum()[1:])

        JUNE_company_sizes_binned, _ = np.histogram(JUNE_company_sizes, bins=size_brackets)

        bin_widths = []
        for i in range(len(size_brackets)-1):
            bin_widths.append(size_brackets[i+1]-size_brackets[i])

        f, ax = plt.subplots()
        ax.bar(size_brackets[:-1], JUNE_company_sizes_binned, width=bin_widths, align='edge', alpha=0.7, label='JUNE sizes')
        ax.bar(size_brackets[:-1], world_company_sizes_binned, width=bin_widths, align='edge', alpha=0.7, label='NOMIS sizes')
        ax.set_xlim((-5,np.max(JUNE_company_sizes)))
        ax.set_yscale('log')
        ax.set_ylabel('Frequency')
        ax.set_xlabel('Number of people')
        ax.legend()

        return ax

    def plot_company_workers(self):
        "Plotting company worker statistics"

        JUNE_company_workers = []
        for company in self.world.companies:
            JUNE_company_workers.append(len(company.workers))
        
        size_brackets = [0]
        for size in self.company_sizes.columns[2:]:
            size_brackets.append(int(size.split('-')[0]))
        size_brackets.append(1500)

        super_areas = []
        for super_area in world.super_areas:
            super_areas.append(super_area.name)

        world_company_sizes_binned = list(company_sizes[self.company_sizes['MSOA'].isin(super_areas)].sum()[1:])

        JUNE_company_workers_binned, _ = np.histogram(JUNE_company_workers, bins=size_brackets)

        bin_widths = []
        for i in range(len(size_brackets)-1):
            bin_widths.append(size_brackets[i+1]-size_brackets[i])

        f, ax = plt.subplots()
        ax.bar(size_brackets[:-1], JUNE_company_workers_binned, width=bin_widths, align='edge', alpha=0.7, label='JUNE workers')
        ax.bar(size_brackets[:-1], world_company_sizes_binned, width=bin_widths, align='edge', alpha=0.7, label='NOMIS sizes')
        ax.set_xlim((-5,np.max(JUNE_company_sizes)))
        ax.set_yscale('log')
        ax.set_ylabel('Frequency')
        ax.set_xlabel('Number of people')
        ax.legend()

        return ax

    def plot_company_sectors(self):
        "Plotting company sector statistics"
        
        JUNE_company_sectors = []
        for company in world.companies:
            JUNE_company_sectors.append(company.sector)

        size_brackets = [0]
        for size in self.company_sizes.columns[2:]:
            size_brackets.append(int(size.split('-')[0]))
        size_brackets.append(1500)

        super_areas = []
        for super_area in self.world.super_areas:
            super_areas.append(super_area.name)

        world_company_sectors_binned = list(company_sectors[self.company_sectors['MSOA'].isin(super_areas)].sum()[1:])
        sector_brackets = self.company_sectors.columns[1:]

        JUNE_company_sectors_unique, JUNE_company_sectors_counts = np.unique(JUNE_company_sectors, return_counts=True)

        x = np.arange(len(sector_brackets))

        f, ax = plt.subplots()
        ax.bar(x, JUNE_company_sectors_binned, align='center', alpha=0.7, label='JUNE')
        ax.bar(x, world_company_sectors_binned, align='center', alpha=0.7, label='NOMIS')
        ax.set_ylabel('Frequency')
        ax.set_xlabel('Company sector')
        ax.set_xticks(x)
        ax.set_xticklabels(sector_brackets)
        ax.legend()

        return ax

    def plot_work_distance_travel(self):
        "Plotting distance travelled to work by sex"

        residence_super_areas_male = []
        residence_super_areas_female = []
        work_super_areas_male = []
        work_super_areas_female = []
        for person in self.world.people:
            if person.work_super_area is not None:
                if person.sex == 'f':
                    residence_super_areas_female.append(person.super_area.coordinates)
                    work_super_areas_female.append(person.work_super_area.coordinates)
                else:
                    residence_super_areas_male.append(person.super_area.coordinates)
                    work_super_areas_male.append(person.work_super_area.coordinates)

        work_travel_male = []
        for idx, coord in enumerate(residence_super_areas_male):
            work_travel_male.append(mpu.haversine_distance((coord[0], coord[1]), (work_super_areas_male[idx][0], work_super_areas_male[idx][1])))
        work_travel_female = []
        for idx, coord in enumerate(residence_super_areas_female):
            work_travel_female.append(mpu.haversine_distance((coord[0], coord[1]), (work_super_areas_female[idx][0], work_super_areas_female[idx][1])))

        work_travel_male_binned, work_travel_male_bins = np.histogram(work_travel_male, bins=100)
        work_travel_female_binned, work_travel_female_bins = np.histogram(work_travel_female, bins=100)

        f, ax = plt.subplots()
        ax.scatter(work_travel_male_bins[1:], work_travel_male_binned, label='Male')
        ax.scatter(work_travel_female_bins[1:], work_travel_female_binned, label='Female')
        ax.set_xlabel('Distance to work (km)')
        ax.set_ylabel('Frequency')
        ax.set_yscale('log')
        ax.legend()

        return ax
