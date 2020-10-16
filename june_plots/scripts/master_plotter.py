import numpy as np
import pandas as pd
import time
from pathlib import Path
from datetime import datetime, timedelta
import argparse
import os
import matplotlib.pyplot as plt

from june.hdf5_savers import generate_world_from_hdf5
from june_plots.scripts.policy import PolicyPlots
from june_plots.scripts.leisure import LeisurePlots
from june_plots.scripts.companies import CompanyPlots
from june_plots.scripts.households import HouseholdPlots
from june_plots.scripts.care_homes import CareHomePlots
from june_plots.scripts.schools import SchoolPlots
from june_plots.scripts.commute import CommutePlots
from june_plots.scripts.contact_matrix import ContactMatrixPlots
from june_plots.scripts.life_expectancy import LifeExpectancyPlots
from june_plots.scripts.demography import DemographyPlots
from june_plots.scripts.health_index import HealthIndexPlots
from june_plots.scripts.university import UniversityPlots


plt.style.use(['science'])
plt.style.reload_library()

default_world_filename = 'world.hdf5'
default_output_plots_path = Path(__file__).absolute().parent.parent / "plots"

class Plotter:
    """
    Master plotting script for paper and validation plots
    Parameters
    ----------
    world
        Preloaded world which can also be passed from the master plotting script
    """

    def __init__(self, world):
        self.world = world

    @classmethod
    def from_file(
            cls,
            world_filename: str = default_world_filename,
    ):
        world = generate_world_from_hdf5(world_filename)

        return Plotter(world)

    def plot_demography(
            self,
            save_dir: Path = default_output_plots_path / "demography",
    ):
        "Make all demography plots"

        save_dir.mkdir(exist_ok=True, parents=True)
        
        print ("Setting up demography plots")
        demography_plots = DemographyPlots(self.world)
        
        print ("Plotting age distribution")
        fig, ax = demography_plots.plot_age_distribution()
        plt.plot()
        plt.savefig(save_dir / 'age_distribution.png', dpi=150, bbox_inches='tight')

        print ("Plotting population density")
        population_density_plot = demography_plots.plot_population_density()
        population_density_plot.plot()
        plt.savefig(save_dir / 'population_density.png', dpi=150, bbox_inches='tight')
        
        london_superareas_path = (
            Path(__file__).absolute().parent.parent.parent / "scripts/london_areas.txt"
        )
        london_superareas = pd.read_csv(london_superareas_path,names=["msoa"])["msoa"]
        
        super_areas = demography_plots.process_socioeconomic_index_for_super_areas(
            london_superareas
        )
        mean_plot = demography_plots.plot_socioeconomic_index(super_areas,column="centile_mean")
        mean_plot.plot()
        plt.savefig(save_dir / 'london_socioeconomic_mean.png', dpi=150, bbox_inches='tight')
        mean_plot = demography_plots.plot_socioeconomic_index(super_areas,column="centile_std")
        mean_plot.plot()
        plt.savefig(save_dir / 'london_socioeconomic_stdev.png', dpi=150, bbox_inches='tight')

        super_areas = demography_plots.process_socioeconomic_index_for_world()
        mean_plot = demography_plots.plot_socioeconomic_index(super_areas,column="centile_mean")
        mean_plot.plot()
        plt.savefig(save_dir / 'world_socioeconomic_mean.png', dpi=150, bbox_inches='tight')
        mean_plot = demography_plots.plot_socioeconomic_index(super_areas,column="centile_std")
        mean_plot.plot()
        plt.savefig(save_dir / 'world_socioeconomic_stdev.png', dpi=150, bbox_inches='tight')

        print("Plotting ethnicity")
        ethnicity_plot = demography_plots.plot_ethnicity_distribution()
        ethnicity_plot.plot()
        plt.savefig(save_dir / "ethnicity_distribution.png", dpi=150, bbox_inches="tight")


    def plot_commute(
            self,
            save_dir: Path = default_output_plots_path / "commute",
    ):
        "Make all commute plots"

        save_dir.mkdir(exist_ok=True, parents=True)

        print ("Setting up commute plots")
        commute_plots = CommutePlots(self.world)

        print ("Plotting internal exteral numbers")
        internal_external_numbers_plot = commute_plots.plot_internal_external_numbers()
        internal_external_numbers_plot.plot()
        plt.savefig(save_dir / 'internal_external.png', dpi=150, bbox_inches='tight')

        print ("Processing Newcastle areas")
        internal_commute_areas, external_commute_areas = commute_plots.process_internal_external_areas(
            city_to_plot = "Newcastle upon Tyne"
        )

        if internal_commute_areas is not None:
            print ("Plotting Newcastle internal areas")
            commute_areas_plot = commute_plots.plot_commute_areas(internal_commute_areas)
            commute_areas_plot.plot()
            plt.savefig(save_dir / 'Newcastle_internal_commute.png', dpi=150, bbox_inches='tight')

        if external_commute_areas is not None:
            print ("Plotting Newcastle external areas")
            commute_areas_plot = commute_plots.plot_commute_areas(external_commute_areas)
            commute_areas_plot.plot()
            plt.savefig(save_dir / 'Newcastle_external_commute.png', dpi=150, bbox_inches='tight')
            

        print ("Processing London areas")
        internal_commute_areas, external_commute_areas = commute_plots.process_internal_external_areas(
            city_to_plot = "London"
        )

        if internal_commute_areas is not None:
            print ("Plotting London internal areas")
            commute_areas_plot = commute_plots.plot_commute_areas(internal_commute_areas)
            commute_areas_plot.plot()
            plt.savefig(save_dir / 'London_internal_commute.png', dpi=150, bbox_inches='tight')

        if external_commute_areas is not None:
            print ("Plotting London external areas")
            commute_areas_plot = commute_plots.plot_commute_areas(external_commute_areas)
            commute_areas_plot.plot()
            plt.savefig(save_dir / 'London_external_commute.png', dpi=150, bbox_inches='tight')
        

    def plot_households(
            self,
            save_dir: Path = default_output_plots_path / "households"
    ):
        "Make all household plots"
        
        save_dir.mkdir(exist_ok=True, parents=True)
        
        print("Setting up household plots")
        household_plots = HouseholdPlots(self.world)

        household_plots.plot_all_household_plots(save_dir=save_dir)


    def plot_companies(
            self,
            save_dir: Path = default_output_plots_path / "companies"
    ):
        "Make all company plots"
        save_dir.mkdir(exist_ok=True, parents=True)

        print ("Setting up company plots")

        company_plots = CompanyPlots(self.world)

        print ("Loading company data")
        company_plots.load_company_data()

        print ("Plotting company sizes")
        company_sizes_plot = company_plots.plot_company_sizes()
        company_sizes_plot.plot()
        plt.savefig(save_dir / 'company_sizes.png', dpi=150, bbox_inches='tight')

        print ("Plotting company workers")
        company_workers_plot = company_plots.plot_company_workers()
        company_workers_plot.plot()
        plt.savefig(save_dir / 'company_workers.png', dpi=150, bbox_inches='tight')

        print ("Plotting company sectors")
        company_sectors_plot = company_plots.plot_company_sectors()
        company_sectors_plot.plot()
        plt.savefig(save_dir / 'company_sectors.png', dpi=150, bbox_inches='tight')

        print ("Plotting work distance travel")
        work_distance_travel_plot = company_plots.plot_work_distance_travel()
        work_distance_travel_plot.plot()
        plt.savefig(save_dir / 'work_distance_travel.png', dpi=150, bbox_inches='tight')
        
    
    def plot_leisure(
            self,
            save_dir: Path = default_output_plots_path / "leisure"
    ):
        "Make all leisure plots"

        save_dir.mkdir(exist_ok=True, parents=True)

        print ("Setting up leisure plots")
        leisure_plots = LeisurePlots(self.world)

        print ("Running poisson process")
        leisure_plots.run_poisson_process()

        print ("Plotting week probabilities")
        week_probabilities_plot = leisure_plots.plot_week_probabilities()
        week_probabilities_plot.plot()
        plt.savefig(save_dir / 'week_probabilities.png', dpi=150, bbox_inches='tight')
        
        plt.clf()
        print ("Plotting leisure time spent")
        leisure_time_spent_plot = leisure_plots.plot_leisure_time_spent()
        leisure_time_spent_plot.plot()
        plt.savefig(save_dir / 'leisure_time_spent.png', dpi=150, bbox_inches='tight')
        
    def plot_policies(
            self,
            save_dir: Path = default_output_plots_path / "policy"
    ):
        "Make all policy plots"

        save_dir.mkdir(exist_ok=True, parents=True)

        print ("Setting up policy plots")
        policy_plots = PolicyPlots(self.world)

        print ("Plotting restaurant reopening")
        restaurant_reopening_plot = policy_plots.plot_restaurant_reopening()
        restaurant_reopening_plot.plot()
        plt.savefig(save_dir / 'restaurant_reopening.png', dpi=150, bbox_inches='tight')

        print ("Plotting school reopening")
        school_reopening_plot = policy_plots.plot_school_reopening()
        school_reopening_plot.plot()
        plt.savefig(save_dir / 'school_reopening.png', dpi=150, bbox_inches='tight')

        print ("Plotting beta fraction")
        beta_fraction_plot = policy_plots.plot_beta_fraction()
        beta_fraction_plot.plot()
        plt.savefig(save_dir / 'beta_fraction.png', dpi=150, bbox_inches='tight')

        print ("All policy plots finished")

    def plot_care_homes(self,
        save_dir: Path = default_output_plots_path / "care_homes"
    ):
        "Make all care home plots"
        save_dir.mkdir(exist_ok=True, parents=True)

        print("Setting up care home plots")
        care_plots = CareHomePlots(self.world)

        print("Plotting age distribution in care homes")
        care_plots.load_care_home_data()
        care_age_plot = care_plots.plot_age_distribution()
        care_age_plot.plot()
        plt.savefig(save_dir / 'age_distribution.png', dpi=150, bbox_inches='tight')

    def plot_schools(
        self,
        save_dir: Path = default_output_plots_path / "schools"
    ):
        """Make all school plots"""
        save_dir.mkdir(exist_ok=True, parents=True)

        print("Setting up school plots")
        school_plots = SchoolPlots(self.world)
        school_plots.load_school_data()

        school_size_plot = school_plots.plot_school_sizes()        
        school_size_plot.plot()
        plt.savefig(save_dir / 'school_sizes.png', dpi=150, bbox_inches='tight')
        
        student_teacher_ratio_plot = school_plots.plot_student_teacher_ratio()
        student_teacher_ratio_plot.plot()
        plt.savefig(save_dir / 'student_teacher_ratios.png', dpi=150, bbox_inches='tight')

        distance_to_school_plot = school_plots.plot_distance_to_school()
        distance_to_school_plot.plot()

        print(save_dir / 'distance_to_school.png')
        plt.savefig(save_dir / 'distance_to_school.png', dpi=150, bbox_inches='tight')      

    def plot_contact_matrices(
            self,
            save_dir: Path = default_output_plots_path / "contact_matrices"
    ):
        "Plot contact matrices pre-lockdown and during lockdown."

        save_dir.mkdir(exist_ok=True, parents=True)

        pre_lockdown_date = datetime(2020, 3, 1)
        during_lockdown_date = datetime(2020, 4, 15)

        print("Setting up contact matrix plots")
        contact_matrix_plots = ContactMatrixPlots(self.world)

        print("Loading world data")
        contact_matrix_plots.load_world_data()

        print("Plotting pre-lockdown contact matrices")
        contact_matrix_plots.calculate_all_contact_matrices(pre_lockdown_date)
        contact_matrices = contact_matrix_plots.contact_matrices
        for location, contact_matrix in contact_matrices.items():
            contact_matrix_plots.plot_contact_matrix(contact_matrix, location)
            plt.savefig(save_dir / f'contact_matrix_{location}_prelockdown.png', dpi=150, bbox_inches='tight')

        print("Plotting during lockdown contact matrices")
        contact_matrix_plots.calculate_all_contact_matrices(during_lockdown_date)
        contact_matrices = contact_matrix_plots.contact_matrices
        for location, contact_matrix in contact_matrices.items():
            contact_matrix_plots.plot_contact_matrix(contact_matrix, location)
            plt.savefig(save_dir / f'contact_matrix_{location}_lockdown.png', dpi=150, bbox_inches='tight')

    def plot_life_expectancy(
        self,
        save_dir: Path = default_output_plots_path / "life_expectancy"
    ):
        "Plot socioeconomic_index vs. life_expectancy"

        save_dir.mkdir(exist_ok=True, parents=True)

        print ("Setting up life expectancy plots")
        le_plots = LifeExpectancyPlots()

        le_plots.load_geography_data()
        le_plots.load_iomd()
        le_plots.load_life_expectancy()

        print ("Plotting life expectancy")
        le_plot = le_plots.plot_life_expectancy_socioecon_index()
        le_plot.plot()
        plt.savefig(save_dir / "socioecon_life_expectancy.png", dpi=150, bbox_inches="tight")
    
    def plot_health_index(
        self,
        save_dir: Path = default_output_plots_path / "health_index"
        
    ):
        "Plot socioeconomic_index vs. life_expectancy"
        save_dir.mkdir(exist_ok=True, parents=True)

        print ("Setting up health index plots")
        hi_plots = HealthIndexPlots()

        print ("Plotting seroprevalence")
        prevalence_plot = hi_plots.sero_prevalence_plot()
        prevalence_plot.plot()
        plt.savefig(save_dir / "prevalence_plots.png", dpi=150, bbox_inches="tight")

        print ("Plotting rates")
        rates_plot = hi_plots.rates_plot()
        rates_plot.plot()
        plt.savefig(save_dir / "rates.png", dpi=150, bbox_inches="tight")

        print ("Plotting infectiousness")
        infectiousness_plot = hi_plots.infectiousness()
        infectiousness_plot.plot()
        plt.savefig(save_dir / "infectiousness.png", dpi=150, bbox_inches="tight")

    def plot_universities(self, save_dir: Path = default_output_plots_path / "universities"):
        save_dir.mkdir(exist_ok=True, parents=True)
        uni_plots = UniversityPlots(world=self.world)
        uni_plots.load_univeristy_data()
        if uni_plots.no_uni:
            return
        print("Plotting uni students household types")
        household_type_plot = uni_plots.plot_students_household_type_histogram()
        household_type_plot.plot()
        plt.savefig(save_dir / "household_type_hist.png", dpi=150, bbox_inches="tight")

        print("Plotting uni students household locations")
        uni_map = uni_plots.plot_where_students_live()
        uni_map.plot()
        plt.savefig(save_dir / "student_household_locations.png", dpi=150, bbox_inches="tight")


    def plot_all(self):
        print ("Plotting the world")
        self.plot_commute()
        self.plot_demography()
        self.plot_companies()
        self.plot_households()
        self.plot_leisure()
        self.plot_policies()
        self.plot_care_homes()
        self.plot_schools()
        self.plot_contact_matrices()
        self.plot_life_expectancy()
        self.plot_health_index()
        self.plot_universities()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Plotter for JUNE's world.")

    parser.add_argument(
        "-w",
        "--world_filename",
        help="Relative directory to world file",
        required=False,
        default = default_world_filename
    )
    parser.add_argument(
        "-q",
        "--households",
        help="Plot only households",
        required=False,
        default = False,
        action="store_true"
    )
    parser.add_argument(
        "-c",
        "--contact_matrix",
        help="Plot only contact matrices",
        required=False,
        default=False
    )
    parser.add_argument(
        "-d",
        "--demography",
        help="Plot only demography",
        required=False,
        default=False,
        action="store_true"
    )
    parser.add_argument(
        "-u",
        "--universities",
        help="Plot only universities",
        required=False,
        default=False,
        action="store_true"
    )

    args = parser.parse_args()
    plotter = Plotter.from_file(args.world_filename)
    if args.households:
        plotter.plot_households()
    elif args.contact_matrix:
        plotter.plot_contact_matrices()
    elif args.demography:
        plotter.plot_demography()
    elif args.universities:
        plotter.plot_universities()
    else:
        plotter.plot_all()
