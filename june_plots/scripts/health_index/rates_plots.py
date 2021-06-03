import pandas as pd
import numpy as np
from pathlib import Path
import json
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.backends.backend_pdf import PdfPages

from june.epidemiology.infection.health_index.data_to_rates import (
    convert_to_intervals,
    Data2Rates,
    get_outputs_df,
)
from june.paths import data_path

health_index_data_path = data_path / "input/health_index"
ifr_imperial_file = data_path / "plotting/health_index/ifr_imperial.csv"
ifr_ward_file = data_path / "plotting/health_index/ifr_ward.csv"


def read_sitrep(file):
    df = pd.read_csv(file)
    df.set_index("Date", inplace=True)
    df.index = pd.to_datetime(df.index)
    df = df.loc[:"2020-07-08"]
    df = df.loc[df.Band != "Admissions_Total"]
    df = df.groupby(["Band"]).sum()
    # df = df.loc[:, "Admissions"]
    mapp = lambda band: band.split("_")[-1] if band != "Admissions_85+" else "85-99"
    df = df.rename(mapper=mapp)
    df = df.loc[df["Admissions"] != 0]
    df = df.loc[:, "Admissions"].to_frame()
    df.index = convert_to_intervals(df.index)
    df = df.sort_index()
    df = df.rename(mapper=revert_to_string)
    return df


def revert_to_string(age):
    a = age.left
    b = age.right
    return f"{a}-{b}"


def bin_deaths_dataframe(df, age_bins):
    ret = pd.DataFrame(index=age_bins)
    ret["male"] = [
        df.loc[age_bin.left : age_bin.right, "male"].sum() for age_bin in age_bins
    ]
    ret["female"] = [
        df.loc[age_bin.left : age_bin.right, "female"].sum() for age_bin in age_bins
    ]
    return ret


