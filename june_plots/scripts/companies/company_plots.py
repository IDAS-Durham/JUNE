import numpy as np
import pandas as pd
import time
from datetime import datetime, timedelta
import argparse
import os
import mpu
import matplotlib.pyplot as plt
from collections import defaultdict

from june import paths

default_size_nr_file = (
    paths.data_path / "input/companies/company_size_2019.csv"
)
default_sector_nr_per_msoa_file = (
    paths.data_path / "input/companies/company_sector_2011.csv"
)
default_sex_per_sector_per_superarea_file = (
    paths.data_path / "input/work/industry_by_sex_ew.csv"
)

class CompanyPlots:

    def __init__(self, world, colors):
        self.world = world
        self.colors = colors

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
        for super_area in self.world.super_areas:
            super_areas.append(super_area.name)

        world_company_sizes_binned = list(self.company_sizes[self.company_sizes['MSOA'].isin(super_areas)].sum()[1:])

        JUNE_company_sizes_binned, _ = np.histogram(JUNE_company_sizes, bins=size_brackets)

        bin_widths = []
        for i in range(len(size_brackets)-1):
            bin_widths.append(size_brackets[i+1]-size_brackets[i])

        f, ax = plt.subplots()
        ax.bar(size_brackets[:-1], world_company_sizes_binned, width=bin_widths, align='edge', alpha=0.7, label='ONS sizes', color=self.colors['ONS'])
        ax.bar(size_brackets[:-1], JUNE_company_sizes_binned, width=bin_widths, align='edge', alpha=0.7, label='JUNE sizes', color=self.colors['JUNE'])
        ax.set_xlim((-5,np.max(size_brackets)))
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
        for super_area in self.world.super_areas:
            super_areas.append(super_area.name)

        world_company_sizes_binned = list(self.company_sizes[self.company_sizes['MSOA'].isin(super_areas)].sum()[1:])

        JUNE_company_workers_binned, _ = np.histogram(JUNE_company_workers, bins=size_brackets)

        bin_widths = []
        for i in range(len(size_brackets)-1):
            bin_widths.append(size_brackets[i+1]-size_brackets[i])

        f, ax = plt.subplots()
        ax.bar(size_brackets[:-1], world_company_sizes_binned, width=bin_widths, align='edge', alpha=0.7, label='ONS sizes', color=self.colors['ONS'])
        ax.bar(size_brackets[:-1], JUNE_company_workers_binned, width=bin_widths, align='edge', alpha=0.7, label='JUNE workers', color=self.colors['JUNE'])
        ax.set_xlim((-5,np.max(size_brackets)))
        ax.set_yscale('log')
        ax.set_ylabel('Frequency')
        ax.set_xlabel('Number of people')
        ax.legend()

        return ax

    def plot_company_sectors(self):
        "Plotting company sector statistics"
        
        JUNE_company_sectors = []
        for company in self.world.companies:
            JUNE_company_sectors.append(company.sector)

        size_brackets = [0]
        for size in self.company_sizes.columns[2:]:
            size_brackets.append(int(size.split('-')[0]))
        size_brackets.append(1500)

        super_areas = []
        for super_area in self.world.super_areas:
            super_areas.append(super_area.name)

        world_company_sectors_binned = list(self.company_sectors[self.company_sectors['MSOA'].isin(super_areas)].sum()[1:])
        sector_brackets = self.company_sectors.columns[1:]

        JUNE_company_sectors_unique, JUNE_company_sectors_counts = np.unique(JUNE_company_sectors, return_counts=True)
        JUNE_company_sectors_binned = np.zeros(len(sector_brackets))
        for idx, sector in enumerate(sector_brackets):
            try:
                JUNE_company_sectors_binned[idx] = JUNE_company_sectors_counts[np.where(JUNE_company_sectors_unique == sector)[0][0]]
            except:
                pass

        x = np.arange(len(sector_brackets))

        f, ax = plt.subplots()
        ax.bar(x, world_company_sectors_binned, align='center', alpha=0.7, label='ONS', color=self.colors['ONS'])
        ax.bar(x, JUNE_company_sectors_binned, align='center', alpha=0.7, label='JUNE', color=self.colors['JUNE'])
        ax.set_ylabel('Frequency')
        ax.set_xlabel('Company sector')
        ax.set_xticks(x)
        ax.set_xticklabels(sector_brackets)
        ax.legend()

        return ax

    def plot_sector_by_sex(
            self,
            sector_by_sex_filename = default_sex_per_sector_per_superarea_file,
    ):
        "Plotting sector by sex distributions"

        sex_per_sector = pd.read_csv(sector_by_sex_filename)

        areas = []
        for area in world.areas:
            areas.append(area.name)

        sex_per_sector = sex_per_sector[sex_per_sector['oareas'].isin(areas)]

        JUNE_male_dict = defaultdict(int)
        JUNE_female_dict = defaultdict(int)
        for person in world.people:
            if person.sector is not None:
                if person.sex == 'f':
                    JUNE_female_dict[person.sector] += 1
                else:
                    JUNE_male_dict[person.sector] += 1

        m_columns = [col for col in sex_per_sector.columns.values if "m " in col]
        m_columns.remove("m all")
        m_columns.remove("m R S T U")
        f_columns = [col for col in sex_per_sector.columns.values if "f " in col]
        f_columns.remove("f all")
        f_columns.remove("f R S T U")

        male_dict = defaultdict(int)
        female_dict = defaultdict(int)
        for column in m_columns:
            male_dict[column.split(' ')[1]] = np.sum(sex_per_sector[column])
        for column in f_columns:
            female_dict[column.split(' ')[1]] = np.sum(sex_per_sector[column])

        sector_dict = {
                    (idx + 1): col.split(" ")[-1] for idx, col in enumerate(m_columns)
                }

        sectors = []
        male_sector = []
        female_sector = []
        JUNE_male_sector = []
        JUNE_female_sector = []
        for key in sector_dict:
            sectors.append(sector_dict[key])
            male_sector.append(male_dict[sector_dict[key]])
            female_sector.append(female_dict[sector_dict[key]])
            JUNE_male_sector.append(JUNE_male_dict[sector_dict[key]])
            JUNE_female_sector.append(JUNE_female_dict[sector_dict[key]])

        x = np.arange(len(sectors))
        width = 0.35

        f, ax = plt.subplots()
        ax.bar(x+width/2, JUNE_female_sector, width, alpha=0.7, label='Female', color=self.colors['female'])
        ax.bar(x-width/2, JUNE_male_sector, width, label='Male', color=self.colors['male'])
        ax.set_ylabel('Frequency')
        ax.set_xlabel('Company sector')
        ax.set_xticks(x)
        ax.set_xticklabels(sectors)
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
        ax.scatter(work_travel_male_bins[1:], work_travel_male_binned, label='Male',s=10,color=self.colors['male'])
        ax.set_ylabel('Frequency')
        ax.set_xlabel('Company sector')
        ax.set_xticks(x)
        ax.set_xticklabels(sectors)
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
        ax.scatter(work_travel_male_bins[1:], work_travel_male_binned, label='Male',s=10,color=self.colors['male'])
        ax.scatter(work_travel_female_bins[1:], work_travel_female_binned, label='Female',s=10,color=self.colors['female'])
        ax.set_xlabel('Distance to work (km)')
        ax.set_ylabel('Frequency')
        ax.set_yscale('log')
        ax.legend()

        return ax
