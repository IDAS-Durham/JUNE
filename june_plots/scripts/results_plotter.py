import os
import argparse
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')

from results import ResultsPlots

plt.style.use(['science'])
plt.style.reload_library()

# putting this here for reference
default_csv_dir = '/cosma7/data/durham/dc-sedg2/june_runs/results_beyonce/baseline/summaries/england/iteration_01'

class ResultsPlotter:
    """
    Plotter for JUNE runs, for results section of paper.

    Parameters
    ----------
    csv_dir (str): Directory containing JUNE output csv files
            world_summary_xxx.csv
            regional_summary_xxx.csv
            age_summary_xxx.csv
    run_no (int): number of the run to plot as integer, i.e. run 005 would be run_no=5
    """
    
    def __init__(self, csv_dir, run_no):       
        self.csv_dir = csv_dir
        self.run_no = run_no

    def plot_results(
        self,
        save_dir: str = '../plots/results/',
        dpi: int = 300
    ):
        "Make all results plots"

        os.makedirs(save_dir, exist_ok=True)

        print("Setting up results plots")

        results_plots = ResultsPlots(self.csv_dir, self.run_no)

        print("Loading real world data")
        results_plots.load_sitrep_data()

        print("Loading JUNE data")
        results_plots.load_csv_files()
        results_plots.get_start_end_date()

        print("Plotting England summaries")
        results_plots.plot_england_results()
        plt.savefig(save_dir + f'/england_plots_{self.run_no:03}.pdf', dpi=dpi, bbox_inches='tight')

        print("Plotting regional summaries")
        results_plots.plot_regional_hospital_admissions()
        plt.savefig(save_dir + f'/regional_admissions_plots_{self.run_no:03}.pdf', dpi=dpi, bbox_inches='tight')

        results_plots.plot_regional_hospital_deaths()
        plt.savefig(save_dir + f'/regional_deaths_plots_{self.run_no:03}.pdf', dpi=dpi, bbox_inches='tight')

        print("Plotting age stratified summaries")
        results_plots.plot_age_stratified_results()
        plt.savefig(save_dir + f'/england_age_stratified_plots_{self.run_no:03}.pdf', dpi=dpi, bbox_inches='tight')

        print("Plotting percentage cumulative infections")
        results_plots.plot_cumulative_infected()
        plt.savefig(save_dir + f'/cumulative_infected_plot_{self.run_no:03}.pdf', dpi=dpi, bbox_inches='tight')

        print("All results plotting finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--csv_dir",
        help="Absolute directory to results csv files",
        default=default_csv_dir
    )

    parser.add_argument(
        "--run_no",
        help="Run number as integer, i.e. run 003 would be --run_no=3",
        default=3,
        type=int
    )

    args = parser.parse_args()

    plotter = ResultsPlotter(args.csv_dir, args.run_no)
    plotter.plot_results()