class RatesPlotter:
    def __init__(self, outputs_dict, colors, age_bins=None):
        self.rates = Data2Rates.from_file()
        self.colors = colors
        if age_bins is None:
            self.age_bins = self.rates.care_home_deaths_by_age_sex_df.index
        else:
            self.age_bins = pd.Index(age_bins)
        self.infected_ch_population = self.compute_ch_infections()
        self.infected_gp_population = self.compute_gp_infections()
        self._process_data_dfs()
        self._care_home_deaths_hospital_ratio = (
            self.rates.hospital_ch_deaths_by_age_sex_df.sum().sum()
            / self.rates.care_home_deaths_by_age_sex_df.sum().sum()
        )
        self.outputs_dict = {}
        for key, output_raw in outputs_dict.items():
            output_proc = output_raw.copy()
            output_proc = output_proc.clip(lower=0)
            self.outputs_dict[key] = output_proc / 100

    def _process_data_dfs(self):
        self.all_deaths = bin_deaths_dataframe(
            self.rates.all_deaths_by_age_sex_df, self.age_bins
        )
        self.ch_deaths = bin_deaths_dataframe(
            self.rates.care_home_deaths_by_age_sex_df, self.age_bins
        )
        self.hospital_ch_deaths = bin_deaths_dataframe(
            self.rates.hospital_ch_deaths_by_age_sex_df, self.age_bins
        )
        self.hospital_all_deaths = bin_deaths_dataframe(
            self.rates.all_hospital_deaths_by_age_sex, self.age_bins
        )
        self.hospital_gp_deaths = self.hospital_all_deaths - self.hospital_ch_deaths

        self.hospital_ch_admissions = bin_deaths_dataframe(
            self.rates.hospital_ch_admissions_by_age_sex_df, self.age_bins
        )
        self.hospital_gp_admissions = bin_deaths_dataframe(
            self.rates.hospital_gp_admissions_by_age_sex_df, self.age_bins
        )
        self.hospital_cocin_deaths = pd.read_csv(
            health_index_data_path / "hospital_deaths_by_age_sex.csv", index_col=0
        )
        self.hospital_cocin_deaths.index = convert_to_intervals(
            self.hospital_cocin_deaths.index
        )
        self.hospital_cocin_deaths = bin_deaths_dataframe(
            self.hospital_cocin_deaths, self.age_bins
        )
        self.hospital_cocin_admissions = pd.read_csv(
            health_index_data_path / "hospital_admissions_by_age_sex.csv", index_col=0
        )
        self.hospital_cocin_admissions.index = convert_to_intervals(
            self.hospital_cocin_admissions.index
        )
        self.hospital_cocin_admissions = bin_deaths_dataframe(
            self.hospital_cocin_admissions, self.age_bins
        )
        self.hospital_sitrep_admissions = read_sitrep(
            "/home/arnau/scratch/health_index_data/raw_data/sitrep_admissions.csv"
        )

    def compute_ch_infections(self):
        """
        Computes the number of infected people in the care home population in the specified age bins.
        """
        care_home_population_binned = self.rates.care_home_population_by_age_sex_df.groupby(
            pd.cut(
                self.rates.care_home_population_by_age_sex_df.index, bins=self.age_bins
            )
        ).sum()
        infected_care_home_population = (
            (care_home_population_binned - self.rates.care_home_deaths_by_age_sex_df)
            * self.rates.care_home_seroprevalence_by_age_df.values.flatten()[0]
            + self.rates.care_home_deaths_by_age_sex_df
        )
        return infected_care_home_population

    def compute_gp_infections(self):
        """
        Computes the number of infected people in the general population (non care-home) the specified age bins.
        """
        seroprev_single_age = pd.DataFrame(
            index=self.rates.population_by_age_sex_df.index
        )
        deaths_single_age = pd.DataFrame(
            index=self.rates.population_by_age_sex_df.index
        )
        seroprev_single_age["seroprevalence"] = [
            self.rates.seroprevalence_df.loc[age].values[0]
            for age in seroprev_single_age.index
        ]
        deaths_single_age["male"] = [
            self.rates._get_interpolated_value(
                df=self.rates.all_deaths_by_age_sex_df,
                age=age,
                sex="male",
                weight_mapper=self.rates.gp_mapper,
            )
            for age in deaths_single_age.index
        ]
        # substract care home deaths
        deaths_single_age["male"] -= [
            self.rates._get_interpolated_value(
                df=self.rates.care_home_deaths_by_age_sex_df,
                age=age,
                sex="male",
                weight_mapper=self.rates.ch_mapper,
            )
            for age in deaths_single_age.index
        ]
        deaths_single_age["female"] = [
            self.rates._get_interpolated_value(
                df=self.rates.all_deaths_by_age_sex_df,
                age=age,
                sex="female",
                weight_mapper=self.rates.gp_mapper,
            )
            for age in deaths_single_age.index
        ]
        # substract care home deaths
        deaths_single_age["female"] -= [
            self.rates._get_interpolated_value(
                df=self.rates.care_home_deaths_by_age_sex_df,
                age=age,
                sex="female",
                weight_mapper=self.rates.ch_mapper,
            )
            for age in deaths_single_age.index
        ]
        # substract care home population
        n_people = (
            self.rates.population_by_age_sex_df
            - self.rates.care_home_population_by_age_sex_df
        )
        infected_single_age = (
            n_people - deaths_single_age
        ) * seroprev_single_age.values + deaths_single_age
        infected_population = infected_single_age.groupby(
            pd.cut(infected_single_age.index, bins=self.age_bins)
        ).sum()
        return infected_population

    def compute_total_gp_deaths_by_age_sex(self, output_rates):
        dmales_gp = self.infected_gp_population["male"] * output_rates["gp_ifr_male"]
        dfemales_gp = (
            self.infected_gp_population["female"] * output_rates["gp_ifr_female"]
        )
        ret = pd.DataFrame(index=self.age_bins)
        ret["male_prediction"] = dmales_gp
        ret["female_prediction"] = dfemales_gp
        ret["male_data"] = self.all_deaths["male"] - self.ch_deaths["male"]
        ret["female_data"] = self.all_deaths["female"] - self.ch_deaths["female"]
        return ret

    def compute_total_ch_deaths_by_age_sex(self, output_rates):
        dmales_ch = self.infected_ch_population["male"] * output_rates["ch_ifr_male"]
        dfemales_ch = (
            self.infected_ch_population["female"] * output_rates["ch_ifr_female"]
        )
        ret = pd.DataFrame(index=self.age_bins)
        ret["male_prediction"] = dmales_ch
        ret["female_prediction"] = dfemales_ch
        ret["male_data"] = self.ch_deaths["male"]
        ret["female_data"] = self.ch_deaths["female"]
        return ret

    def compute_total_deaths_by_age_sex(self, output_rates):
        return self.compute_total_gp_deaths_by_age_sex(
            output_rates
        ) + self.compute_total_ch_deaths_by_age_sex(output_rates)

    def compute_gp_hospital_deaths_by_age_sex(self, output_rates):
        dmales_gp = (
            self.infected_gp_population["male"] * output_rates["gp_hospital_ifr_male"]
        )
        dfemales_gp = (
            self.infected_gp_population["female"]
            * output_rates["gp_hospital_ifr_female"]
        )
        ret = pd.DataFrame(index=self.age_bins)
        ret["male_prediction"] = dmales_gp
        ret["female_prediction"] = dfemales_gp
        ret["male_data"] = self.hospital_gp_deaths["male"]
        ret["female_data"] = self.hospital_gp_deaths["female"]
        return ret

    def compute_ch_hospital_deaths_by_age_sex(self, output_rates):
        dmales_ch = (
            self.infected_ch_population["male"] * output_rates["ch_hospital_ifr_male"]
        )
        dfemales_ch = (
            self.infected_ch_population["female"]
            * output_rates["ch_hospital_ifr_female"]
        )
        ret = pd.DataFrame(index=self.age_bins)
        ret["male_prediction"] = dmales_ch
        ret["female_prediction"] = dfemales_ch
        ret["male_data"] = self.hospital_ch_deaths["male"]
        ret["female_data"] = self.hospital_ch_deaths["female"]
        return ret

    def compute_total_hospital_deaths_by_age_sex(self, output_rates):
        return self.compute_gp_hospital_deaths_by_age_sex(
            output_rates
        ) + self.compute_ch_hospital_deaths_by_age_sex(output_rates)

    def compute_ch_home_deaths_by_age_sex(self, output_rates):
        dmales_ch = (
            self.infected_ch_population["male"] * output_rates["ch_home_ifr_male"]
        )
        dfemales_ch = (
            self.infected_ch_population["female"] * output_rates["ch_home_ifr_female"]
        )
        dmales = dmales_ch
        dfemales = dfemales_ch
        ret = pd.DataFrame(index=self.age_bins)
        ret["male_prediction"] = dmales
        ret["female_prediction"] = dfemales
        ret["male_data"] = self.ch_deaths["male"] - self.hospital_ch_deaths["male"]
        ret["female_data"] = (
            self.ch_deaths["female"] - self.hospital_ch_deaths["female"]
        )
        return ret

    def compute_gp_home_deaths_by_age_sex(self, output_rates):
        dmales_gp = (
            self.infected_gp_population["male"] * output_rates["gp_home_ifr_male"]
        )
        dfemales_gp = (
            self.infected_gp_population["female"] * output_rates["gp_home_ifr_female"]
        )
        dmales = dmales_gp
        dfemales = dfemales_gp
        ret = pd.DataFrame(index=self.age_bins)
        ret["male_prediction"] = dmales
        ret["female_prediction"] = dfemales
        ret["male_data"] = (
            self.all_deaths["male"]
            - self.ch_deaths["male"]
            - self.hospital_gp_deaths["male"]
        )
        ret["female_data"] = (
            self.all_deaths["female"]
            - self.ch_deaths["female"]
            - self.hospital_gp_deaths["female"]
        )
        return ret

    def compute_total_home_deaths_by_age_sex(self, output_rates):
        return self.compute_gp_home_deaths_by_age_sex(
            output_rates
        ) + self.compute_ch_home_deaths_by_age_sex(output_rates)

    def compute_gp_admissions_by_age_sex(self, output_rates):
        dmales = (
            self.infected_gp_population["male"] * output_rates["gp_admissions_male"]
        )
        dfemales = (
            self.infected_gp_population["female"] * output_rates["gp_admissions_female"]
        )
        ret = pd.DataFrame(index=self.age_bins)
        ret["male_prediction"] = dmales
        ret["female_prediction"] = dfemales
        ret["male_data"] = self.hospital_gp_admissions["male"]
        ret["female_data"] = self.hospital_gp_admissions["female"]
        return ret

    def compute_ch_admissions_by_age_sex(self, output_rates):
        dmales = (
            self.infected_ch_population["male"] * output_rates["ch_admissions_male"]
        )
        dfemales = (
            self.infected_ch_population["female"] * output_rates["ch_admissions_female"]
        )
        ret = pd.DataFrame(index=self.age_bins)
        ret["male_prediction"] = dmales
        ret["female_prediction"] = dfemales
        ret["male_data"] = self.hospital_ch_admissions["male"]
        ret["female_data"] = self.hospital_ch_admissions["female"]
        return ret

    def compute_total_admissions_by_age_sex(self, output_rates):
        return self.compute_gp_admissions_by_age_sex(
            output_rates
        ) + self.compute_ch_admissions_by_age_sex(output_rates)

    def compute_cocin_hospital_deaths_by_age_sex(self, output_rates):
        dmales = (
            self.infected_gp_population["male"] * output_rates["gp_hospital_ifr_male"]
        )
        dfemales = (
            self.infected_gp_population["female"]
            * output_rates["gp_hospital_ifr_female"]
        )
        dmales += (
            self.infected_ch_population["male"] * output_rates["ch_hospital_ifr_male"]
        )
        dfemales += (
            self.infected_ch_population["female"]
            * output_rates["ch_hospital_ifr_female"]
        )
        ret = pd.DataFrame(index=self.age_bins)
        ret["male_prediction"] = dmales
        ret["female_prediction"] = dfemales
        ret["male_data"] = self.hospital_cocin_deaths["male"]
        ret["female_data"] = self.hospital_cocin_deaths["female"]
        return ret

    def compute_cocin_hospital_admissions_by_age_sex(self, output_rates):
        dmales = (
            self.infected_gp_population["male"] * output_rates["gp_admissions_male"]
        )
        dfemales = (
            self.infected_gp_population["female"] * output_rates["gp_admissions_female"]
        )
        dmales += (
            self.infected_ch_population["male"] * output_rates["ch_admissions_male"]
        )
        dfemales += (
            self.infected_ch_population["female"] * output_rates["ch_admissions_female"]
        )
        ret = pd.DataFrame(index=self.age_bins)
        ret["male_prediction"] = dmales
        ret["female_prediction"] = dfemales
        ret["male_data"] = self.hospital_cocin_admissions["male"]
        ret["female_data"] = self.hospital_cocin_admissions["female"]
        return ret

    def _get_total_sum_of_df(self, df):
        return df.sum().sum()

    def make_numbers_table(self):
        functions = {
            "total deaths": self.compute_total_deaths_by_age_sex,
            "gp total deaths": self.compute_total_gp_deaths_by_age_sex,
            "ch total deaths": self.compute_total_ch_deaths_by_age_sex,
            "total hospital deaths": self.compute_total_hospital_deaths_by_age_sex,
            "gp hospital deaths": self.compute_gp_hospital_deaths_by_age_sex,
            "ch hospital deaths": self.compute_ch_hospital_deaths_by_age_sex,
            "total home deaths": self.compute_total_home_deaths_by_age_sex,
            "gp home deaths": self.compute_gp_home_deaths_by_age_sex,
            "ch home deaths": self.compute_ch_home_deaths_by_age_sex,
            "total admissions": self.compute_total_admissions_by_age_sex,
            "gp admissions": self.compute_gp_admissions_by_age_sex,
            "ch admissions": self.compute_ch_admissions_by_age_sex,
        }
        results = pd.DataFrame(
            index=list(functions.keys()),
            columns=["data"] + list(self.outputs_dict.keys()),
        )
        for quantity_name in results.index:
            for name, output in self.outputs_dict.items():
                results.loc[quantity_name, name] = (
                    functions[quantity_name](output)
                    .loc[:, ["male_prediction", "female_prediction"]]
                    .sum()
                    .sum()
                )
            results.loc[quantity_name, "data"] = (
                functions[quantity_name](output)
                .loc[:, ["male_data", "female_data"]]
                .sum()
                .sum()
            )
        return results

    def get_prediction_df(self, function):
        ret = None
        for name, output in self.outputs_dict.items():
            prediction = function(output_rates=output,)
            if ret is None:
                ret = pd.DataFrame(index=prediction.index)
                ret["data male"] = prediction["male_data"]
                ret["data female"] = prediction["female_data"]
            ret[f"{name} male"] = prediction["male_prediction"]
            ret[f"{name} female"] = prediction["female_prediction"]
        ret.index.name = "Age"
        return ret

    def plot_comparison_with_data(self, pdf_name="health_index_comparison.pdf", dpi=80):
        total_deaths = self.get_prediction_df(self.compute_total_deaths_by_age_sex)
        total_gp_hospital_deaths = self.get_prediction_df(
            self.compute_gp_hospital_deaths_by_age_sex
        )
        total_ch_hospital_deaths = self.get_prediction_df(
            self.compute_ch_hospital_deaths_by_age_sex
        )
        total_ch_deaths = self.get_prediction_df(
            self.compute_total_ch_deaths_by_age_sex
        )
        total_gp_admissions = self.get_prediction_df(
            self.compute_gp_admissions_by_age_sex
        )
        total_ch_admissions = self.get_prediction_df(
            self.compute_ch_admissions_by_age_sex
        )
        total_home_deaths = self.get_prediction_df(
            self.compute_gp_home_deaths_by_age_sex
        )
        cocin_hospital_deaths = self.get_prediction_df(
            self.compute_cocin_hospital_deaths_by_age_sex
        )
        cocin_hospital_admissions = self.get_prediction_df(
            self.compute_cocin_hospital_admissions_by_age_sex
        )
        pdf = PdfPages(pdf_name)
        male_model_columns = [
            column
            for column in total_deaths.columns
            if "data" not in column and " male" in column
        ] + ["data male"]
        female_model_columns = [
            column
            for column in total_deaths.columns
            if "data" not in column and "female" in column
        ] + ["data female"]
        colors = [f"C{i}" for i in range(len(male_model_columns) - 1)] + ["black"]

        fig, ax = plt.subplots()
        total_deaths.loc[:, male_model_columns].plot.bar(
            ax=ax, ylabel="Deaths", title="All Deaths Male", color=colors
        )
        pdf.savefig(ax.get_figure(), bbox_inches="tight", dpi=dpi)

        fig, ax = plt.subplots()
        total_deaths.loc[:, female_model_columns].plot.bar(
            ax=ax, ylabel="Deaths", title="All Deaths Female", color=colors
        )
        pdf.savefig(ax.get_figure(), bbox_inches="tight", dpi=dpi)

        fig, ax = plt.subplots()
        total_gp_hospital_deaths.loc[:, male_model_columns].plot.bar(
            ax=ax, ylabel="Deaths", title="GP Hospital Deaths Male", color=colors
        )
        pdf.savefig(ax.get_figure(), bbox_inches="tight", dpi=dpi)

        fig, ax = plt.subplots()
        total_gp_hospital_deaths.loc[:, female_model_columns].plot.bar(
            ax=ax, ylabel="Deaths", title="GP Hospital Deaths Female", color=colors
        )
        pdf.savefig(ax.get_figure(), bbox_inches="tight", dpi=dpi)

        fig, ax = plt.subplots()
        total_ch_hospital_deaths.loc[:, male_model_columns].plot.bar(
            ax=ax, ylabel="Deaths", title="CH Hospital Deaths Male", color=colors
        )
        pdf.savefig(ax.get_figure(), bbox_inches="tight", dpi=dpi)

        fig, ax = plt.subplots()
        total_ch_hospital_deaths.loc[:, female_model_columns].plot.bar(
            ax=ax, ylabel="Deaths", title="CH Hospital Deaths Female", color=colors
        )
        pdf.savefig(ax.get_figure(), bbox_inches="tight", dpi=dpi)

        fig, ax = plt.subplots()
        total_ch_deaths.loc[:, male_model_columns].plot.bar(
            ax=ax, ylabel="Deaths", title="CH All Deaths Male", color=colors
        )
        pdf.savefig(ax.get_figure(), bbox_inches="tight", dpi=dpi)

        fig, ax = plt.subplots()
        total_ch_deaths.loc[:, female_model_columns].plot.bar(
            ax=ax, ylabel="Deaths", title="CH All Deaths Female", color=colors
        )
        pdf.savefig(ax.get_figure(), bbox_inches="tight", dpi=dpi)

        fig, ax = plt.subplots()
        total_home_deaths.loc[:, male_model_columns].plot.bar(
            ax=ax, ylabel="Deaths", title="GP Home Deaths Male", color=colors
        )
        pdf.savefig(ax.get_figure(), bbox_inches="tight", dpi=dpi)

        fig, ax = plt.subplots()
        total_home_deaths.loc[:, female_model_columns].plot.bar(
            ax=ax, ylabel="Deaths", title="GP Home Deaths Female", color=colors
        )
        pdf.savefig(ax.get_figure(), bbox_inches="tight", dpi=dpi)

        fig, ax = plt.subplots()
        total_gp_admissions.loc[:, male_model_columns].plot.bar(
            ax=ax, ylabel="Admissions", title="GP Admissions Male", color=colors
        )
        pdf.savefig(ax.get_figure(), bbox_inches="tight", dpi=dpi)

        fig, ax = plt.subplots()
        total_gp_admissions.loc[:, female_model_columns].plot.bar(
            ax=ax, ylabel="Admissions", title="GP Admissions Female", color=colors
        )
        pdf.savefig(ax.get_figure(), bbox_inches="tight", dpi=dpi)

        fig, ax = plt.subplots()
        total_ch_admissions.loc[:, male_model_columns].plot.bar(
            ax=ax, ylabel="Admissions", title="CH Admissions Male", color=colors
        )
        pdf.savefig(ax.get_figure(), bbox_inches="tight", dpi=dpi)

        fig, ax = plt.subplots()
        total_ch_admissions.loc[:, female_model_columns].plot.bar(
            ax=ax, ylabel="Admissions", title="CH Admissions Female", color=colors
        )
        pdf.savefig(ax.get_figure(), bbox_inches="tight", dpi=dpi)

        pdf.close()
        plt.show()

    def plot_ifr_comparison(self, data_file, data_name, output_file):
        data = pd.read_csv(data_file, index_col=0)
        data.index = convert_to_intervals(data.index, is_interval=True)
        age_bins = data.index
        rates = Data2Rates.from_file()
        june_ifrs_all = np.array(
            [rates.get_infection_fatality_rate(age=age, sex="all") for age in age_bins]
        )
        june_ifrs_male = np.array(
            [rates.get_infection_fatality_rate(age=age, sex="male") for age in age_bins]
        )
        june_ifrs_female = np.array(
            [
                rates.get_infection_fatality_rate(age=age, sex="female")
                for age in age_bins
            ]
        )
        toplot = pd.DataFrame(index=data.index)
        toplot.loc[:, "JUNE male"] = june_ifrs_male * 100
        toplot.loc[:, "JUNE female"] = june_ifrs_female * 100
        toplot.loc[:, "JUNE average"] = june_ifrs_all * 100
        toplot.loc[:, data_name] = data.values
        colors = [f"C{i}" for i in range(3)] + ["black"]
        toplot = toplot.rename(mapper=revert_to_string)
        errors = np.array([data.error_low, data.error_high]).reshape(2, -1)
        june_errors = np.zeros_like(errors)
        errors_to_plot = np.array([errors, june_errors, june_errors, june_errors])
        # ax = toplot.plot.bar(yerr = , capsize=4, ylabel="IFR [%]", xlabel="Age bin")
        ax = toplot.loc[:, ["JUNE male", "JUNE female", "JUNE average"]].plot.bar(
            capsize=4,
            ylabel="IFR [\%]",
            xlabel="Age group",
            width=0.8,
            alpha=0.7,
            color=[self.colors["general_1"], self.colors["general_2"], self.colors["general_3"], self.colors["general_4"]]
            #title="Infection Fatality Rates (IFR)",
        )
        ax = toplot.loc[:, [data_name]].plot.bar(
            ax=ax,
            capsize=2,
            width=0.8,
            color="C3",
            yerr=errors,
            alpha=0.3,
        )
        fig = ax.get_figure()
        fig.savefig(output_file, dpi=300, bbox_inches="tight")
        return fig, ax

    def plot_comparison_with_imperial(self, output_file="imperial_vs_june.png"):
        return self.plot_ifr_comparison(
            data_file=ifr_imperial_file, output_file=output_file, data_name="Brazeau et al. average"
        )

    def plot_comparison_with_ward(self, output_file="ward_vs_june.png"):
        return self.plot_ifr_comparison(
            data_file=ifr_ward_file, output_file=output_file, data_name="Ward et al. average"
        )
