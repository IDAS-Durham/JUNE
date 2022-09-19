import numpy as np
import yaml
import pandas as pd
from pathlib import Path
import glob

from june.tracker.tracker import Tracker
from june.tracker.tracker_plots import PlotClass

from june.mpi_setup import mpi_comm, mpi_size, mpi_rank
import logging

logger = logging.getLogger("tracker merger")
mpi_logger = logging.getLogger("mpi")

if mpi_rank > 0:
    logger.propagate = False

#######################################################
# Plotting functions ##################################
#######################################################


class MergerClass:
    """
    Class to merge trackers results from multiple MPI runs

    Parameters
    ----------
        record_path:
            location of results directory

    Returns
    -------
    """

    class Timer:
        def __init__(
            self,
        ):
            self.total_days = 1

    def __init__(self, record_path=Path(""), NRanksTest=None):

        self.record_path = record_path
        self.timer = self.Timer()

        if (self.record_path / "Tracker" / "raw_data_output").exists():
            self.MPI = True
        else:
            self.MPI = False

        if not self.MPI:
            pass
        else:
            self.raw_data_path = self.record_path / "Tracker" / "raw_data_output"
            self.merged_data_path = self.record_path / "Tracker" / "merged_data_output"
            self.merged_data_path.mkdir(exist_ok=True, parents=True)

            if NRanksTest is None:
                self.NRanks = len(glob.glob(str(self.raw_data_path / "*.yaml")))
            else:
                self.NRanks = NRanksTest

            with open(self.raw_data_path / "tracker_Simulation_Params_r0_.yaml") as f:
                Params = yaml.load(f, Loader=yaml.FullLoader)

            self.group_type_names = {}
            self.group_type_names[0] = list(Params["NVenues"].keys()) + [
                "care_home_visits",
                "household_visits",
                "global",
            ]
            self.group_type_names["all"] = list(Params["NVenues"].keys()) + ["global"]
            self.binTypes = list(Params["binTypes"])
            self.contact_sexes = list(Params["sexes"])
            self.timer.total_days = int(Params["total_days"])

            Params["MPI_rank"] = "Combined"
            Params["Weekday_Names"] = self.MatrixString(
                matrix=np.array(Params["Weekday_Names"])
            )
            Params["Weekend_Names"] = self.MatrixString(
                matrix=np.array(Params["Weekend_Names"])
            )
            Params["binTypes"] = self.MatrixString(matrix=np.array(Params["binTypes"]))
            Params["sexes"] = self.MatrixString(matrix=np.array(Params["sexes"]))

            for rank in range(1, self.NRanks):
                with open(
                    self.raw_data_path / f"tracker_Simulation_Params_r{rank}_.yaml"
                ) as f:
                    Params_rank = yaml.load(f, Loader=yaml.FullLoader)

                self.group_type_names[rank] = list(Params_rank["NVenues"].keys()) + [
                    "care_home_visits",
                    "household_visits",
                    "global",
                ]

                group_names_update = list(
                    set(self.group_type_names["all"] + self.group_type_names[rank])
                )
                self.group_type_names["all"] = group_names_update

                venues = list(
                    set(Params_rank["NVenues"].keys())
                    & set(self.group_type_names[rank])
                )

                for v in venues:
                    if (
                        v in Params["NVenues"].keys()
                        and v in Params_rank["NVenues"].keys()
                    ):
                        Params["NVenues"][v] += Params_rank["NVenues"][v]
                    elif (
                        v not in Params["NVenues"].keys()
                        and v in Params_rank["NVenues"].keys()
                    ):
                        Params["NVenues"][v] = Params_rank["NVenues"][v]
                    else:
                        continue

                Params["NPeople"] += Params_rank["NPeople"]
            self.Save_CM_JSON(
                dir=self.merged_data_path,
                folder="merged_data_output",
                filename="tracker_Simulation_Params.yaml",
                jsonfile=Params,
            )

        logger.info(
            f"Rank {mpi_rank} -- Initial params loaded -- have following group types { self.group_type_names['all'] }"
        )

    ###########################################################################################
    # Import the useful functions from other Tracker modules ##################################
    ###########################################################################################

    def CM_Norm(self, cm, cm_err, pop_tots, contact_type="global", Which="UNCM"):
        return Tracker.CM_Norm(self, cm, cm_err, pop_tots, contact_type, Which)

    def Get_characteristic_time(self, location):
        return Tracker.Get_characteristic_time(self, location)

    def PolicyText(
        self, Type, contacts, contacts_err, proportional_physical, characteristic_time
    ):
        return Tracker.PolicyText(
            self,
            Type,
            contacts,
            contacts_err,
            proportional_physical,
            characteristic_time,
        )

    def MatrixString(self, matrix, dtypeString="float"):
        return Tracker.MatrixString(self, matrix, dtypeString)

    def pluralise_r(self, loc):
        return Tracker.pluralise_r(self, loc)

    def pluralise(self, loc):
        return Tracker.pluralise(self, loc)

    def initalize_CM_Normalisations(self):
        return Tracker.initalize_CM_Normalisations(self)

    def initalize_CM_All_Normalisations(self):
        return Tracker.initalize_CM_All_Normalisations(self)

    def normalise_1D_CM(self):
        return Tracker.normalise_1D_CM(self)

    def normalise_All_CM(self):
        return Tracker.normalise_All_CM(self)

    def PrintOutResults(self):
        return Tracker.PrintOutResults(self)

    def Save_CM_JSON(self, dir, folder, filename, jsonfile):
        return Tracker.Save_CM_JSON(self, dir, folder, filename, jsonfile)

    def tracker_CMJSON(self, binType, CM, CM_err, NormType):
        return Tracker.tracker_CMJSON(self, binType, CM, CM_err, NormType)

    def contract_matrix(self, CM, bins, method=np.sum):
        return Tracker.contract_matrix(self, CM, bins, method)

    def Calculate_CM_Metrics(self, bin_type, contact_type, CM, CM_err, ratio, sex="unisex"):
        return Tracker.Calculate_CM_Metrics(
            self, bin_type, contact_type, CM, CM_err, ratio, sex
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

    def AttendenceRatio(self, bin_type, contact_type, sex):
        return Tracker.AttendenceRatio(self, bin_type, contact_type, sex)

    def CMPlots_GetCM(self, bin_type, contact_type, sex="unisex", which="UNCM"):
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
                str, which matrix type to collect "CM", "UNCM", "UNCM_R", "CMV", "UNCM_V"

        Returns
        -------
            cm:
                np.array contact matrix
            cm_err:
                np.array contact matrix errors
        """
        if bin_type != "Interaction":
            if which == "CM":
                cm = self.CM[bin_type][contact_type][sex]
                cm_err = self.CM_err[bin_type][contact_type][sex]
            elif which == "UNCM":
                cm = self.UNCM[bin_type][contact_type][sex]
                cm_err = self.UNCM_err[bin_type][contact_type][sex]
            elif which == "UNCM_R":
                cm = self.UNCM_R[bin_type][contact_type][sex]
                cm_err = self.UNCM_R_err[bin_type][contact_type][sex]


            elif which == "CMV":
                cm = self.CMV[bin_type][contact_type][sex]
                cm_err = self.CMV_err[bin_type][contact_type][sex]
            elif which == "UNCM_V":
                cm = self.UNCM_V[bin_type][contact_type][sex]
                cm_err = self.UNCM_V_err[bin_type][contact_type][sex]

        else:
            if which == "CM":
                cm = self.CM[bin_type][contact_type]
                cm_err = self.CM_err[bin_type][contact_type]
            elif which == "UNCM":
                cm = self.UNCM[bin_type][contact_type]
                cm_err = self.UNCM_err[bin_type][contact_type]
            elif which == "UNCM_R":
                cm = self.UNCM_R[bin_type][contact_type]
                cm_err = self.UNCM_R_err[bin_type][contact_type]

            elif which == "CMV":
                cm = self.CMV[bin_type][contact_type]
                cm_err = self.CMV_err[bin_type][contact_type]
            elif which == "UNCM_V":
                cm = self.UNCM_V[bin_type][contact_type]
                cm_err = self.UNCM_V_err[bin_type][contact_type]
        return np.array(cm), np.array(cm_err)

    def IMPlots_GetIM(self, contact_type):
        return Tracker.IMPlots_GetIM(self, contact_type)

    #####################################################
    # Individual Merge ##################################
    #####################################################

    def Travel_Distance(self):
        travel_distance = {}
        for rank in range(0, self.NRanks):
            filename = (
                self.raw_data_path
                / "Venue_TravelDist"
                / f"Distance_traveled_r{rank}_.xlsx"
            )
            for loc in self.group_type_names[rank]:
                if loc in [
                    "global",
                    "shelter_inter",
                    "shelter_intra",
                    "care_home_visits",
                    "household_visits",
                ]:
                    continue
                df = pd.read_excel(filename, sheet_name=loc, index_col=0)
                if loc not in travel_distance.keys():
                    travel_distance[loc] = df
                else:
                    travel_distance[loc].iloc[:, 1:] += df.iloc[:, 1:]
        Save_dir = self.merged_data_path / "Venue_TravelDist"
        Save_dir.mkdir(exist_ok=True, parents=True)
        with pd.ExcelWriter(Save_dir / f"Distance_traveled.xlsx", mode="w") as writer:
            for local in travel_distance.keys():
                travel_distance[local].to_excel(writer, sheet_name=f"{local}")
        return 1

    def CumPersonCounts(self):
        self.location_cum_pop = {}
        for rbt in self.binTypes:
            self.location_cum_pop[rbt] = {}
            for rank in range(0, self.NRanks):
                filename = (
                    self.raw_data_path
                    / "Venue_TotalDemographics"
                    / f"CumPersonCounts_{rbt}_r{rank}_.xlsx"
                )
                for loc in self.group_type_names[rank]:
                    if loc in ["care_home_visits", "household_visits"]:
                        continue

                    loc = self.pluralise_r(loc)

                    if loc == "global" and rbt == "Interaction":
                        continue

                    df = pd.read_excel(filename, sheet_name=loc, index_col=0)

                    if loc not in self.location_cum_pop[rbt].keys():
                        self.location_cum_pop[rbt][loc] = df
                    else:
                        self.location_cum_pop[rbt][loc] += df

            Save_dir = self.merged_data_path / "Venue_TotalDemographics"
            Save_dir.mkdir(exist_ok=True, parents=True)
            with pd.ExcelWriter(
                Save_dir / f"CumPersonCounts_{rbt}.xlsx", mode="w"
            ) as writer:
                for local in self.location_cum_pop[rbt].keys():
                    df = pd.DataFrame(self.location_cum_pop[rbt][local])
                    df.to_excel(writer, sheet_name=f"{local}")
        return 1

    def VenueUniquePops(self):
        np.random.seed(1234)
        location_counters = {}
        for sex in self.contact_sexes:
            location_counters[sex] = {}
            for plural_loc in self.group_type_names["all"]:
                if plural_loc in ["global", "care_home_visits", "household_visits"]:
                    continue
                loc = self.pluralise_r(plural_loc)
                NVenues_so_far = 0
                for rank in range(0, self.NRanks):

                    if plural_loc not in self.group_type_names[rank]:
                        continue

                    filename = (
                        self.raw_data_path
                        / "Venue_UniquePops"
                        / f"Venues_{sex}_Counts_ByDate_r{rank}_.xlsx"
                    )

                    df = pd.read_excel(filename, sheet_name=plural_loc, index_col=0)

                    NVenues_rank_loc = df.shape[1] - 1
                    if NVenues_rank_loc == 0:
                        # No venues available
                        location_counters[sex][plural_loc] = pd.DataFrame(
                            {"t": df["t"]}
                        )
                        continue
                    Pick = int(600 / self.NRanks)
                    if NVenues_rank_loc > Pick:
                        pass
                    else:
                        Pick = NVenues_rank_loc

                    rands = np.random.choice(
                        np.arange(1, NVenues_rank_loc + 1, 1), size=Pick, replace=False
                    )
                    if plural_loc not in location_counters[sex].keys():
                        location_counters[sex][plural_loc] = pd.DataFrame(
                            {"t": df["t"]}
                        )
                        location_counters[sex][plural_loc][
                            np.arange(NVenues_so_far, NVenues_so_far + Pick, 1)
                        ] = df.iloc[:, [0] + rands].values
                    else:
                        location_counters[sex][plural_loc][
                            np.arange(NVenues_so_far, NVenues_so_far + Pick, 1)
                        ] = df.iloc[:, rands].values

                    NVenues_so_far += Pick

            Save_dir = self.merged_data_path / "Venue_UniquePops"
            Save_dir.mkdir(exist_ok=True, parents=True)
            with pd.ExcelWriter(
                Save_dir / f"Venues_{sex}_Counts_ByDate.xlsx", mode="w"
            ) as writer:
                for local in location_counters[sex].keys():
                    df = pd.DataFrame(location_counters[sex][local])
                    df.to_excel(writer, sheet_name=f"{local}")

        np.random.seed(1234)
        location_counters = {}
        for sex in self.contact_sexes:
            location_counters[sex] = {}
            for plural_loc in self.group_type_names["all"]:
                if plural_loc in ["global", "care_home_visits", "household_visits"]:
                    continue
                loc = self.pluralise_r(plural_loc)

                NVenues_so_far = 0
                for rank in range(0, self.NRanks):

                    if plural_loc not in self.group_type_names[rank]:
                        continue

                    filename = (
                        self.raw_data_path
                        / "Venue_UniquePops"
                        / f"Venues_{sex}_Counts_BydT_r{rank}_.xlsx"
                    )

                    df = pd.read_excel(filename, sheet_name=plural_loc, index_col=0)

                    NVenues_rank_loc = df.shape[1] - 1
                    if NVenues_rank_loc == 0:
                        location_counters[sex][plural_loc] = pd.DataFrame(
                            {"t": df["t"]}
                        )
                        continue
                    Pick = int(600 / self.NRanks)
                    if NVenues_rank_loc > Pick:
                        pass
                    else:
                        Pick = NVenues_rank_loc

                    rands = np.random.choice(
                        np.arange(1, NVenues_rank_loc + 1, 1), size=Pick, replace=False
                    )
                    if plural_loc not in location_counters[sex].keys():
                        location_counters[sex][plural_loc] = pd.DataFrame(
                            {"t": df["t"], "dt": df["dt"]}
                        )
                        location_counters[sex][plural_loc][
                            np.arange(NVenues_so_far, NVenues_so_far + Pick, 1)
                        ] = df.iloc[:, [0] + rands]
                    else:
                        location_counters[sex][plural_loc][
                            np.arange(NVenues_so_far, NVenues_so_far + Pick, 1)
                        ] = df.iloc[:, rands].values

                    NVenues_so_far += Pick

            Save_dir = self.merged_data_path / "Venue_UniquePops"
            Save_dir.mkdir(exist_ok=True, parents=True)
            with pd.ExcelWriter(
                Save_dir / f"Venues_{sex}_Counts_BydT.xlsx", mode="w"
            ) as writer:
                for local in location_counters[sex].keys():
                    df = pd.DataFrame(location_counters[sex][local])
                    df.to_excel(writer, sheet_name=f"{local}")
        return 1

    def VenuePersonCounts(self):
        self.age_profiles = {}
        self.rank_age_profiles = {}
        for rbt in self.binTypes:
            if rbt == "Interaction":
                continue

            self.rank_age_profiles[rbt] = {}

            self.age_profiles[rbt] = {}
            for rank in range(0, self.NRanks):

                filename = (
                    self.raw_data_path
                    / "Venue_Demographics"
                    / f"PersonCounts_{rbt}_r{rank}_.xlsx"
                )
                for loc in self.group_type_names[rank]:
                    if loc in ["care_home_visits", "household_visits"]:

                        continue

                    loc = self.pluralise_r(loc)
                    if loc not in self.rank_age_profiles[rbt].keys():
                        self.rank_age_profiles[rbt][loc] = {}

                    df = pd.read_excel(filename, sheet_name=loc, index_col=0)

                    self.rank_age_profiles[rbt][loc][rank] = df.copy()["unisex"].iloc[
                        :-1
                    ]
                    if "all" not in self.rank_age_profiles[rbt][loc].keys():
                        self.rank_age_profiles[rbt][loc]["all"] = df["unisex"].iloc[:-1]
                    else:
                        self.rank_age_profiles[rbt][loc]["all"] += (
                            df["unisex"].iloc[:-1].values
                        )

                    if loc not in self.age_profiles[rbt].keys():
                        self.age_profiles[rbt][loc] = df
                    else:
                        self.age_profiles[rbt][loc] += df.values

            Save_dir = self.merged_data_path / "Venue_Demographics"
            Save_dir.mkdir(exist_ok=True, parents=True)
            with pd.ExcelWriter(
                Save_dir / f"PersonCounts_{rbt}.xlsx", mode="w"
            ) as writer:
                for local in self.age_profiles[rbt].keys():
                    df = pd.DataFrame(self.age_profiles[rbt][local])
                    df.to_excel(writer, sheet_name=f"{local}")

        # Remove the total row.
        for rbt in self.age_profiles.keys():
            for loc in self.age_profiles[rbt].keys():
                self.age_profiles[rbt][loc] = self.age_profiles[rbt][loc].iloc[:-1, :]
        return 1

    def AvContacts(self):
        AvContacts = {}
        for rbt in self.binTypes:
            if rbt == "Interaction":
                continue
            for rank in range(0, self.NRanks):
                filename = (
                    self.raw_data_path
                    / "Venue_AvContacts"
                    / f"Average_contacts_r{rank}_.xlsx"
                )
                df = pd.read_excel(filename, sheet_name=rbt, index_col=0)

                if rank == 0:
                    dat = {df.columns[0]: df.iloc[0]}
                    nbins = len(self.rank_age_profiles[rbt]["global"]["all"])
                    for col in self.group_type_names["all"]:
                        col = self.pluralise_r(col)
                        if "visit" in col:
                            col += "s"
                        dat[col] = np.zeros(nbins)

                    AvContacts[rbt] = pd.DataFrame(dat)

                for col in df.columns:
                    if self.pluralise(col) not in self.group_type_names[rank]:
                        continue
                    col_age = self.pluralise_r(col)
                    if col_age == "care_home_visit":
                        col_age = "care_home"
                    if col_age == "household_visit":
                        col_age = "household"

                    # factor = (self.rank_age_profiles[rbt][col_age][rank].values/self.rank_age_profiles[rbt][col_age]["all"].values)
                    factor = (
                        self.rank_age_profiles[rbt]["global"][rank].values
                        / self.rank_age_profiles[rbt]["global"]["all"].values
                    )
                    AvContacts[rbt][col] += (df[col] * factor).values

        Save_dir = self.merged_data_path / "Venue_AvContacts"
        Save_dir.mkdir(exist_ok=True, parents=True)
        with pd.ExcelWriter(Save_dir / f"Average_contacts.xlsx", mode="w") as writer:
            for rbt in self.binTypes:
                if rbt == "Interaction":
                    continue
                df = pd.DataFrame(AvContacts[rbt]).replace(np.nan, 0)

                df.to_excel(writer, sheet_name=f"{rbt}")
        return 1

    def LoadIMatrices(self):
        with open(self.merged_data_path / "CM_yamls" / f"tracker_IM.yaml") as f:
            self.IM = yaml.load(f, Loader=yaml.FullLoader)
        return 1

    def LoadContactMatrices(self):
        self.age_bins = {}

        for rank in range(0, self.NRanks):
            with open(
                self.raw_data_path / "CM_yamls" / f"tracker_CM_r{rank}_.yaml"
            ) as f:
                self.CM_rank = yaml.load(f, Loader=yaml.FullLoader)

            if rank == 0:
                # Create copies of the contact_matrices to be filled in.
                # Error Matrix
                self.CM = {
                    bin_type: {
                        loc: {
                            sex: np.array(
                                self.CM_rank[bin_type][loc]["sex"][sex]["contacts"]
                            )
                            * self.timer.total_days
                            for sex in self.CM_rank[bin_type][loc]["sex"].keys()
                        }
                        for loc in self.CM_rank[bin_type].keys()
                    }
                    for bin_type in self.CM_rank.keys()
                    if bin_type != "Interaction"
                }
                self.CM["Interaction"] = {
                    loc: np.array(self.CM_rank["Interaction"][loc]["contacts"])
                    * self.timer.total_days
                    for loc in self.CM_rank["Interaction"].keys()
                }

                for rbt in self.binTypes:
                    if rbt == "Interaction" or rbt in self.age_bins.keys():
                        continue
                    loc = list(self.CM_rank[rbt].keys())[0]
                    self.age_bins[rbt] = self.CM_rank[rbt][loc]["bins"]

            else:
                for bin_type in self.binTypes:
                    for loc_plural in self.group_type_names["all"]:
                        loc = self.pluralise_r(loc_plural)
                        NEW = False
                        if loc_plural not in self.group_type_names[rank]:
                            continue
                        if loc_plural in ["care_home_visits", "household_visits"]:
                            continue

                        if loc not in self.CM[bin_type].keys():
                            NEW = True

                        if bin_type != "Interaction":
                            if NEW:
                                self.CM[bin_type][loc] = {}

                            for sex in self.contact_sexes:
                                if NEW:
                                    self.CM[bin_type][loc][sex] = (
                                        np.array(
                                            self.CM_rank[bin_type][loc]["sex"][sex][
                                                "contacts"
                                            ]
                                        )
                                        * self.timer.total_days
                                    )
                                else:
                                    self.CM[bin_type][loc][sex] += (
                                        np.array(
                                            self.CM_rank[bin_type][loc]["sex"][sex][
                                                "contacts"
                                            ]
                                        )
                                        * self.timer.total_days
                                    )

                        else:
                            if loc in [
                                "global",
                                "care_home_visits",
                                "household_visits",
                            ]:
                                continue
                            if NEW:
                                self.CM[bin_type][loc] = (
                                    np.array(self.CM_rank[bin_type][loc]["contacts"])
                                    * self.timer.total_days
                                )
                            else:
                                self.CM[bin_type][loc] += (
                                    np.array(self.CM_rank[bin_type][loc]["contacts"])
                                    * self.timer.total_days
                                )
        logger.info(f"Rank {mpi_rank} -- Load CMs Done")

        for rank in range(0, self.NRanks):
            with open(
                self.raw_data_path / "CM_yamls" / f"tracker_CMV_r{rank}_.yaml"
            ) as f:
                self.CMV_rank = yaml.load(f, Loader=yaml.FullLoader)
                # [bin_type][contact_type]["sex"][sex]["contacts"]

            if rank == 0:
                # Create copies of the contact_matrices to be filled in.
                # Error Matrix
                self.CMV = {
                    bin_type: {
                        loc: {
                            sex: np.array(
                                self.CMV_rank[bin_type][loc]["sex"][sex]["contacts"]
                            )
                            * self.timer.total_days
                            for sex in self.CMV_rank[bin_type][loc]["sex"].keys()
                        }
                        for loc in self.CMV_rank[bin_type].keys()
                    }
                    for bin_type in self.CMV_rank.keys()
                    if bin_type != "Interaction"
                }
                self.CMV["Interaction"] = {
                    loc: np.array(self.CMV_rank["Interaction"][loc]["contacts"])
                    * self.timer.total_days
                    for loc in self.CMV_rank["Interaction"].keys()
                }

                for rbt in self.binTypes:
                    if rbt == "Interaction" or rbt in self.age_bins.keys():
                        continue
                    loc = list(self.CMV_rank[rbt].keys())[0]
                    self.age_bins[rbt] = self.CMV_rank[rbt][loc]["bins"]

            else:
                for bin_type in self.binTypes:
                    for loc_plural in self.group_type_names["all"]:
                        loc = self.pluralise_r(loc_plural)
                        NEW = False
                        if loc_plural not in self.group_type_names[rank]:
                            continue
                        if loc_plural in [
                            "global",
                            "care_home_visits",
                            "household_visits",
                        ]:
                            continue

                        if loc not in self.CMV[bin_type].keys():
                            NEW = True

                        if bin_type != "Interaction":
                            if NEW:
                                self.CMV[bin_type][loc] = {}

                            for sex in self.contact_sexes:
                                if NEW:
                                    self.CMV[bin_type][loc][sex] = (
                                        np.array(
                                            self.CMV_rank[bin_type][loc]["sex"][sex][
                                                "contacts"
                                            ]
                                        )
                                        * self.timer.total_days
                                    )
                                else:
                                    self.CMV[bin_type][loc][sex] += (
                                        np.array(
                                            self.CMV_rank[bin_type][loc]["sex"][sex][
                                                "contacts"
                                            ]
                                        )
                                        * self.timer.total_days
                                    )

                        else:
                            if loc in [
                                "global",
                                "care_home_visits",
                                "household_visits",
                            ]:
                                continue
                            if NEW:
                                self.CMV[bin_type][loc] = (
                                    np.array(self.CMV_rank[bin_type][loc]["contacts"])
                                    * self.timer.total_days
                                )
                            else:
                                self.CMV[bin_type][loc] += (
                                    np.array(self.CMV_rank[bin_type][loc]["contacts"])
                                    * self.timer.total_days
                                )

        logger.info(f"Rank {mpi_rank} -- Load CMVs Done")
        return 1

    def LoadCumtimes(self):
        self.location_cum_time = {}
        for rank in range(0, self.NRanks):
            filename = self.raw_data_path / "Venue_CumTime" / f"CumTime_r{rank}_.xlsx"

            df = pd.read_excel(filename, index_col=0)

            for plural_col in self.group_type_names["all"]:
                if plural_col in ["care_home_visits", "household_visits"]:
                    continue
                col = self.pluralise_r(plural_col)
                if col not in df.columns:
                    continue

                if col not in self.location_cum_time.keys():
                    self.location_cum_time[col] = df[col].values[0]
                else:
                    self.location_cum_time[col] += df[col].values[0]

        Save_dir = self.merged_data_path / "Venue_CumTime"
        Save_dir.mkdir(exist_ok=True, parents=True)
        df = pd.DataFrame.from_dict(self.location_cum_time, orient="index").T
        with pd.ExcelWriter(Save_dir / f"CumTime.xlsx", mode="w") as writer:
            df.to_excel(writer)
        return 1

    def SaveOutCM(self):
        folder_name = self.merged_data_path
        mpi_rankname = ""
        
        def SaveMatrix(CM, CM_err, Mtype, NormType="U"):
            jsonfile = {}
            for binType in list(CM.keys()):

                if NormType == "U":
                    pass
                elif NormType == "P":
                    Mtype = "P"+Mtype[1:]

                jsonfile[binType] = self.tracker_CMJSON(
                    binType=binType, CM=CM, CM_err=CM_err, NormType=NormType,
                )
            # Save out the Normalised UNCM
            self.Save_CM_JSON(
                dir=self.record_path / "Tracker" / folder_name / "CM_yamls",
                folder=folder_name,
                filename=f"tracker_{Mtype}{mpi_rankname}.yaml",
                jsonfile=jsonfile,
            )

        def SaveMatrixMetrics(CM, CM_err, Mtype, NormType="U"):
            # Save out metric calculations
            jsonfile = {}
            for binType in list(CM.keys()):
                jsonfile[binType] = {}
                for loc in list(CM[binType].keys()):

                    if NormType == "U":
                        ratio = 1
                    elif NormType == "P":
                        ratio = self.AttendenceRatio(binType, loc, "unisex")
                        Mtype = "P"+Mtype[1:]

                    jsonfile[binType][loc] = self.Calculate_CM_Metrics(
                        bin_type=binType,
                        contact_type=loc,
                        CM=CM,
                        CM_err=CM_err,
                        ratio = ratio,
                        sex = "unisex"
                    )
            self.Save_CM_JSON(
                dir=self.record_path / "Tracker" / folder_name / "CM_Metrics",
                folder=folder_name,
                filename=f"tracker_Metrics_{Mtype}{mpi_rankname}.yaml",
                jsonfile=jsonfile,
            )

        def SaveMatrixCamberra(CM, CM_err, Mtype, NormType="U"):
            jsonfile = {}
            for loc in list(CM["Interaction"].keys()):

                if NormType == "U":
                    ratio = 1
                elif NormType == "P":
                    ratio = self.AttendenceRatio("Interaction", loc, "unisex")
                    Mtype = "P"+Mtype[1:]

                cm = CM["Interaction"][loc]
                cm = self.UNtoPNConversion(cm, ratio)
      
                A = np.array(cm, dtype=float)
                B = np.array(self.IM[loc]["contacts"], dtype=float)
                Dc = self.Canberra_distance(A, B)[0]
                jsonfile[loc] = {"Dc": f"{Dc}"}
            self.Save_CM_JSON(
                dir=self.record_path / "Tracker" / folder_name / "CM_Metrics",
                folder=folder_name,
                filename=f"tracker_CamberraDist_{Mtype}{mpi_rankname}.yaml",
                jsonfile=jsonfile,
            )

        # Saving Contacts tracker results ##################################
        SaveMatrix(CM=self.CM, CM_err=self.CM, Mtype = "CM")
        SaveMatrix(CM=self.CMV, CM_err=self.CMV_err, Mtype = "CMV")

        SaveMatrix(CM=self.UNCM, CM_err=self.UNCM_err, Mtype = "UNCM")
        SaveMatrix(CM=self.UNCM_R, CM_err=self.UNCM_R_err, Mtype = "UNCM_R")
        SaveMatrix(CM=self.UNCM_V, CM_err=self.UNCM_V_err, Mtype = "UNCM_V")

        SaveMatrix(CM=self.UNCM, CM_err=self.UNCM_err, Mtype = "UNCM",NormType="P")
        SaveMatrix(CM=self.UNCM_R, CM_err=self.UNCM_R_err, Mtype = "UNCM_R",NormType="P")
        SaveMatrix(CM=self.UNCM_V, CM_err=self.UNCM_V_err, Mtype = "UNCM_V",NormType="P")

        SaveMatrixMetrics(CM=self.UNCM, CM_err=self.UNCM_err, Mtype = "UNCM")
        SaveMatrixMetrics(CM=self.UNCM_R, CM_err=self.UNCM_R_err, Mtype = "UNCM_R")
        SaveMatrixMetrics(CM=self.UNCM_V, CM_err=self.UNCM_V_err, Mtype = "UNCM_V")

        SaveMatrixMetrics(CM=self.UNCM, CM_err=self.UNCM_err, Mtype = "UNCM",NormType="P")
        SaveMatrixMetrics(CM=self.UNCM_R, CM_err=self.UNCM_R_err, Mtype = "UNCM_R",NormType="P")
        SaveMatrixMetrics(CM=self.UNCM_V, CM_err=self.UNCM_V_err, Mtype = "UNCM_V",NormType="P")

        SaveMatrixCamberra(CM=self.UNCM, CM_err=self.UNCM_err, Mtype = "UNCM")
        SaveMatrixCamberra(CM=self.UNCM_R, CM_err=self.UNCM_R_err, Mtype = "UNCM_R")
        SaveMatrixCamberra(CM=self.UNCM_V, CM_err=self.UNCM_V_err, Mtype = "UNCM_V")

        SaveMatrixCamberra(CM=self.UNCM, CM_err=self.UNCM_err, Mtype = "UNCM",NormType="P")
        SaveMatrixCamberra(CM=self.UNCM_R, CM_err=self.UNCM_R_err, Mtype = "UNCM_R",NormType="P")
        SaveMatrixCamberra(CM=self.UNCM_V, CM_err=self.UNCM_V_err, Mtype = "UNCM_V",NormType="P")
        return 1

    #################################################
    # Master Merge ##################################
    #################################################

    def Merge(self):
        logger.info(f"Rank {mpi_rank} -- Begin Merging from {self.NRanks+1} ranks")
        if self.MPI:
            self.Travel_Distance()
            logger.info(f"Rank {mpi_rank} -- Distance sheet done")

            self.LoadCumtimes()
            logger.info(f"Rank {mpi_rank} -- Cumulative time done")
            self.CumPersonCounts()
            logger.info(f"Rank {mpi_rank} -- Person counts done")
            self.VenueUniquePops()
            logger.info(f"Rank {mpi_rank} -- Unique Venue pops done")
            self.VenuePersonCounts()
            logger.info(f"Rank {mpi_rank} -- Total Venue pops done")
            self.AvContacts()
            logger.info(f"Rank {mpi_rank} -- Average contacts done")

            self.LoadIMatrices()
            self.LoadContactMatrices()
            logger.info(f"Rank {mpi_rank} -- Load IM and CMs done")

            self.initalize_CM_Normalisations()
            self.normalise_1D_CM()

            self.initalize_CM_All_Normalisations()
            self.normalise_All_CM()

            logger.info(f"Rank {mpi_rank} -- Normalised CMs done")

            self.SaveOutCM()
            logger.info(f"Rank {mpi_rank} -- Saved CM done")

        else:
            logger.info(f"Rank {mpi_rank} -- Skip run was on 1 core")
        logger.info(f"Rank {mpi_rank} -- Merging done")
        self.PrintOutResults()
