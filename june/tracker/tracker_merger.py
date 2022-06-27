from cProfile import label
from concurrent.futures import thread
import numpy as np
import yaml
import pandas as pd

from pathlib import Path
from june import paths


from june.world import World

import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates
import datetime

from june.paths import data_path, configs_path
default_BBC_Pandemic_loc = data_path / "BBC_Pandemic"

DaysOfWeek_Names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

#####################################################################################################################################################################
                            ################################### Plotting functions ##################################
#####################################################################################################################################################################

class MergerClass:
    """
    Class to plot everything tracker related

    Parameters
    ----------
    record_path:
        path for results directory

    Tracker_Contact_Type:

    Params:

    IM:

    CM_T:

    NCM:

    NCM_R:
    
    average_contacts:

    location_counters:

    location_counters_day:

    location_cum_pop:

    age_profiles:

    travel_distance:

    Returns
    -------
        The tracker plotting class

    """
    def __init__(
        self,        
        record_path=Path(""),
        Tracker_Contact_Type="1D",

        Params=None,

        IM=None,
        CM_T=None,
        NCM=None,
        NCM_R=None,

        average_contacts=None,
        location_counters=None,
        location_counters_day=None,

        location_cum_pop = None,
        age_profiles = None,

        travel_distance = None,
    ):
        self.record_path = record_path
        self.Tracker_Contact_Type = Tracker_Contact_Type


        if Params is None:
            with open(self.record_path / "data_output" / "tracker_Simulation_Params.yaml") as f:
                self.Params = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self.Params = Params

        if IM is None:
            with open(self.record_path / "data_output" / "CM_yamls" / "tracker_IM.yaml") as f:
                self.IM = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self.IM = IM

        if CM_T is None:
            with open(self.record_path / "data_output" / "CM_yamls" / f"tracker_{self.Tracker_Contact_Type}_Total_CM.yaml") as f:
                self.CM_T = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self.CM_T = CM_T

        if NCM is None:
            with open(self.record_path / "data_output" / "CM_yamls" / f"tracker_{self.Tracker_Contact_Type}_NCM.yaml") as f:
                self.NCM = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self.NCM = NCM

        if NCM_R is None:
            with open(self.record_path / "data_output" / "CM_yamls" / f"tracker_{self.Tracker_Contact_Type}_NCM_R.yaml") as f:
                self.NCM_R = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self.NCM_R = NCM_R

        #Get Parameters of simulation
        self.total_days = self.Params["total_days"]
        self.day_types = {"weekend":self.Params["Weekend_Names"],"weekday":self.Params["Weekday_Names"]}
        self.NVenues = self.Params["NVenues"]
        #Get all the bin types
        self.relevant_bin_types = list(self.CM_T.keys())
        #Get all location names
        self.group_type_names = list(self.CM_T["syoa"].keys())
        #Get all CM options
        self.CM_Keys = list(self.CM_T["syoa"][self.group_type_names[0]].keys())
        #Get all contact sexes
        self.contact_sexes = list(self.CM_T["syoa"][self.group_type_names[0]]["sex"].keys())
    
        self.age_bins = {}
        for rbt in self.relevant_bin_types:
            if rbt == "Interaction":
                continue
            self.age_bins[rbt] = np.array(self.CM_T[rbt][self.group_type_names[0]]["bins"])

        if average_contacts is None:
            self.average_contacts = {}
            for rbt in self.relevant_bin_types:
                if rbt == "Interaction":
                    continue
                self.average_contacts[rbt] = pd.read_excel(
                    self.record_path / "data_output" / "Venue_AvContacts" / "Average_contacts.xlsx",
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
                    if loc[-1] == "y":
                        sheet_name = loc[:-1] + "ies"
                    else:
                        sheet_name = loc + "s"
                    df = pd.read_excel(
                    self.record_path / "data_output" / "Venue_UniquePops" / filename,
                    sheet_name=sheet_name,
                    index_col=0,
                )
                    self.location_counters["loc"][loc][sex] = df.iloc[:,2:]
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
                    if loc[-1] == "y":
                        sheet_name = loc[:-1] + "ies"
                    else:
                        sheet_name = loc + "s"
                    df = pd.read_excel(
                    self.record_path / "data_output" / "Venue_UniquePops" / filename,
                    sheet_name=sheet_name,
                    index_col=0,
                )
                    self.location_counters_day["loc"][loc][sex] = df.iloc[:,0:]
                    if self.location_counters_day["Timestamp"] is None:
                        self.location_counters_day["Timestamp"] = df["t"]
        else:
            self.location_counters_day = location_counters_day

        if location_cum_pop is None:
            self.location_cum_pop = {}
            for rbt in self.relevant_bin_types:
                self.location_cum_pop[rbt] = {}
                filename = self.record_path / "data_output" / "Venue_TotalDemographics" / f"CumPersonCounts_{rbt}.xlsx"
                for loc in self.group_type_names:
                    self.location_cum_pop[rbt][loc] = {}
                    if rbt == "Interaction" and loc in ["global", "shelter_inter", "shelter_intra"]:
                            continue
                    df = pd.read_excel(
                        filename,
                        sheet_name=loc,
                        index_col=0,
                    )
                    self.location_cum_pop[rbt][loc] = df
        else:
            self.location_cum_pop = location_cum_pop

        if age_profiles is None:
            self.age_profiles = {}
            for rbt in self.relevant_bin_types:
                if rbt == "Interaction":
                    continue
                self.age_profiles[rbt] = {}
                filename = self.record_path / "data_output" / "Venue_Demographics" / f"PersonCounts_{rbt}.xlsx"
                for loc in self.group_type_names:
                    self.age_profiles[rbt][loc] = {}

                    df = pd.read_excel(
                        filename,
                        sheet_name=loc,
                        index_col=0,
                    )
                    self.age_profiles[rbt][loc] = df

        else:
            self.age_profiles = age_profiles

        if travel_distance is None:
            filename = self.record_path / "data_output" / "Venue_TravelDist" / "Distance_traveled.xlsx"
            self.travel_distance= {}
            for loc in self.group_type_names:
                if loc in ["global", "shelter_inter", "shelter_intra"]:
                    continue
                if loc[-1] == "y":
                    sheet_name = loc[:-1] + "ies"
                else:
                    sheet_name = loc + "s"
                df = pd.read_excel(
                    filename,
                    sheet_name=sheet_name,
                    index_col=0,
                )
                self.travel_distance[loc] = df
        else:
            self.travel_distance = travel_distance

#####################################################################################################################################################################
                                ################################### General Plotting ##################################
#####################################################################################################################################################################

 