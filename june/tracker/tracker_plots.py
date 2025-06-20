from .tracker_plots_formatting import fig_initialize, set_size, dpi

import numpy as np
import yaml
import pandas as pd

from pathlib import Path
from june import paths

from june.world import World

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates
import datetime
import logging

from june.tracker.tracker import Tracker

from june.mpi_wrapper import mpi_comm, mpi_size, mpi_rank
from june.paths import data_path, configs_path

fig_initialize(setsize=True)

logger = logging.getLogger("tracker plotter")
mpi_logger = logging.getLogger("mpi")

if mpi_rank > 0:
    logger.propagate = False

default_BBC_Pandemic_loc = data_path / "BBC_Pandemic"

DaysOfWeek_Names = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]

cmap_A = "RdYlBu_r"
cmap_B = "seismic"


#######################################################
# Plotting functions ##################################
#######################################################


class PlotClass:
    """
    Class to plot everything tracker related

    Parameters
    ----------
    record_path:
        path for results directory

    Tracker_Contact_Type:
        NONE, Not used

    Normalization_Type:
        string, "U" for venue normalized or "P" for population normalized

    Following parameters can be preloaded data from another plot class. If None data automatically loaded.
        Params,
        IM,
        CM,
        NCM,
        NCM_R,
        CMV,
        NCMV,
        average_contacts,
        location_counters,
        location_counters_day,
        location_cum_pop,
        age_profiles,
        travel_distance,


    Returns
    -------
        The tracker plotting class

    """

    def __init__(
        self,
        record_path=Path(""),
        Tracker_Contact_Type=None,
        Params=None,
        IM=None,
        CM=None,
        NCM=None,
        NCM_R=None,
        CMV=None,
        NCM_V=None,
        average_contacts=None,
        location_counters=None,
        location_counters_day=None,
        location_cum_pop=None,
        age_profiles=None,
        travel_distance=None,
        Normalization_Type="U",
    ):

        if Tracker_Contact_Type is None:
            pass
        else:
            print("Tracker_Contact_Type argument no longer required")

        self.Normalization_Type = Normalization_Type

        self.record_path = record_path

        # Only plot fully merged data (Only applies to MPI runs, auto saved to merge if single core)
        folder_name = "merged_data_output"

        logger.info(f"Rank {mpi_rank} -- Begin loading")

        if Params is None:
            with open(
                self.record_path / folder_name / "tracker_Simulation_Params.yaml"
            ) as f:
                self.Params = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self.Params = Params

        if IM is None:
            with open(
                self.record_path / folder_name / "CM_yamls" / "tracker_IM.yaml"
            ) as f:
                self.IM = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self.IM = IM

        if CM is None:
            with open(
                self.record_path / folder_name / "CM_yamls" / f"tracker_CM.yaml"
            ) as f:
                self.CM = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self.CM = CM

        if NCM is None:
            with open(
                self.record_path
                / folder_name
                / "CM_yamls"
                / f"tracker_{self.Normalization_Type}NCM.yaml"
            ) as f:
                self.NCM = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self.NCM = NCM

        if NCM_R is None:
            with open(
                self.record_path
                / folder_name
                / "CM_yamls"
                / f"tracker_{self.Normalization_Type}NCM_R.yaml"
            ) as f:
                self.NCM_R = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self.NCM_R = NCM_R

        if CMV is None:
            with open(
                self.record_path / folder_name / "CM_yamls" / f"tracker_CMV.yaml"
            ) as f:
                self.CMV = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self.CMV = CMV

        if NCM_V is None:
            with open(
                self.record_path
                / folder_name
                / "CM_yamls"
                / f"tracker_{self.Normalization_Type}NCM_V.yaml"
            ) as f:
                self.NCM_V = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self.NCM_V = NCM_V

        # Get Parameters of simulation
        self.total_days = self.Params["total_days"]
        self.day_types = {
            "weekend": self.Params["Weekend_Names"],
            "weekday": self.Params["Weekday_Names"],
        }
        self.NVenues = self.Params["NVenues"]
        # Get all the bin types
        self.relevant_bin_types = list(self.CM.keys())
        # Get all location names
        self.group_type_names = list(self.CM["syoa"].keys())
        # Get all CM options
        self.CM_Keys = list(self.CM["syoa"][self.group_type_names[0]].keys())
        # Get all contact sexes
        self.contact_sexes = list(
            self.CM["syoa"][self.group_type_names[0]]["sex"].keys()
        )

        self.age_bins = {}
        for rbt in self.relevant_bin_types:
            if rbt == "Interaction":
                continue
            self.age_bins[rbt] = np.array(
                self.CM[rbt][self.group_type_names[0]]["bins"]
            )

        if average_contacts is None:
            self.average_contacts = {}
            for rbt in self.relevant_bin_types:
                if rbt == "Interaction":
                    continue
                self.average_contacts[rbt] = pd.read_excel(
                    self.record_path
                    / folder_name
                    / "Venue_AvContacts"
                    / "Average_contacts.xlsx",
                    sheet_name=rbt,
                    index_col=0,
                )
        else:
            self.average_contacts = average_contacts

        if location_counters is None:
            self.location_counters = {"loc": {}}
            for loc in self.group_type_names:
                if loc in ["global", "shelter_inter", "shelter_intra"]:
                    continue
                self.location_counters["loc"][loc] = {}
                self.location_counters["Timestamp"] = None
                self.location_counters["dt"] = None

                for sex in self.contact_sexes:
                    filename = f"Venues_{sex}_Counts_BydT.xlsx"
                    sheet_name = Tracker.pluralize(self, loc)
                    df = pd.read_excel(
                        self.record_path / folder_name / "Venue_UniquePops" / filename,
                        sheet_name=sheet_name,
                        index_col=0,
                    )
                    self.location_counters["loc"][loc][sex] = df.iloc[:, 2:]
                    if self.location_counters["Timestamp"] is None:
                        self.location_counters["Timestamp"] = df["t"]
                        self.location_counters["delta_t"] = df["dt"]
        else:
            self.location_counters = location_counters

        if location_counters_day is None:
            self.location_counters_day = {"loc": {}}
            for loc in self.group_type_names:
                if loc in ["global", "shelter_inter", "shelter_intra"]:
                    continue
                self.location_counters_day["loc"][loc] = {}
                self.location_counters_day["Timestamp"] = None

                for sex in self.contact_sexes:
                    filename = f"Venues_{sex}_Counts_ByDate.xlsx"
                    sheet_name = Tracker.pluralize(self, loc)
                    df = pd.read_excel(
                        self.record_path / folder_name / "Venue_UniquePops" / filename,
                        sheet_name=sheet_name,
                        index_col=0,
                    )
                    self.location_counters_day["loc"][loc][sex] = df.iloc[:, 0:]
                    if self.location_counters_day["Timestamp"] is None:
                        self.location_counters_day["Timestamp"] = df["t"]
        else:
            self.location_counters_day = location_counters_day

        if location_cum_pop is None:
            self.location_cum_pop = {}
            for rbt in self.relevant_bin_types:
                self.location_cum_pop[rbt] = {}
                filename = (
                    self.record_path
                    / folder_name
                    / "Venue_TotalDemographics"
                    / f"CumPersonCounts_{rbt}.xlsx"
                )
                for loc in self.group_type_names:
                    self.location_cum_pop[rbt][loc] = {}
                    if rbt == "Interaction" and loc in [
                        "global",
                        "shelter_inter",
                        "shelter_intra",
                    ]:
                        continue
                    df = pd.read_excel(filename, sheet_name=loc, index_col=0)
                    self.location_cum_pop[rbt][loc] = df
        else:
            self.location_cum_pop = location_cum_pop

        if age_profiles is None:
            self.age_profiles = {}
            for rbt in self.relevant_bin_types:
                if rbt == "Interaction":
                    continue
                self.age_profiles[rbt] = {}
                filename = (
                    self.record_path
                    / folder_name
                    / "Venue_Demographics"
                    / f"PersonCounts_{rbt}.xlsx"
                )
                for loc in self.group_type_names:
                    self.age_profiles[rbt][loc] = {}

                    df = pd.read_excel(filename, sheet_name=loc, index_col=0)
                    self.age_profiles[rbt][loc] = df.iloc[:-1, :]

        else:
            self.age_profiles = age_profiles

        if travel_distance is None:
            filename = (
                self.record_path
                / folder_name
                / "Venue_TravelDist"
                / "Distance_traveled.xlsx"
            )
            self.travel_distance = {}
            for loc in self.group_type_names:
                if loc in ["global", "shelter_inter", "shelter_intra"]:
                    continue
                sheet_name = Tracker.pluralize(self, loc)
                df = pd.read_excel(filename, sheet_name=sheet_name, index_col=0)
                self.travel_distance[loc] = df
        else:
            self.travel_distance = travel_distance

        logger.info(f"Rank {mpi_rank} -- Data loaded")

    #####################################################
    # Useful functions ##################################
    #####################################################

    def Calculate_CM_Metrics(self, bin_type, contact_type, CM, CM_err, sex="unisex"):
        return Tracker.Calculate_CM_Metrics(
            self, bin_type, contact_type, CM, CM_err, sex
        )

    def Population_Metrics(self, pop_by_bin, pop_bins):
        return Tracker.Population_Metrics(self, pop_by_bin, pop_bins)

    def Expectation_Assortativeness(self, NPCDM, pop_bins):
        return Tracker.Expectation_Assortativeness(self, NPCDM, pop_bins)

    def Calc_NPCDM(self, cm, pop_by_bin, pop_width):
        return Tracker.Calc_NPCDM(self, cm, pop_by_bin, pop_width)

    def Calc_QIndex(self, cm):
        return Tracker.Calc_QIndex(self, cm)

    def Canberra_distance(self, x, y):
        return Tracker.Canberra_distance(self, x, y)

    #############################################
    # Grab CM  ##################################
    #############################################

    def CMPlots_GetCM(self, bin_type, contact_type, sex="unisex", which="NCM"):
        """
        Get cm out of dictionary.

        Parameters
        ----------
            binType:
                Name of bin type syoa, AC etc
            contact_type:
                Location of contacts
            sex:
                Sex contact matrix
            which:
                str, which matrix type to collect "CM", "NCM", "NCM_R", "CMV", "NCM_V"

        Returns
        -------
            cm:
                np.array contact matrix
            cm_err:
                np.array contact matrix errors
        """
        if bin_type != "Interaction":
            if which == "CM":
                cm = self.CM[bin_type][contact_type]["sex"][sex]["contacts"]
                cm_err = self.CM[bin_type][contact_type]["sex"][sex]["contacts_err"]
            elif which == "NCM":
                cm = self.NCM[bin_type][contact_type]["sex"][sex]["contacts"]
                cm_err = self.NCM[bin_type][contact_type]["sex"][sex]["contacts_err"]
            elif which == "NCM_R":
                cm = self.NCM_R[bin_type][contact_type]["sex"][sex]["contacts"]
                cm_err = self.NCM_R[bin_type][contact_type]["sex"][sex]["contacts_err"]

            elif which == "CMV":
                cm = self.CMV[bin_type][contact_type]["sex"][sex]["contacts"]
                cm_err = self.CMV[bin_type][contact_type]["sex"][sex]["contacts_err"]
            elif which == "NCM_V":
                cm = self.NCM_V[bin_type][contact_type]["sex"][sex]["contacts"]
                cm_err = self.NCM_V[bin_type][contact_type]["sex"][sex]["contacts_err"]

        else:
            if which == "CM":
                cm = self.CM[bin_type][contact_type]["contacts"]
                cm_err = self.CM[bin_type][contact_type]["contacts_err"]
            elif which == "NCM":
                cm = self.NCM[bin_type][contact_type]["contacts"]
                cm_err = self.NCM[bin_type][contact_type]["contacts_err"]
            elif which == "NCM_R":
                cm = self.NCM_R[bin_type][contact_type]["contacts"]
                cm_err = self.NCM_R[bin_type][contact_type]["contacts_err"]

            elif which == "CMV":
                cm = self.CMV[bin_type][contact_type]["contacts"]
                cm_err = self.CMV[bin_type][contact_type]["contacts_err"]
            elif which == "NCM_V":
                cm = self.NCM_V[bin_type][contact_type]["contacts"]
                cm_err = self.NCM_V[bin_type][contact_type]["contacts_err"]

        return np.array(cm), np.array(cm_err)

    def IMPlots_GetIM(self, contact_type):
        return Tracker.IMPlots_GetIM(self, contact_type)

    def get_characteristic_time(self, location):
        return Tracker.get_characteristic_time(self, location)

    #####################################################
    # General Plotting ##################################
    #####################################################

    def Get_SAMECMAP_Norm(self, dim, which="NCM", override=None):
        """
        If same colour map required this produces standardized colourmaps for different size matrices.

        Parameters
        ----------
            dim:
                int, the dimension (length) of square matrix
            which:
                string, the contact matrix type
            override:
                string, Log, Lin, SymLog or SymLin. Override if SAMECMAP was False. (Applies to certain plots)

        Returns
        -------
            Norm:
                matplotlib.colors.Norm object

        """
        if which in ["CM", "NCM", "NCM_R"]:
            if self.Normalization_Type == "U":
                SAMElinvmin = {"small_dim": 0, "large_dim": 0}
                SAMElogvmin = {"small_dim": 1e-1, "large_dim": 1e-2}

                SAMElinvmax = {"small_dim": 2.5e1, "large_dim": 4e0}
                SAMElogvmax = {"small_dim": 2.5e1, "large_dim": 4e0}

                SAMEsymlogvmax = {"small_dim": 3e0, "large_dim": 3e0}
                SAMEsymlinvmax = {"small_dim": 1e0, "large_dim": 0.5e0}

            elif self.Normalization_Type == "P":
                SAMElinvmin = {"small_dim": 0, "large_dim": 0}
                SAMElogvmin = {"small_dim": 1e-1, "large_dim": 1e-4}

                SAMElinvmax = {"small_dim": 2.5e1, "large_dim": 1e0}
                SAMElogvmax = {"small_dim": 2.5e1, "large_dim": 1e0}

                SAMEsymlogvmax = {"small_dim": 3e0, "large_dim": 1e0}
                SAMEsymlinvmax = {"small_dim": 1e0, "large_dim": 1e0}

        elif which in ["CMV", "NCM_V"]:
            if self.Normalization_Type == "U":
                SAMElinvmin = {"small_dim": 0, "large_dim": 0}
                SAMElogvmin = {"small_dim": 1, "large_dim": 1e-2}

                SAMElinvmax = {"small_dim": 1e2, "large_dim": 1e1}
                SAMElogvmax = {"small_dim": 1e2, "large_dim": 1e1}

                SAMEsymlogvmax = {"small_dim": 1e2, "large_dim": 1e1}
                SAMEsymlinvmax = {"small_dim": 1e2, "large_dim": 1e1}
            elif self.Normalization_Type == "P":
                SAMElinvmin = {"small_dim": 0, "large_dim": 0}
                SAMElogvmin = {"small_dim": 1e-1, "large_dim": 1e-4}

                SAMElinvmax = {"small_dim": 1e2, "large_dim": 1e1}
                SAMElogvmax = {"small_dim": 1e2, "large_dim": 1e1}

                SAMEsymlogvmax = {"small_dim": 1e2, "large_dim": 1e1}
                SAMEsymlinvmax = {"small_dim": 1e2, "large_dim": 1e1}

        if dim < 5:
            kind = "small_dim"
        else:
            kind = "large_dim"

        if override is None:
            if self.SameCMAP == "Log":
                return colors.LogNorm(vmin=SAMElogvmin[kind], vmax=SAMElogvmax[kind])
            elif self.SameCMAP == "Lin":
                return colors.Normalize(vmin=SAMElinvmin[kind], vmax=SAMElinvmax[kind])
        elif override == "SymLog":
            return colors.SymLogNorm(
                linthresh=1e-1, vmin=-SAMEsymlogvmax[kind], vmax=SAMEsymlogvmax[kind]
            )
        elif override == "SymLin":
            return colors.Normalize(
                vmin=-SAMEsymlinvmax[kind], vmax=SAMEsymlinvmax[kind]
            )
        elif override == "Log":
            return colors.LogNorm(vmin=SAMElogvmin[kind], vmax=SAMElogvmax[kind])
        elif override == "Lin":
            return colors.Normalize(vmin=SAMElinvmin[kind], vmax=SAMElinvmax[kind])
        return None

    def AnnotateCM(self, cm, cm_err, ax, thresh=1e10, annotate=True):
        """
        Function to annotate the CM with text. Including error catching for Nonetype errors.

        Parameters
        ----------
            cm:
                np.array contact matrix
            cm_err:
                np.array contact matrix errors
            ax:
                matplotlib axes
            thresh:
                threshold value for CM text change colour


        Returns
        -------
            ax
        """
        size = mpl.rcParams["font.size"]
        if cm.shape[0] <= 2:
            size -= 3
        if cm.shape[0] >= 3:
            size -= 4

        if annotate == "Small":
            size -= 2

        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                fmt = ".2f"
                if cm[i, j] == 1e-16:
                    cm[i, j] = 0
                if cm[i, j] > 1e8:
                    cm[i, j] = np.inf

                if cm_err is not None:
                    if np.isnan(cm_err[i, j]):
                        cm_err[i, j] = 0

                    if cm_err[i, j] + cm[i, j] == 0:
                        fmt = ".0f"

                    if fmt == ".0f":
                        text = r"$0 \pm 0$"
                    else:
                        text = (
                            r"$%s \pm $" % (format(cm[i, j], fmt))
                            + "\n\t"
                            + "$%s$" % (format(cm_err[i, j], fmt))
                        )

                else:
                    text = r"$%s$" % (format(cm[i, j], fmt))

                if thresh == 1e8:
                    ax.text(
                        j, i, text, ha="center", va="center", color="black", size=size
                    )
                else:
                    ax.text(
                        j,
                        i,
                        text,
                        ha="center",
                        va="center",
                        color="white" if abs(cm[i, j] - 1) > thresh else "black",
                        size=size,
                    )
        return ax

    def PlotCM(
        self,
        cm,
        cm_err,
        labels,
        ax,
        thresh=1e10,
        thumb=False,
        annotate=True,
        **plt_kwargs,
    ):
        """
        Function to imshow plot the CM.

        Parameters
        ----------
            cm:
                np.array contact matrix
            cm_err:
                np.array contact matrix errors
            labels:
                list of string bins labels (or none type)
            ax:
                matplotlib axes
            thresh:
                threshold value for CM text change colour
            thumb:
                bool, make thumbnail style plots. e.g. no axis labels
            **plt_kwargs:
                plot keyword arguments

        Returns
        -------
            im:
                reference to plot object
        """

        if cm is None:
            pass
        else:
            cm = cm.T

        if cm_err is None:
            pass
        else:
            cm_err = cm_err.T

        if labels is not None:
            if "kids" in labels and "young_adults" in labels:
                labels = ["K", "Y", "A", "O"]
            elif len(labels) == 2 and "students" in labels:
                if labels[0] == "students" and labels[1] == "teachers":
                    labels = ["  S  ", "  T  "]
                elif labels[1] == "students" and labels[0] == "teachers":
                    labels = ["  S  ", "  T  "]
                    # labels = ["Stude", "Teach"]
                    cm = cm.T
                    if cm_err is None:
                        pass
                    else:
                        cm_err = cm_err.T
            elif "workers" in labels and len(labels) == 1:
                labels = ["W"]
            elif "inter" in labels:
                labels = [r" H$_1$ ", r" H$_2$ "]

        # im = ax.matshow(cm, **plt_kwargs)
        Interpolation = "None"
        im = ax.imshow(cm, **plt_kwargs, interpolation=Interpolation)
        ax.xaxis.tick_bottom()

        if annotate == "Small" and len(labels) >= 3:
            size = mpl.rcParams["xtick.labelsize"] - 4
        elif annotate == "Small":
            size = mpl.rcParams["xtick.labelsize"] - 2
        else:
            size = mpl.rcParams["xtick.labelsize"]

        if labels is not None:
            if len(labels) == 1:
                ax.set_xticks(np.arange(len(cm)))
                ax.set_xticklabels(labels, rotation=0, size=size)
                ax.set_yticks(np.arange(len(cm)))
                ax.set_yticklabels(labels, rotation=0, size=size)
            elif len(labels) < 10:
                ax.set_xticks(np.arange(len(cm)))
                ax.set_xticklabels(labels, rotation=45)
                ax.set_yticks(np.arange(len(cm)))
                ax.set_yticklabels(labels)

            elif len(labels) >= 10 and len(labels) <= 25:
                ax.set_xticks(np.arange(len(cm)))
                ax.set_xticklabels(labels, rotation=90, size=size)
                ax.set_yticks(np.arange(len(cm)))
                ax.set_yticklabels(labels, size=size)
            elif len(labels) < 25:
                ax.set_xticks(np.arange(len(cm)))
                ax.set_xticklabels(labels, rotation=90, size=size)
                ax.set_yticks(np.arange(len(cm)))
                ax.set_yticklabels(labels, size=size)
        else:
            Nticks = 5
            ticks = np.arange(0, len(cm), int((len(cm) + 1) / (Nticks - 1)))
            ax.set_xticks(ticks)
            ax.set_xticklabels(ticks)
            ax.set_yticks(ticks)
            ax.set_yticklabels(ticks)

        # Loop over data dimensions and create text annotations.
        if cm.shape[0] * cm.shape[1] < 26 and annotate:
            self.AnnotateCM(cm, cm_err, ax, thresh=thresh, annotate=annotate)
        if not thumb:
            ax.set_xlabel("age group")
            ax.set_ylabel("contact age group")
        else:
            # ax.axes.xaxis.set_visible(False)
            # ax.axes.yaxis.set_visible(False)
            ax.set_xlabel("")
            ax.set_ylabel("")
            pass
        return im

    def CMPlots_GetLabels(self, bins):
        """
        Create list of labels for the bins in the CM plots

        Parameters
        ----------
            bins:
                np.array bin edges

        Returns
        -------
            labels:
                list of strings for bin labels or none type
        """
        if len(bins) < 25:
            return [f"{low}-{high-1}" for low, high in zip(bins[:-1], bins[1:])]
        else:
            return None

    def MaxAgeBinIndex(self, bins, MaxAgeBin=60):
        """
        Get index for truncation of bins upto max age MaxAgeBin
            self.group_type_names

        Parameters
        ----------
            bins:
                Age bins
            MaxAgeBin:
                The maximum age at which to truncate the bins

        Returns
        -------
            Index
        """
        Array = [index for index in range(len(bins)) if bins[index] >= MaxAgeBin]
        if len(Array) != 0:
            return min(Array)
        else:
            return None

    def CMPlots_UsefulCM(self, bin_type, cm, cm_err=None, labels=None, MaxAgeBin=100):
        """
        Truncate the CM for the plots to drop age bins of the data with no people.

        Parameters
        ----------
            binType:
                Name of bin type syoa, AC etc
            cm:
                np.array contact matrix
            cm_err:
                np.array contact matrix errors
            labels:
                list of strings for bin labels or none type

        Returns
        -------
            Truncated values of;
            cm:
                np.array contact matrix
            cm_err:
                np.array contact matrix errors
            labels:
                list of strings for bin labels or none type
        """
        if bin_type == "Paper":
            MaxAgeBin = np.inf
        index = self.MaxAgeBinIndex(self.age_bins[bin_type], MaxAgeBin=MaxAgeBin)
        cm = cm[:index, :index]
        if cm_err is not None:
            cm_err = cm_err[:index, :index]
        if labels is not None:
            labels = labels[:index]
        return cm, cm_err, labels

    def IMPlots_GetLabels(self, contact_type):
        """
        Create list of labels for the bins in the input IM plots. More nuisanced as subgroups not always age bins.

        Parameters
        ----------
            contact_type:
                Location of contacts


        Returns
        -------
            labels:
                list of strings for bin labels or none type
        """

        bintype = self.IM[contact_type]["type"]
        bins = np.array(self.IM[contact_type]["bins"])

        if len(bins) < 25 and bintype == "Age":
            labels = [
                f"{int(low)}-{int(high-1)}" for low, high in zip(bins[:-1], bins[1:])
            ]
        elif len(bins) < 25 and bintype == "Discrete":
            labels = bins
        else:
            labels = None
        return labels

    def IMPlots_UsefulCM(self, contact_type, cm, cm_err=None, labels=None):
        """
        Truncate the CM for the plots to drop age bins of the data with no people.

        Parameters
        ----------
            contact_type:
                Location of contacts
            cm:
                np.array contact matrix
            cm_err:
                np.array contact matrix errors
            labels:
                list of strings for bin labels or none type

        Returns
        -------
            Truncated values of;
            cm:
                np.array contact matrix
            cm_err:
                np.array contact matrix errors
            labels:
                list of strings for bin labels or none type
        """
        bintype = self.IM[contact_type]["type"]
        bins = np.array(self.IM[contact_type]["bins"])

        if bintype == "Discrete":
            return cm, cm_err, labels

        index = self.MaxAgeBinIndex(np.array(bins))
        cm = cm[:index, :index]
        if cm_err is not None:
            cm_err = cm_err[:index, :index]
        if labels is not None:
            labels = labels[:index]
        return cm, cm_err, labels

    #############################################
    # Plotting ##################################
    #############################################

    def plot_contact_matrix_INOUT(
        self,
        bin_type,
        contact_type,
        sex="unisex",
        which="NCM_R",
        plot_BBC_Sheet=False,
        MaxAgeBin=100,
    ):
        """
        Function to plot input contact matrix vs output for bin_type, contact_type and sex.

        Parameters
        ----------
            binType:
                Name of bin type syoa, AC etc
            contact_type:
                Location of contacts
            sex:
                Sex contact matrix
            which:
                str, which matrix type to collect "NCM", "NCM_R", "CM_T"

        Returns
        -------
            (ax1,ax2):
                matplotlib axes objects (Linear and Log)
        """

        IM, IM_err = self.IMPlots_GetIM(contact_type)
        labels_IM = self.IMPlots_GetLabels(contact_type)
        IM, IM_err, labels_IM = self.IMPlots_UsefulCM(
            contact_type, IM, cm_err=IM_err, labels=labels_IM
        )

        if len(np.nonzero(IM)[0]) != 0 and len(np.nonzero(IM)[1]) != 0:
            IM_Min = np.nanmin(IM[np.nonzero(IM)])
        else:
            IM_Min = 1e-1
        if np.isfinite(IM).sum() != 0:
            IM_Max = IM[np.isfinite(IM)].max()
        else:
            IM_Max = 1

        if np.isnan(IM_Min):
            IM_Min = 1e-1
        if np.isnan(IM_Max) or IM_Max == 0:
            IM_Max = 1

        IM = np.nan_to_num(IM, posinf=IM_Max, neginf=0, nan=0)

        labels = self.CMPlots_GetLabels(self.age_bins[bin_type])
        cm, cm_err = self.CMPlots_GetCM(bin_type, contact_type, sex=sex, which=which)
        cm, cm_err, labels = self.CMPlots_UsefulCM(
            bin_type, cm, cm_err, labels, MaxAgeBin
        )

        if len(np.nonzero(cm)[0]) != 0 and len(np.nonzero(cm)[1]) != 0:
            cm_Min = np.nanmin(cm[np.nonzero(cm)])
        else:
            cm_Min = 1e-1
        if np.isfinite(cm).sum() != 0:
            cm_Max = cm[np.isfinite(cm)].max()
        else:
            cm_Max = 1

        if np.isnan(cm_Min):
            cm_Min = 1e-1
        if np.isnan(cm_Max) or cm_Max == 0:
            cm_Max = 1

        cm = np.nan_to_num(cm, posinf=cm_Max, neginf=0, nan=0)

        if not self.SameCMAP:
            norm1 = colors.Normalize(vmin=0, vmax=IM_Max)
            norm2 = colors.Normalize(vmin=0, vmax=cm_Max)
        else:
            norm1 = self.Get_SAMECMAP_Norm(IM.shape[0], which=which)
            norm2 = self.Get_SAMECMAP_Norm(cm.shape[0], which=which)

        if not plot_BBC_Sheet:
            # plt.rcParams["figure.figsize"] = (15, 5)
            f, (ax1, ax2) = plt.subplots(1, 2)
            f.set_size_inches(set_size(subplots=(1, 2), fraction=1))
            f.patch.set_facecolor("white")

            im1 = self.PlotCM(
                IM + 1e-16,
                IM_err,
                labels_IM,
                ax1,
                origin="lower",
                cmap=cmap_A,
                norm=norm1,
            )
            im2 = self.PlotCM(
                cm + 1e-16, cm_err, labels, ax2, origin="lower", cmap=cmap_A, norm=norm2
            )

            f.colorbar(im1, ax=ax1, extend="both")
            f.colorbar(im2, ax=ax2, extend="both")

            # ax1.set_title(f"IM")
            # ax2.set_title(f"{which}")
            # f.suptitle(f"{bin_type} binned contacts in {contact_type}")
            # plt.tight_layout()
            return (ax1, ax2)
        else:
            df = pd.read_excel(
                default_BBC_Pandemic_loc
                / "BBC reciprocal matrices by type and context.xls",
                sheet_name=plot_BBC_Sheet,
            )
            bbc_cm = df.iloc[:, 1:].values.T
            bbc_labels = df.iloc[:, 0].values

            bbc_Max = np.nanmax(bbc_cm)
            bbc_Min = np.nanmin(bbc_cm)

            # Put into same contact units

            CT = self.get_characteristic_time(contact_type)[0]
            cm /= CT

            cm_Max = max(bbc_Max, cm_Max)

            if contact_type in "household":
                norm2 = colors.LogNorm(vmin=1e-2, vmax=2)
            elif contact_type in "school":
                norm2 = colors.LogNorm(vmin=1e-3, vmax=1e1)
            elif contact_type in "company":
                norm2 = colors.LogNorm(vmin=1e-2, vmax=1)

            # plt.rcParams["figure.figsize"] = (15, 5)
            f, (ax1, ax2, ax3) = plt.subplots(1, 3)
            f.set_size_inches(set_size(subplots=(1, 2), fraction=1))
            f.patch.set_facecolor("white")

            im1 = self.PlotCM(
                IM + 1e-16,
                IM_err,
                labels_IM,
                ax1,
                origin="lower",
                cmap=cmap_A,
                norm=norm1,
                annotate=True,
                thumb=True,
            )
            im2 = self.PlotCM(
                (cm + 1e-16),
                cm_err,
                labels,
                ax2,
                origin="lower",
                cmap=cmap_A,
                norm=norm2,
                annotate="Small",
                thumb=True,
            )

            im3 = self.PlotCM(
                bbc_cm,
                None,
                bbc_labels,
                ax3,
                origin="lower",
                cmap=cmap_A,
                norm=norm2,
                annotate="Small",
                thumb=True,
            )

            cm = np.nan_to_num(cm, nan=0.0)
            bbc_cm = np.nan_to_num(bbc_cm, nan=0.0)

            print(contact_type)
            pop_by_bin = np.array(self.age_profiles[bin_type][contact_type][sex])
            pop_bins = np.array(self.age_bins[bin_type])
            pop_width = np.diff(pop_bins)

            pop_density = pop_by_bin / (np.nansum(pop_by_bin) * pop_width)

            pop_by_bin_true = np.array(self.age_profiles["syoa"][contact_type][sex])
            pop_bins_true = np.array(self.age_bins["syoa"])
            mean, var = self.Population_Metrics(pop_by_bin_true, pop_bins_true)

            Q = self.Calc_QIndex(cm)
            NPCDM = self.Calc_NPCDM(cm, pop_density, pop_width)
            I_sq = self.Expectation_Assortativeness(NPCDM, pop_bins)
            I_sq_s = I_sq / var**2
            print("JUNE", {"Q": f"{Q}", "I_sq": f"{I_sq}", "I_sq_s": f"{I_sq_s}"})

            Q = self.Calc_QIndex(bbc_cm)
            NPCDM = self.Calc_NPCDM(bbc_cm, pop_density, pop_width)
            I_sq = self.Expectation_Assortativeness(NPCDM, pop_bins)
            I_sq_s = I_sq / var**2
            print("BBC", {"Q": f"{Q}", "I_sq": f"{I_sq}", "I_sq_s": f"{I_sq_s}"})
            print({"Camberra": self.Canberra_distance(cm, bbc_cm)[0]})
            print("")

            f.colorbar(im1, ax=ax1, extend="both", format="%g")
            f.colorbar(im2, ax=ax2, extend="both", format="%g")
            f.colorbar(im3, ax=ax3, extend="both", format="%g")

            # ax1.set_title(f"IM")
            # ax2.set_title(f"{which}")
            # ax3.set_title(f"BBC ({plot_BBC_Sheet})")
            # f.suptitle(f"{bin_type} binned contacts in {contact_type}")
            plt.tight_layout()
            return (ax1, ax2, ax3)

    def plot_interaction_matrix(self, contact_type):
        """
        Function to plot interaction matrix for contact_type

        Parameters
        ----------
            contact_type:
                Location of contacts

        Returns
        -------
            ax1:
                matplotlib axes object
        """
        which = "NCM"
        IM, IM_err = self.IMPlots_GetIM(contact_type)
        labels_IM = self.IMPlots_GetLabels(contact_type)
        IM, IM_err, labels_IM = self.IMPlots_UsefulCM(
            contact_type, IM, cm_err=IM_err, labels=labels_IM
        )

        if len(np.nonzero(IM)[0]) != 0 and len(np.nonzero(IM)[1]) != 0:
            IM_Min = np.nanmin(IM[np.nonzero(IM)])
        else:
            IM_Min = 1e-1
        if np.isfinite(IM).sum() != 0:
            IM_Max = IM[np.isfinite(IM)].max()
        else:
            IM_Max = 1

        if np.isnan(IM_Min):
            IM_Min = 1e-1
        if np.isnan(IM_Max) or IM_Max == 0:
            IM_Max = 1

        IM = np.nan_to_num(IM, posinf=IM_Max, neginf=0, nan=0)

        labels_CM = labels_IM
        if contact_type in self.CM["Interaction"].keys():
            cm, cm_err = self.CMPlots_GetCM("Interaction", contact_type, which=which)
            cm, cm_err, _ = self.IMPlots_UsefulCM(
                contact_type, cm, cm_err=cm_err, labels=labels_CM
            )
        else:  # The venue wasn't tracked
            cm = np.zeros_like(IM)
            cm_err = np.zeros_like(cm)

        if len(np.nonzero(cm)[0]) != 0 and len(np.nonzero(cm)[1]) != 0:
            cm_Min = np.nanmin(cm[np.nonzero(cm)])
        else:
            cm_Min = 1e-1
        if np.isfinite(cm).sum() != 0:
            cm_Max = cm[np.isfinite(cm)].max()
        else:
            cm_Max = 1

        if np.isnan(cm_Min):
            cm_Min = 1e-1
        if np.isnan(cm_Max) or cm_Max == 0:
            cm_Max = 1
        cm = np.nan_to_num(cm, posinf=cm_Max, neginf=0, nan=0)

        vMax = max(cm_Max, IM_Max)
        vMin = 1e-2

        # plt.rcParams["figure.figsize"] = (15, 5)
        f, (ax1, ax2, ax3) = plt.subplots(1, 3)
        f.set_size_inches(set_size(subplots=(1, 2), fraction=1))
        f.patch.set_facecolor("white")

        if not self.SameCMAP:
            norm1 = colors.Normalize(vmin=vMin, vmax=vMax)
            norm2 = colors.Normalize(vmin=vMin, vmax=vMax)
        else:

            norm1 = self.Get_SAMECMAP_Norm(IM.shape[0], which=which)
            norm2 = self.Get_SAMECMAP_Norm(cm.shape[0], which=which)

        im1 = self.PlotCM(
            IM + 1e-16,
            IM_err,
            labels_IM,
            ax1,
            origin="lower",
            cmap=cmap_A,
            norm=norm1,
            annotate=True,
            thumb=True,
        )
        im2 = self.PlotCM(
            cm + 1e-16,
            cm_err,
            labels_CM,
            ax2,
            origin="lower",
            cmap=cmap_A,
            norm=norm2,
            annotate="Small",
            thumb=True,
        )

        ratio = cm / IM
        ratio = np.nan_to_num(ratio)
        ratio_values = ratio[np.nonzero(ratio) and ratio < 1e3]
        if len(ratio_values) != 0:
            ratio_max = np.nanmax(ratio_values)
            ratio_min = np.nanmin(ratio_values)
            diff_max = np.max([abs(ratio_max - 1), abs(ratio_min - 1)])
            if diff_max < 0.5:
                diff_max = 0.5
        else:
            diff_max = 0.5
        if IM_err is None:
            IM_err = np.zeros_like(IM)
        ratio_errors = ratio * np.sqrt((cm_err / cm) ** 2 + (IM_err / IM) ** 2)

        norm = colors.Normalize(vmin=1 - diff_max, vmax=1 + diff_max)
        norm = colors.Normalize(vmin=1 - 1, vmax=1 + 1)
        im3 = self.PlotCM(
            ratio,
            ratio_errors,
            labels_CM,
            ax3,
            thresh=diff_max / 3,
            origin="lower",
            cmap=cmap_B,
            norm=norm,
            annotate="Small",
            thumb=True,
        )
        f.colorbar(im1, ax=ax1, extend="both")
        f.colorbar(im2, ax=ax2, extend="both")
        f.colorbar(im3, ax=ax3, extend="both")
        ax1.set_title("IM")
        ax2.set_title("NCM")
        ax3.set_title("NCM / IM")

        # f.suptitle(f"Survey interaction binned contacts in {contact_type}")
        plt.tight_layout()
        return ax1

    def plot_interaction_matrix_thumb(self, log, contact_type):
        """
        Function to plot interaction matrix for contact_type

        Parameters
        ----------
            log:

            contact_type:
                Location of contacts

        Returns
        -------
            ax1:
                matplotlib axes object
        """
        which = "NCM"
        IM, IM_err = self.IMPlots_GetIM(contact_type)
        labels_IM = self.IMPlots_GetLabels(contact_type)
        IM, IM_err, labels_IM = self.IMPlots_UsefulCM(
            contact_type, IM, cm_err=IM_err, labels=labels_IM
        )

        if len(np.nonzero(IM)[0]) != 0 and len(np.nonzero(IM)[1]) != 0:
            IM_Min = np.nanmin(IM[np.nonzero(IM)])
        else:
            IM_Min = 1e-1
        if np.isfinite(IM).sum() != 0:
            IM_Max = IM[np.isfinite(IM)].max()
        else:
            IM_Max = 1

        if np.isnan(IM_Min):
            IM_Min = 1e-1
        if np.isnan(IM_Max) or IM_Max == 0:
            IM_Max = 1

        IM = np.nan_to_num(IM, posinf=IM_Max, neginf=0, nan=0)

        labels_CM = labels_IM

        f, ax1 = plt.subplots(1, 1)
        f.set_size_inches(set_size(subplots=(1, 1), fraction=0.5))
        f.patch.set_facecolor("white")

        if not self.SameCMAP:
            normlin = colors.Normalize(vmin=0, vmax=IM_Max)
            normlog = colors.LogNorm(vmin=IM_Max, vmax=IM_Max)
        else:
            normlin = self.Get_SAMECMAP_Norm(IM.shape[0], which=which)
            normlog = self.Get_SAMECMAP_Norm(IM.shape[0], which=which)

        if not log:
            im1 = self.PlotCM(
                IM + 1e-16,
                IM_err,
                labels_IM,
                ax1,
                origin="lower",
                cmap=cmap_A,
                norm=normlin,
                thumb=True,
            )
        else:
            im1 = self.PlotCM(
                IM + 1e-16,
                IM_err,
                labels_IM,
                ax1,
                origin="lower",
                cmap=cmap_A,
                norm=normlog,
                thumb=True,
            )

        # f.suptitle(f"Survey interaction binned contacts in {contact_type}")
        # plt.tight_layout()
        return f, ax1, im1

    def plot_contact_matrix(
        self, bin_type, contact_type, sex="unisex", which="NCM", MaxAgeBin=100
    ):
        """
        Function to plot contact matrix for bin_type, contact_type and sex.

        Parameters
        ----------
            binType:
                Name of bin type syoa, AC etc
            contact_type:
                Location of contacts
            sex:
                Sex contact matrix
            which:
                str, which matrix type to collect "NCM", "NCM_R", "CM_T"

        Returns
        -------
            (ax1,ax2):
                matplotlib axes objects (Linear and Log)
        """
        cm, cm_err = self.CMPlots_GetCM(bin_type, contact_type, sex=sex, which=which)
        if bin_type == "Interaction":
            labels = self.IMPlots_GetLabels(contact_type)
        else:
            labels = self.CMPlots_GetLabels(self.age_bins[bin_type])
            cm, cm_err, labels = self.CMPlots_UsefulCM(
                bin_type, cm, cm_err, labels, MaxAgeBin
            )

        if len(np.nonzero(cm)[0]) != 0 and len(np.nonzero(cm)[1]) != 0:
            cm_Min = np.nanmin(cm[np.nonzero(cm)])
        else:
            cm_Min = 1e-1
        if np.isfinite(cm).sum() != 0:
            cm_Max = cm[np.isfinite(cm)].max()
        else:
            cm_Max = 1

        if np.isnan(cm_Min):
            cm_Min = 1e-1
        if np.isnan(cm_Max) or cm_Max == 0:
            cm_Max = 1

        cm = np.nan_to_num(cm, posinf=cm_Max, neginf=0, nan=0)

        if not self.SameCMAP or which == "CM_T":
            normlin = colors.Normalize(vmin=0, vmax=cm_Max)
            normlog = colors.LogNorm(vmin=cm_Min, vmax=cm_Max)
        else:
            normlin = self.Get_SAMECMAP_Norm(cm.shape[0], which=which, override="Lin")
            normlog = self.Get_SAMECMAP_Norm(cm.shape[0], which=which, override="Log")

        # plt.rcParams["figure.figsize"] = (15, 5)
        f, (ax1, ax2) = plt.subplots(1, 2)
        f.set_size_inches(set_size(subplots=(1, 2), fraction=1))
        f.patch.set_facecolor("white")

        im1 = self.PlotCM(
            cm + 1e-16, cm_err, labels, ax1, origin="lower", cmap=cmap_A, norm=normlin
        )
        im2 = self.PlotCM(
            cm + 1e-16, cm_err, labels, ax2, origin="lower", cmap=cmap_A, norm=normlog
        )

        f.colorbar(im1, ax=ax1, extend="both")
        f.colorbar(im2, ax=ax2, extend="both")

        # ax1.set_title("Linear Scale")
        # ax2.set_title("Log Scale")
        # f.suptitle(f"{bin_type} binned contacts in {contact_type} for {sex}")
        # plt.tight_layout()
        return (ax1, ax2)

    def plot_contact_matrix_thumb(
        self, log, bin_type, contact_type, sex="unisex", which="NCM", MaxAgeBin=100
    ):
        """
        Function to plot contact matrix for bin_type, contact_type and sex.

        Parameters
        ----------
            log:
                bool, shold be log plot?
            binType:
                Name of bin type syoa, AC etc
            contact_type:
                Location of contacts
            sex:
                Sex contact matrix
            which:
                str, which matrix type to collect "NCM", "NCM_R", "CM_T"

        Returns
        -------
            (ax1,ax2):
                matplotlib axes objects (Linear and Log)
        """

        cm, cm_err = self.CMPlots_GetCM(bin_type, contact_type, sex=sex, which=which)
        if bin_type == "Interaction":
            labels = self.IMPlots_GetLabels(contact_type)
        else:
            labels = self.CMPlots_GetLabels(self.age_bins[bin_type])
            cm, cm_err, labels = self.CMPlots_UsefulCM(
                bin_type, cm, cm_err, labels, MaxAgeBin
            )

        if len(np.nonzero(cm)[0]) != 0 and len(np.nonzero(cm)[1]) != 0:
            cm_Min = np.nanmin(cm[np.nonzero(cm)])
        else:
            cm_Min = 1e-1
        if np.isfinite(cm).sum() != 0:
            cm_Max = cm[np.isfinite(cm)].max()
        else:
            cm_Max = 1

        if np.isnan(cm_Min):
            cm_Min = 1e-1
        if np.isnan(cm_Max) or cm_Max == 0:
            cm_Max = 1

        cm = np.nan_to_num(cm, posinf=cm_Max, neginf=0, nan=0)

        f, ax1 = plt.subplots(1, 1)
        f.set_size_inches(set_size(subplots=(1, 1), fraction=0.5))
        f.patch.set_facecolor("white")

        if not self.SameCMAP or which == "CM_T":
            normlin = colors.Normalize(vmin=0, vmax=cm_Max)
            normlog = colors.LogNorm(vmin=cm_Min, vmax=cm_Max)
        else:
            normlin = self.Get_SAMECMAP_Norm(cm.shape[0], which=which, override="Lin")
            normlog = self.Get_SAMECMAP_Norm(cm.shape[0], which=which, override="Log")

        if not log:
            im1 = self.PlotCM(
                cm + 1e-16,
                cm_err,
                labels,
                ax1,
                origin="lower",
                cmap=cmap_A,
                norm=normlin,
                thumb=True,
            )
        else:
            im1 = self.PlotCM(
                cm + 1e-16,
                cm_err,
                labels,
                ax1,
                origin="lower",
                cmap=cmap_A,
                norm=normlog,
                thumb=True,
            )

        # cax1 = f.add_axes([ax1.get_position().x1+0.01,ax1.get_position().y0,0.02,ax1.get_position().height])
        # plt.tight_layout()
        return f, ax1, im1

    def plot_comparesexes_contact_matrix(
        self, bin_type, contact_type, which="NCM", MaxAgeBin=100
    ):
        """
        Function to plot difference in contact matrices between men and women for bin_type, contact_type.

        Parameters
        ----------
            binType:
                Name of bin type syoa, AC etc
            contact_type:
                Location of contacts
            which:
                str, which matrix type to collect "NCM", "NCM_R", "CM_T"

        Returns
        -------
            (ax1,ax2):
                matplotlib axes objects (Linear and Log)
        """
        # plt.rcParams["figure.figsize"] = (15, 5)
        f, (ax1, ax2) = plt.subplots(1, 2)
        f.set_size_inches(set_size(subplots=(1, 2), fraction=1))
        f.patch.set_facecolor("white")

        labels = self.CMPlots_GetLabels(self.age_bins[bin_type])

        cm_M, _ = self.CMPlots_GetCM(bin_type, contact_type, "male", which)
        cm_F, _ = self.CMPlots_GetCM(bin_type, contact_type, "female", which)
        cm = cm_M - cm_F

        cm, cm_err, labels = self.CMPlots_UsefulCM(
            bin_type, cm, None, labels, MaxAgeBin
        )

        cm_Min = -1e-1
        cm_Max = 1e-1

        if not self.SameCMAP:
            normlin = colors.Normalize(vmin=cm_Max, vmax=cm_Max)
            normlog = colors.SymLogNorm(linthresh=1, vmin=cm_Min, vmax=cm_Max)
        else:
            normlin = self.Get_SAMECMAP_Norm(
                cm.shape[0], which=which, override="SymLin"
            )
            normlog = self.Get_SAMECMAP_Norm(
                cm.shape[0], which=which, override="SymLog"
            )

        cm = np.nan_to_num(cm, posinf=cm_Max, neginf=0, nan=0)

        im1 = self.PlotCM(
            cm + 1e-16, cm_err, labels, ax1, origin="lower", cmap=cmap_A, norm=normlin
        )
        im2 = self.PlotCM(
            cm + 1e-16, cm_err, labels, ax2, origin="lower", cmap=cmap_B, norm=normlog
        )

        f.colorbar(im1, ax=ax1, extend="both", label="$M - F$")
        f.colorbar(im2, ax=ax2, extend="both", label="$M - F$")

        # ax1.set_title("Linear Scale")
        # ax2.set_title("Log Scale")
        # f.suptitle(f"Male - female {bin_type} binned contacts in {contact_type}")
        # plt.tight_layout()
        return (ax1, ax2)

    def plot_stacked_contacts(self, bin_type, contact_types=None):
        """
        Plot average contacts per day in each location.

        Parameters
        ----------
            binType:
                Name of bin type syoa, AC etc
            contact_types:
                List of the contact_type locations (or none to grab all of them)

        Returns
        -------
            ax:
                matplotlib axes object

        """
        # plt.rcParams["figure.figsize"] = (10, 5)
        f, ax = plt.subplots()
        f.set_size_inches(set_size(subplots=(1, 2), fraction=1))
        f.patch.set_facecolor("white")

        average_contacts = self.average_contacts[bin_type]
        bins = self.age_bins[bin_type]
        lower = np.zeros(len(bins) - 1)

        mids = 0.5 * (bins[:-1] + bins[1:])
        widths = bins[1:] - bins[:-1]
        plotted = 0

        if contact_types is None:
            contact_types = self.contact_types

        for ii, contact_type in enumerate(contact_types):
            if contact_type in ["shelter_intra", "shelter_inter", "informal_work"]:
                continue
            if contact_type not in average_contacts.columns:
                print(f"No contact_type {contact_type}")
                continue
            if contact_type == "global":
                ax.plot(
                    mids,
                    average_contacts[contact_type],
                    linestyle="-",
                    color="black",
                    label="Total",
                )
                continue

            if plotted > len(plt.rcParams["axes.prop_cycle"].by_key()["color"]) - 1:
                hatch = "//"
            else:
                hatch = None

            heights = average_contacts[contact_type]
            ax.bar(
                mids,
                heights,
                widths,
                bottom=lower,
                hatch=hatch,
                label=contact_type,
                edgecolor="black",
                linewidth=0,
            )
            plotted += 1

            lower = lower + heights

        ax.set_xlim(bins[0], bins[-1])

        ax.legend(bbox_to_anchor=(0.5, 1.02), loc="lower center", ncol=3)
        ax.set_xlabel("Age")
        ax.set_ylabel("average contacts per day")
        f.subplots_adjust(top=0.70)
        # plt.tight_layout()
        return ax

    def plot_population_at_locs_variations(self, locations):
        """
        Plot variations of median values of attendence across all venues of each type

        Parameters
        ----------
            locations:
                list of locations to plot for
        Returns
        -------
            ax:
                matplotlib axes object

        """
        # Get variations between days
        Weekday_Names = self.day_types["weekday"]
        Weekend_Names = self.day_types["weekend"]

        #

        df = pd.DataFrame()
        df = self.location_counters_day["loc"][locations]["unisex"]
        df["t"] = pd.to_datetime(self.location_counters_day["Timestamp"].values)
        df["day"] = [day.day_name() for day in df["t"]]

        means = np.zeros(len(DaysOfWeek_Names))
        stds = np.zeros(len(DaysOfWeek_Names))
        medians = np.zeros(len(DaysOfWeek_Names))
        for day_i in range(len(DaysOfWeek_Names)):
            day = DaysOfWeek_Names[day_i]

            data = df[df["day"] == day][
                df.columns[~df.columns.isin(["t", "day"])]
            ].values.flatten()
            data = data[data > 0]

            if len(data) == 0:
                continue

            means[day_i] = np.nanmean(data)
            stds[day_i] = np.nanstd(data, ddof=1)
            medians[day_i] = np.nanmedian(data)

        # plt.rcParams["figure.figsize"] = (15, 5)
        f, (ax1, ax2) = plt.subplots(1, 2)
        f.set_size_inches(set_size(subplots=(1, 2), fraction=1))
        f.patch.set_facecolor("white")
        ax1.bar(
            np.arange(len(DaysOfWeek_Names)), means, alpha=0.4, color="b", label="mean"
        )
        ax1.bar(
            np.arange(len(DaysOfWeek_Names)),
            medians,
            alpha=0.4,
            color="g",
            label="median",
        )
        # ax1.errorbar(
        #     np.arange(len(DaysOfWeek_Names)),
        #     means,
        #     [stds, stds],
        #     color="black",
        #     label="std errorbar",
        # )
        labels = []
        for i in range(len(DaysOfWeek_Names)):
            labels += [DaysOfWeek_Names[i][:2]]

        ax1.set_xticks(np.arange(len(DaysOfWeek_Names)))
        ax1.set_xticklabels(labels)
        # ax1.set_ylabel("Unique Attendees per day")
        # ax1.set_xlabel("Day of week")
        ax1.set_ylim([0, np.nanmax(means) * 1.4])
        ax1.legend()

        # Get variations between days and time of day
        df = pd.DataFrame()
        df = self.location_counters["loc"][locations]["unisex"]
        df["t"] = pd.to_datetime(
            self.location_counters["Timestamp"].values, format="%d/%m/%y %H:%M:%S"
        )
        df["dt"] = np.array(self.location_counters["delta_t"], dtype=float)
        df["day"] = [day.day_name() for day in df["t"]]

        available_days = np.unique(df["day"].values)
        dts = {}
        times = {}
        timesmid = {}

        for day_i in range(len(DaysOfWeek_Names)):
            day = DaysOfWeek_Names[day_i]
            data = df[df["day"] == day]

            dts[day] = []
            times[day] = [df["t"].iloc[0]]
            timesmid[day] = []

            for i in range(len(data["dt"].values)):

                dts[day].append(df["dt"].values[i])
                timesmid[day].append(
                    times[day][-1] + datetime.timedelta(hours=dts[day][-1]) / 2
                )
                times[day].append(
                    times[day][-1] + datetime.timedelta(hours=dts[day][-1])
                )
                if sum(dts[day]) >= 24:
                    break

            dts[day] = np.array(dts[day])
            times[day] = np.array(times[day])
            timesmid[day] = np.array(timesmid[day])

        medians_days = {}
        means_days = {}
        stds_days = {}

        ymax = -1e3
        ymin = 1e3
        for day_i in range(len(DaysOfWeek_Names)):
            day = DaysOfWeek_Names[day_i]
            if day not in available_days:
                continue
            data = df[df["day"] == day][df.columns[~df.columns.isin(["day"])]]
            total_persons = (
                data[data.columns[~data.columns.isin(["dt", "t"])]].sum(axis=0).values
            )
            total_persons = total_persons[total_persons > 0]

            medians_days[day] = []
            means_days[day] = []
            stds_days[day] = []
            for time_i in range(len(dts[day])):
                data_dt = data[data.columns[~data.columns.isin(["dt", "t"])]].values[
                    time_i
                ]
                data_dt = data_dt[data_dt > 1]
                if len(data_dt) == 0:
                    medians_days[day].append(0)
                    means_days[day].append(0)
                    stds_days[day].append(0)
                else:
                    medians_days[day].append(np.nanmedian(data_dt))
                    means_days[day].append(np.nanmean(data_dt))
                    stds_days[day].append(np.nanstd(data_dt, ddof=1))

            if ymax < np.nanmax(means_days[day]):
                ymax = np.nanmax(means_days[day])
            if ymin > np.nanmin(means_days[day]):
                ymin = np.nanmin(means_days[day])

        xlim = [times[Weekday_Names[0]][0], times[Weekday_Names[0]][-1]]
        for day_i in range(len(DaysOfWeek_Names)):
            day = DaysOfWeek_Names[day_i]
            if day not in available_days:
                continue
            timesmid[day] = np.insert(
                timesmid[day], 0, timesmid[day][-1] - datetime.timedelta(days=1), axis=0
            )
            timesmid[day] = np.insert(
                timesmid[day],
                len(timesmid[day]),
                timesmid[day][1] + datetime.timedelta(days=1),
                axis=0,
            )
            medians_days[day] = np.insert(
                medians_days[day], 0, medians_days[day][-1], axis=0
            )
            medians_days[day] = np.insert(
                medians_days[day], len(medians_days[day]), medians_days[day][1], axis=0
            )
            means_days[day] = np.insert(means_days[day], 0, means_days[day][-1], axis=0)
            means_days[day] = np.insert(
                means_days[day], len(means_days[day]), means_days[day][1], axis=0
            )

        for day_i in range(len(DaysOfWeek_Names)):
            day = DaysOfWeek_Names[day_i]
            if day not in available_days:
                continue
            if day in Weekend_Names:
                linestyle = "--"
            else:
                linestyle = "-"
            # ax2.plot(timesmid[day], medians_days[day], label=DaysOfWeek_Names[day_i], linestyle=linestyle)
            ax2.plot(
                timesmid[day],
                means_days[day],
                label=DaysOfWeek_Names[day_i],
                linestyle=linestyle,
            )

        alphas = [0.1, 0.2]
        ylim = [-abs(ymin * 1.1), abs(ymax * 1.1)]
        for time_i in range(len(dts[Weekday_Names[0]])):
            ax2.fill_between(
                [times[Weekday_Names[0]][time_i], times[Weekday_Names[0]][time_i + 1]],
                ylim[0],
                ylim[1],
                color="g",
                alpha=alphas[time_i % 2],
            )
        ax2.axhline(0, color="grey", linestyle="--")

        # ax2.set_ylabel("Mean Unique Attendees per timeslot")
        # ax2.set_xlabel("Time of day [hour]")
        # Define the date format
        ax2.xaxis.set_major_locator(mdates.HourLocator(byhour=None, interval=4))
        ax2.xaxis.set_major_formatter(DateFormatter("%H"))
        ax2.set_xlim(xlim)
        ax2.set_ylim([0, ylim[1]])
        ax2.legend()
        # plt.tight_layout()
        return (ax1, ax2)

    def plot_AgeProfileRatios(
        self, contact_type="global", bin_type="syoa", sex="unisex"
    ):
        """
        Plot demographic counts for each location and ratio of counts in age bins.

        Parameters
        ----------
            contact_types:
                List of the contact_type locations (or none to grab all of them)
            binType:
                Name of bin type syoa, AC etc
            sex:
                Which sex of population ["male", "female", "unisex"]


        Returns
        -------
            ax:
                matplotlib axes object

        """

        if bin_type != "Interaction":
            pop_tots = self.location_cum_pop[bin_type][contact_type][sex]
            global_age_profile = self.age_profiles[bin_type]["global"][sex]
            Bins = np.array(self.age_bins[bin_type])

            Labels = self.CMPlots_GetLabels(Bins)
            Bincenters = 0.5 * (Bins[1:] + Bins[:-1])
            Bindiffs = np.abs(Bins[1:] - Bins[:-1])
        else:
            Bins = np.array(self.IM[contact_type]["bins"])
            AgeDiscrete = self.IM[contact_type]["type"]
            if AgeDiscrete == "Age":
                pop_tots = self.location_cum_pop[bin_type][contact_type][sex]

                contacts_loc = self.contacts_df[self.contacts_df[contact_type] != 0]
                AgesCount = contacts_loc.groupby([Bins], dropna=False).size()
                AgesCount = AgesCount.reindex(len(Bins), fill_value=0)
                global_age_profile = self.age_profiles[bin_type]["global"][sex]

                Labels = self.CMPlots_GetLabels(Bins)
                Bincenters = 0.5 * (Bins[1:] + Bins[:-1])
                Bindiffs = np.abs(Bins[1:] - Bins[:-1])

            if AgeDiscrete == "Discrete":
                Labels = Bins
                pass

        Height_G = global_age_profile / Bindiffs
        Height_P = pop_tots / Bindiffs

        ws_G = np.zeros((Bins.shape[0] - 1, Bins.shape[0] - 1))
        ws_P = np.zeros((Bins.shape[0] - 1, Bins.shape[0] - 1))
        # Loop over elements
        for i in range(ws_G.shape[0]):
            for j in range(ws_G.shape[1]):
                # Population rescaling
                ws_G[i, j] = Height_G[i] / Height_G[j]
                ws_P[i, j] = Height_P[i] / Height_P[j]

        # plt.rcParams["figure.figsize"] = (15, 5)
        f, (ax1, ax2) = plt.subplots(1, 2)
        f.set_size_inches(set_size(subplots=(1, 1), fraction=1))
        f.patch.set_facecolor("white")

        vmax_G = np.nan
        vmax_P = np.nan
        if np.isfinite(ws_G).sum() != 0:
            vmax_G = ws_G[np.isfinite(ws_G)].max() * 2
        if np.isfinite(ws_P).sum() != 0:
            vmax_P = ws_P[np.isfinite(ws_P)].max() * 2

        vmax = np.nanmax([vmax_G, vmax_P])
        if np.isnan(vmax) or vmax is None:
            vmax = 1e-1

        vmin = 10 ** (-1 * np.log10(vmax))
        # ax1_ins = ax1.inset_axes([0.8, 1.0, 0.2, 0.2])

        norm = colors.LogNorm(vmin=vmin, vmax=vmax)
        im_P = self.PlotCM(
            ws_P, None, Labels, ax1, origin="lower", cmap=cmap_B, norm=norm
        )
        # im_G = self.PlotCM(
        #    ws_G, None, Labels, ax1_ins, origin="lower", cmap=cmap_B, norm=norm
        # )

        f.colorbar(im_P, ax=ax1, label=r"$\dfrac{Age_{y}}{Age_{x}}$", extend="both")
        plt.bar(
            x=Bincenters,
            height=Height_G / sum(Height_G),
            width=Bindiffs,
            tick_label=Labels,
            alpha=0.5,
            color="blue",
            label="Ground truth",
        )
        plt.bar(
            x=Bincenters,
            height=Height_P / sum(Height_P),
            width=Bindiffs,
            tick_label=Labels,
            alpha=0.5,
            color="red",
            label="tracker",
        )
        ax2.set_xlabel("Age")
        ax2.set_ylabel("Normed Population size")
        ax2.set_xlim([Bins[0], Bins[-1]])
        ax2.set_yscale("log")
        plt.xticks(rotation=90)
        # f.suptitle(f"Age profile of {contact_type}")
        plt.legend()
        plt.tight_layout()
        return (ax1, ax2)

    def plot_DistanceTraveled(self, location, day):
        """
        Plot histogram of commuting distances from home

        Parameters
        ----------
            location:
                The venue to look at
            day:
                The day of the week

        Returns
        -------
            ax:
                matplotlib axes object

        """
        plural_locations = Tracker.pluralize(self, location)
        Nlocals = self.NVenues[plural_locations]
        dat = self.travel_distance[location]
        Total = dat.iloc[:, 1].sum()

        # Truncate plot on relvent bins.
        CumSum = np.cumsum(dat.iloc[:, 1].values)
        indexlast = len(CumSum) - np.sum(CumSum == CumSum[-1])
        maxkm = dat.iloc[indexlast, 0] + 3.5 * (dat.iloc[1, 0] - dat.iloc[0, 0])

        # plt.rcParams["figure.figsize"] = (10, 5)
        f, ax = plt.subplots(1, 1)
        f.set_size_inches(set_size(subplots=(1, 2), fraction=1))
        f.patch.set_facecolor("white")
        ax.bar(
            x=dat["bins"],
            height=(100 * dat.iloc[:, 1]) / Total,
            width=(dat["bins"].iloc[1] - dat["bins"].iloc[0]),
            color="b",
            alpha=0.4,
        )
        # ax.set_title(f"{Nlocals} available {location}")
        ax.set_ylabel(r"Frequency [%]")
        ax.set_xlabel(r"Travel distance from shelter [km]")
        ax.set_xlim([0, maxkm])
        return ax

    ###################################################
    # Master plotter ##################################
    ###################################################

    def make_plots(
        self,
        plot_BBC=False,
        plot_thumbprints=False,
        SameCMAP=False,
        plot_INPUTOUTPUT=True,
        plot_AvContactsLocation=True,
        plot_dTLocationPopulation=True,
        plot_InteractionMatrices=True,
        plot_ContactMatrices=True,
        plot_CompareSexMatrices=True,
        plot_AgeBinning=True,
        plot_Distances=True,
        MaxAgeBin=100,
    ):
        """
        Make plots.

        Parameters
        ----------
            plot_BBC:
                bool, if we want to compare to BBC Pandemic data.
            plot_thumbprints:
                bool, To plot thumbnail style plots for plot_ContactMatrices and plot_CompareSexMatrices
            SameCMAP:
                bool, To plot same colour map accross all similar dimension contact matrices
            plot_INPUTOUTPUT:
                bool,
            plot_AvContactsLocation:
                bool, To plot average contacts per location plots
            plot_dTLocationPopulation:
                bool, To plot average people per location at timestamp
            plot_InteractionMatrices:
                bool, To plot interaction matrices
            plot_ContactMatrices:
                bool, To plot contact matrices
            plot_CompareSexMatrices:
                bool, To plot comparison of sexes matrices
            plot_AgeBinning:
                bool, To plot w weight matrix to compare demographics
            plot_Distances:
                bool, To plot the distance traveled from shelter to locations
        Returns
        -------
            None
        """
        CbarMultiplier = 3
        aspect = 40

        logger.info(f"Rank {mpi_rank} -- Begin plotting")
        if self.group_type_names == []:
            return 1

        self.SameCMAP = SameCMAP

        relevant_bin_types = list(self.CM.keys())
        relevant_bin_types_short = ["syoa", "AC"]
        relevant_contact_types = list(self.CM["syoa"].keys())
        IM_contact_types = list(self.CM["Interaction"].keys())

        if self.Normalization_Type == "U":
            NormFolder = "VenueNorm"
        elif self.Normalization_Type == "P":
            NormFolder = "PopNorm"

        CMTypes = ["NCM", "NCM_R", "NCM_V"]

        if plot_INPUTOUTPUT:
            plot_dir_1 = (
                self.record_path / "Graphs" / "Contact_Matrices_INOUT" / NormFolder
            )
            plot_dir_1.mkdir(exist_ok=True, parents=True)
            if "Paper" in relevant_bin_types:
                rbt = "Paper"
            else:
                rbt = "syoa"
            for rct in self.IM.keys():
                if rct not in relevant_contact_types:
                    continue

                which = "NCM_R"
                plot_BBC_Sheet = False

                if (
                    plot_BBC
                    and rct in ["household", "school", "company"]
                    and rbt == "Paper"
                ):
                    if rct == "household":
                        plot_BBC_Sheet = "all_home"
                    if rct == "school":
                        plot_BBC_Sheet = "all_school"
                    if rct == "company":
                        plot_BBC_Sheet = "all_work"
                    which = "NCM_R"

                self.plot_contact_matrix_INOUT(
                    bin_type=rbt,
                    contact_type=rct,
                    sex="unisex",
                    which=which,
                    plot_BBC_Sheet=plot_BBC_Sheet,
                    MaxAgeBin=MaxAgeBin,
                )
                plt.savefig(plot_dir_1 / f"{rct}.pdf", dpi=dpi, bbox_inches="tight")
                plt.close()
        logger.info(f"Rank {mpi_rank} -- Input vs output done")

        if plot_AvContactsLocation:
            plot_dir = self.record_path / "Graphs" / f"Average_Contacts"
            plot_dir.mkdir(exist_ok=True, parents=True)
            for rbt in relevant_bin_types_short:
                stacked_contacts_plot = self.plot_stacked_contacts(
                    bin_type=rbt, contact_types=relevant_contact_types
                )
                stacked_contacts_plot.plot()
                plt.savefig(
                    plot_dir / f"{rbt}_contacts.pdf", dpi=dpi, bbox_inches="tight"
                )
                plt.close()
        logger.info(f"Rank {mpi_rank} -- Av contacts done")

        if plot_dTLocationPopulation:
            plot_dir = self.record_path / "Graphs" / "Location_Pops"
            plot_dir.mkdir(exist_ok=True, parents=True)
            for locations in self.location_counters["loc"].keys():
                self.plot_population_at_locs_variations(locations)
                plt.savefig(
                    plot_dir / f"{locations}_Variations.pdf",
                    dpi=dpi,
                    bbox_inches="tight",
                )
                plt.close()

                # self.plot_population_at_locs(locations)
                # plt.savefig(plot_dir / f"{locations}.pdf", dpi=dpi, bbox_inches="tight")
                # plt.close()
        logger.info(f"Rank {mpi_rank} -- Pop at locations done")

        if plot_InteractionMatrices:
            plot_dir = self.record_path / "Graphs" / "IM" / NormFolder
            plot_dir.mkdir(exist_ok=True, parents=True)
            for rct in self.IM.keys():
                self.plot_interaction_matrix(contact_type=rct)
                plt.savefig(plot_dir / f"{rct}.pdf", dpi=dpi, bbox_inches="tight")
                plt.close()

                if plot_thumbprints:
                    fig, ax1, im1 = self.plot_interaction_matrix_thumb(
                        log=False, contact_type=rct
                    )
                    plt.savefig(
                        plot_dir / f"{rct}_thumbnail.pdf", dpi=100, bbox_inches="tight"
                    )
                    if rct == list(self.IM.keys())[0] and SameCMAP:
                        cbar = fig.colorbar(
                            im1,
                            ax=ax1,
                            extend="both",
                            orientation="horizontal",
                            aspect=aspect,
                            format="%g",
                        )
                        # cbar.ticklabel_format(style='plain')
                        ax1.remove()
                        fig.set_size_inches(
                            fig.get_size_inches()[0] * CbarMultiplier,
                            fig.get_size_inches()[1],
                        )
                        plt.savefig(
                            plot_dir / f"colourbar.pdf", dpi=100, bbox_inches="tight"
                        )
                    plt.close()

                    fig, ax1, im1 = self.plot_interaction_matrix_thumb(
                        log=True, contact_type=rct
                    )
                    plt.savefig(
                        plot_dir / f"{rct}_thumbnail_log.pdf",
                        dpi=100,
                        bbox_inches="tight",
                    )
                    if rct == list(self.IM.keys())[0] and SameCMAP:
                        fig.colorbar(
                            im1,
                            ax=ax1,
                            extend="both",
                            orientation="horizontal",
                            aspect=aspect,
                            format="%g",
                        )
                        ax1.remove()
                        fig.set_size_inches(
                            fig.get_size_inches()[0] * CbarMultiplier,
                            fig.get_size_inches()[1],
                        )
                        plt.savefig(
                            plot_dir / f"colourbar_log.pdf",
                            dpi=100,
                            bbox_inches="tight",
                        )
                    plt.close()
        logger.info(f"Rank {mpi_rank} -- Interaction matrix plots done")

        if plot_ContactMatrices:
            for CMType in CMTypes:
                plot_dir_1 = (
                    self.record_path
                    / "Graphs"
                    / "Contact_Matrices"
                    / NormFolder
                    / CMType
                )
                plot_dir_1.mkdir(exist_ok=True, parents=True)

                for rbt in relevant_bin_types:

                    plot_dir_2 = plot_dir_1 / f"{rbt}"
                    plot_dir_2.mkdir(exist_ok=True, parents=True)

                    if rbt != "Interaction":
                        for sex in self.contact_sexes:
                            plot_dir_3 = plot_dir_2 / f"{sex}"
                            plot_dir_3.mkdir(exist_ok=True, parents=True)

                            for rct in relevant_contact_types:
                                self.plot_contact_matrix(
                                    bin_type=rbt,
                                    contact_type=rct,
                                    sex=sex,
                                    which=CMType,
                                    MaxAgeBin=MaxAgeBin,
                                )
                                plt.savefig(
                                    plot_dir_3 / f"{rct}.pdf",
                                    dpi=dpi,
                                    bbox_inches="tight",
                                )
                                plt.close()

                                if plot_thumbprints:
                                    fig, ax1, im1 = self.plot_contact_matrix_thumb(
                                        log=False,
                                        bin_type=rbt,
                                        contact_type=rct,
                                        sex=sex,
                                        which=CMType,
                                        MaxAgeBin=MaxAgeBin,
                                    )
                                    plt.savefig(
                                        plot_dir_3 / f"{rct}_thumbnail.pdf",
                                        dpi=100,
                                        bbox_inches="tight",
                                    )
                                    if rct == relevant_contact_types[0] and SameCMAP:
                                        fig.colorbar(
                                            im1,
                                            ax=ax1,
                                            extend="both",
                                            orientation="horizontal",
                                            aspect=aspect,
                                            format="%g",
                                        )
                                        ax1.remove()
                                        fig.set_size_inches(
                                            fig.get_size_inches()[0] * CbarMultiplier,
                                            fig.get_size_inches()[1],
                                        )
                                        plt.savefig(
                                            plot_dir_3 / f"colourbar.pdf",
                                            dpi=100,
                                            bbox_inches="tight",
                                        )
                                    plt.close()

                                    fig, ax1, im1 = self.plot_contact_matrix_thumb(
                                        log=True,
                                        bin_type=rbt,
                                        contact_type=rct,
                                        sex=sex,
                                        which=CMType,
                                        MaxAgeBin=MaxAgeBin,
                                    )
                                    plt.savefig(
                                        plot_dir_3 / f"{rct}_thumbnail_log.pdf",
                                        dpi=100,
                                        bbox_inches="tight",
                                    )
                                    if rct == relevant_contact_types[0] and SameCMAP:
                                        fig.colorbar(
                                            im1,
                                            ax=ax1,
                                            extend="both",
                                            orientation="horizontal",
                                            aspect=aspect,
                                            format="%g",
                                        )
                                        ax1.remove()
                                        fig.set_size_inches(
                                            fig.get_size_inches()[0] * CbarMultiplier,
                                            fig.get_size_inches()[1],
                                        )
                                        plt.savefig(
                                            plot_dir_3 / f"colourbar_log.pdf",
                                            dpi=100,
                                            bbox_inches="tight",
                                        )
                                    plt.close()
                    else:
                        for rct in IM_contact_types:
                            sex = "unisex"
                            self.plot_contact_matrix(
                                bin_type=rbt,
                                contact_type=rct,
                                sex=sex,
                                which=CMType,
                                MaxAgeBin=MaxAgeBin,
                            )
                            plt.savefig(
                                plot_dir_2 / f"{rct}.pdf", dpi=150, bbox_inches="tight"
                            )
                            plt.close()

                            if plot_thumbprints:
                                fig, ax1, im1 = self.plot_contact_matrix_thumb(
                                    log=False,
                                    bin_type=rbt,
                                    contact_type=rct,
                                    sex=sex,
                                    which=CMType,
                                    MaxAgeBin=MaxAgeBin,
                                )
                                plt.savefig(
                                    plot_dir_2 / f"{rct}_thumbnail.pdf",
                                    dpi=100,
                                    bbox_inches="tight",
                                )
                                if rct == IM_contact_types[0]:
                                    fig.colorbar(
                                        im1,
                                        ax=ax1,
                                        extend="both",
                                        aspect=aspect,
                                        orientation="horizontal",
                                        format="%g",
                                    )
                                    ax1.remove()
                                    fig.set_size_inches(
                                        fig.get_size_inches()[0] * CbarMultiplier,
                                        fig.get_size_inches()[1],
                                    )
                                    plt.savefig(
                                        plot_dir_2 / f"colourbar.pdf",
                                        dpi=100,
                                        bbox_inches="tight",
                                    )
                                plt.close()

                                fig, ax1, im1 = self.plot_contact_matrix_thumb(
                                    log=True,
                                    bin_type=rbt,
                                    contact_type=rct,
                                    sex=sex,
                                    which=CMType,
                                    MaxAgeBin=MaxAgeBin,
                                )
                                plt.savefig(
                                    plot_dir_2 / f"{rct}_thumbnail_log.pdf",
                                    dpi=100,
                                    bbox_inches="tight",
                                )
                                if rct == IM_contact_types[0]:
                                    fig.colorbar(
                                        im1,
                                        ax=ax1,
                                        extend="both",
                                        aspect=aspect,
                                        orientation="horizontal",
                                        format="%g",
                                    )
                                    ax1.remove()
                                    fig.set_size_inches(
                                        fig.get_size_inches()[0] * CbarMultiplier,
                                        fig.get_size_inches()[1],
                                    )
                                    plt.savefig(
                                        plot_dir_2 / f"colourbar_log.pdf",
                                        dpi=100,
                                        bbox_inches="tight",
                                    )
                                plt.close()
        logger.info(f"Rank {mpi_rank} -- CM plots done")

        if plot_CompareSexMatrices:
            for CMType in CMTypes:
                plot_dir_1 = (
                    self.record_path
                    / "Graphs"
                    / "Contact_Matrices"
                    / NormFolder
                    / CMType
                )
                plot_dir_1.mkdir(exist_ok=True, parents=True)

                for rbt in relevant_bin_types:
                    if rbt == "Interaction":
                        continue

                    plot_dir_2 = plot_dir_1 / f"{rbt}"
                    plot_dir_2.mkdir(exist_ok=True, parents=True)

                    for rct in relevant_contact_types:
                        if (
                            "male" in self.contact_sexes
                            and "female" in self.contact_sexes
                        ):
                            plot_dir_3 = plot_dir_2 / "CompareSexes"
                            plot_dir_3.mkdir(exist_ok=True, parents=True)

                            self.plot_comparesexes_contact_matrix(
                                bin_type=rbt, contact_type=rct, which=CMType
                            )
                            plt.savefig(
                                plot_dir_3 / f"{rct}.pdf", dpi=dpi, bbox_inches="tight"
                            )
                            plt.close()
        logger.info(f"Rank {mpi_rank} -- CM between sexes done")

        if plot_AgeBinning:
            plot_dir = self.record_path / "Graphs" / "Age_Binning"
            plot_dir.mkdir(exist_ok=True, parents=True)
            for rbt in ["syoa", "Paper"]:
                if rbt not in self.age_bins.keys():
                    continue
                for rct in relevant_contact_types:
                    self.plot_AgeProfileRatios(
                        contact_type=rct, bin_type=rbt, sex="unisex"
                    )
                    plt.savefig(
                        plot_dir / f"{rbt}_{rct}.pdf", dpi=dpi, bbox_inches="tight"
                    )
                    plt.close()
        logger.info(f"Rank {mpi_rank} -- Age bin matrix done")

        if plot_Distances:
            plot_dir = self.record_path / "Graphs" / "Distance_Traveled"
            plot_dir.mkdir(exist_ok=True, parents=True)
            for locations in self.location_counters["loc"].keys():
                for day in self.travel_distance.keys():
                    self.plot_DistanceTraveled(locations, day)
                    plt.savefig(
                        plot_dir / f"{locations}.pdf", dpi=dpi, bbox_inches="tight"
                    )
                    plt.close()
                    break
        logger.info(f"Rank {mpi_rank} -- Distance plots done")
        return 1
