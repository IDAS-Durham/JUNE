from operator import index
import numpy as np
import yaml
import pandas as pd
from pathlib import Path
import glob

from june.tracker.tracker import Tracker

################################################################################################################################################################
                            ################################### Plotting functions ##################################
#####################################################################################################################################################################

class MergerClass:
    """
    Class to plot everything tracker related

    Parameters
    ----------

    Returns
    -------
    """
    def __init__(
        self,        
        record_path=Path("")
    ):

        self.record_path = record_path

        if (self.record_path / "Tracker" / "raw_data_output").exists():
            self.MPI = True
        else:
            self.MPI = False
            
            
        if self.MPI == False:
            pass
        else:
            self.raw_data_path = self.record_path / "Tracker" / "raw_data_output"
            self.merged_data_path = self.record_path / "Tracker" / "merged_data_output"
            self.merged_data_path.mkdir(exist_ok=True, parents=True)

            self.NRanks = len(glob.glob(str(self.raw_data_path / "*.yaml")))
            
            with open(self.raw_data_path / "tracker_Simulation_Params_r0_.yaml") as f:
                Params = yaml.load(f, Loader=yaml.FullLoader)
                
            self.group_type_names = {} 
            self.group_type_names[0] = list(Params["NVenues"].keys()) + ["care_home_visits", "household_visits", "global"]
            self.group_type_names["all"] = list(Params["NVenues"].keys())
            self.binTypes = list(Params["binTypes"])
            self.contact_sexes = list(Params["sexes"])
            
            Params["MPI_rank"] = "Combined"
            Params["Weekday_Names"] = self.MatrixString(matrix=np.array(Params["Weekday_Names"]))
            Params["Weekend_Names"] = self.MatrixString(matrix=np.array(Params["Weekend_Names"]))
            Params["binTypes"] = self.MatrixString(matrix=np.array(Params["binTypes"]))

        
            for rank in range(1,self.NRanks):
                with open(self.raw_data_path / f"tracker_Simulation_Params_r{rank}_.yaml") as f:
                    Params_rank = yaml.load(f, Loader=yaml.FullLoader)

                
                self.group_type_names[rank] = list(Params_rank["NVenues"].keys()) + ["care_home_visits", "household_visits", "global"]

                group_names_update = list( set(self.group_type_names["all"] + self.group_type_names[rank]) )
                self.group_type_names["all"] = group_names_update

                venues = list(set(Params_rank["NVenues"].keys()) & set(self.group_type_names[rank]))

                for v in venues:
                    if v in Params["NVenues"].keys() and v in Params_rank["NVenues"].keys():
                        Params["NVenues"][v] += Params_rank["NVenues"][v]
                    elif v not in Params["NVenues"].keys() and v in Params_rank["NVenues"].keys():
                        Params["NVenues"][v] = Params_rank["NVenues"][v]
                    else:
                        continue
                        
                Params["NPeople"] += Params_rank["NPeople"]  
            Tracker.Save_CM_JSON(
                self,
                dir=self.merged_data_path, 
                folder="",
                filename="tracker_Simulation_Params.yaml", 
                jsonfile=Params
            )

        print(self.group_type_names["all"])

            
#####################################################################################################################################################################
                                ################################### Individual Merge ##################################
#####################################################################################################################################################################
 
    def Travel_Distance(self):
        travel_distance = {}
        for rank in range(0,self.NRanks):
            filename = self.raw_data_path / "Venue_TravelDist" / f"Distance_traveled_r{rank}_.xlsx"
            for loc in self.group_type_names[rank]:
                if loc in ["global", "shelter_inter", "shelter_intra", "care_home_visits", "household_visits"]:
                    continue
                df = pd.read_excel(
                    filename,
                    sheet_name=loc,
                    index_col=0,
                )                
                if loc not in travel_distance.keys():
                    travel_distance[loc] = df
                else:
                    travel_distance[loc].iloc[:, 1:] += df.iloc[:,1:]   
        Save_dir = self.merged_data_path / "Venue_TravelDist"
        Save_dir.mkdir(exist_ok=True, parents=True)
        with pd.ExcelWriter(Save_dir / f'Distance_traveled.xlsx', mode="w") as writer:  
            for local in travel_distance.keys(): 
                travel_distance[local].to_excel(writer, sheet_name=f'{local}')
        return 1

    def CumPersonCounts(self):
        self.location_cum_pop = {}
        for rbt in self.binTypes:
            self.location_cum_pop[rbt] = {}
            for rank in range(0, self.NRanks):
                filename = self.raw_data_path / "Venue_TotalDemographics" / f"CumPersonCounts_{rbt}_r{rank}_.xlsx"
                for loc in self.group_type_names[rank]: 
                    if loc in ["care_home_visits", "household_visits"]:
                        continue
                   
                    loc = self.pluralise_r(loc)

                    if loc == "global" and rbt == "Interaction":
                        continue

                    df = pd.read_excel(
                        filename,
                        sheet_name=loc,
                        index_col=0,
                    )    

                    if loc not in self.location_cum_pop[rbt].keys():
                        self.location_cum_pop[rbt][loc] = df
                    else:
                        self.location_cum_pop[rbt][loc] += df

            Save_dir = self.merged_data_path / "Venue_TotalDemographics"
            Save_dir.mkdir(exist_ok=True, parents=True)
            with pd.ExcelWriter(Save_dir / f'CumPersonCounts_{rbt}.xlsx', mode="w") as writer:  
                for local in self.location_cum_pop[rbt].keys(): 
                    df = pd.DataFrame(self.location_cum_pop[rbt][local])
                    df.to_excel(writer, sheet_name=f'{local}')
        return 1

    def VenueUniquePops(self):
        location_counters = {}
        for sex in self.contact_sexes:
            location_counters[sex] = {}
            for plural_loc in self.group_type_names["all"]: 
                if plural_loc in ["global","care_home_visits", "household_visits"]:
                    continue
                loc = self.pluralise_r(plural_loc)
                NVenues_so_far = 0
                for rank in range(0, self.NRanks):

                    if plural_loc not in self.group_type_names[rank]:
                        continue

                    filename = self.raw_data_path / "Venue_UniquePops" / f"Venues_{sex}_Counts_ByDate_r{rank}_.xlsx"
            
                    df = pd.read_excel(
                        filename,
                        sheet_name=plural_loc,
                        index_col=0,
                    ) 

                    NVenues_rank_loc = df.shape[1]-1
                    if NVenues_rank_loc == 0: 
                        #No venues available
                        continue
                    Pick = int(600 / self.NRanks)
                    if NVenues_rank_loc > Pick:
                        pass
                    else:
                        Pick = NVenues_rank_loc

                    rands = np.random.choice(np.arange(1,NVenues_rank_loc+1,1), size=Pick, replace=False)
                    if plural_loc not in location_counters[sex].keys():
                        location_counters[sex][plural_loc] = pd.DataFrame({"t":df["t"]})
                        location_counters[sex][plural_loc][np.arange(NVenues_so_far, NVenues_so_far+Pick, 1)] = df.iloc[:,[0] + rands].values
                    else:
                        location_counters[sex][plural_loc][np.arange(NVenues_so_far, NVenues_so_far+Pick, 1)] = df.iloc[:, rands].values

                    NVenues_so_far += Pick

            Save_dir = self.merged_data_path / "Venue_UniquePops"
            Save_dir.mkdir(exist_ok=True, parents=True)
            with pd.ExcelWriter(Save_dir / f"Venues_{sex}_Counts_ByDate.xlsx", mode="w") as writer:  
                for local in location_counters[sex].keys(): 
                    df = pd.DataFrame(location_counters[sex][local])
                    df.to_excel(writer, sheet_name=f'{local}')
                
        location_counters = {}
        for sex in self.contact_sexes:
            location_counters[sex] = {}
            for plural_loc in self.group_type_names["all"]: 
                if plural_loc in ["global","care_home_visits", "household_visits"]:
                    continue
                loc = self.pluralise_r(plural_loc)
                
                NVenues_so_far = 0
                for rank in range(0, self.NRanks):

                    if plural_loc not in self.group_type_names[rank]:
                        continue

                    filename = self.raw_data_path / "Venue_UniquePops" / f"Venues_{sex}_Counts_BydT_r{rank}_.xlsx"
            
                    df = pd.read_excel(
                        filename,
                        sheet_name=plural_loc,
                        index_col=0,
                    ) 

                    NVenues_rank_loc = df.shape[1]-1
                    if NVenues_rank_loc == 0: 
                        #No venues available
                        continue
                    Pick = int(600 / self.NRanks)
                    if NVenues_rank_loc > Pick:
                        pass
                    else:
                        Pick = NVenues_rank_loc

                    rands = np.random.choice(np.arange(1,NVenues_rank_loc+1,1), size=Pick, replace=False)
                    if plural_loc not in location_counters[sex].keys():
                        location_counters[sex][plural_loc] = pd.DataFrame({"t":df["t"], "dt":df["dt"]})
                        location_counters[sex][plural_loc][np.arange(NVenues_so_far, NVenues_so_far+Pick, 1)] = df.iloc[:,[0] + rands]
                    else:
                        location_counters[sex][plural_loc][np.arange(NVenues_so_far, NVenues_so_far+Pick, 1)] = df.iloc[:, rands].values

                    NVenues_so_far += Pick

            Save_dir = self.merged_data_path / "Venue_UniquePops"
            Save_dir.mkdir(exist_ok=True, parents=True)
            with pd.ExcelWriter(Save_dir / f"Venues_{sex}_Counts_BydT.xlsx", mode="w") as writer:  
                for local in location_counters[sex].keys(): 
                    df = pd.DataFrame(location_counters[sex][local])
                    df.to_excel(writer, sheet_name=f'{local}')
        return 1


    
    def VenuePersonCounts(self):
        age_profiles = {}
        self.rank_age_profiles = {}
        for rbt in self.binTypes:
            if rbt == "Interaction":
                continue

            self.rank_age_profiles[rbt] = {}

            age_profiles[rbt] = {}
            for rank in range(0, self.NRanks):
                
                filename = self.raw_data_path / "Venue_Demographics" / f"PersonCounts_{rbt}_r{rank}_.xlsx"
                for loc in self.group_type_names[rank]: 
                    if loc in ["care_home_visits", "household_visits"]:
                        continue


                    
                    loc = self.pluralise_r(loc)
                    df = pd.read_excel(
                        filename,
                        sheet_name=loc,
                        index_col=0,
                    )    

                    if loc == "global":
                        self.rank_age_profiles[rbt][rank] = df.copy()["unisex"].iloc[:-1]
                        if "all" not in self.rank_age_profiles[rbt].keys():
                            self.rank_age_profiles[rbt]["all"] = df["unisex"].iloc[:-1]
                        else:
                            self.rank_age_profiles[rbt]["all"] += df["unisex"].iloc[:-1].values

                    if loc not in age_profiles[rbt].keys():
                        age_profiles[rbt][loc] = df
                    else:
                        age_profiles[rbt][loc] += df.values

                   

            Save_dir = self.merged_data_path / "Venue_Demographics"
            Save_dir.mkdir(exist_ok=True, parents=True)
            with pd.ExcelWriter(Save_dir / f'PersonCounts_{rbt}.xlsx', mode="w") as writer:  
                for local in age_profiles[rbt].keys(): 
                    df = pd.DataFrame(age_profiles[rbt][local])
                    df.to_excel(writer, sheet_name=f'{local}')
        return 1

    def AvContacts(self):
        AvContacts = {}
        for rbt in self.binTypes:
            if rbt == "Interaction":
                continue
            for rank in range(0, self.NRanks):
                filename = self.raw_data_path / "Venue_AvContacts" / f'Average_contacts_r{rank}_.xlsx'
                df = pd.read_excel(
                    filename,
                    sheet_name=rbt,
                    index_col=0,
                )   

                if rank == 0:
                    dat = {df.columns[0] : df.iloc[0]}
                    nbins = len(self.rank_age_profiles[rbt]["all"])
                    for col in self.group_type_names["all"]:
                        col = self.pluralise_r(col) 
                        if "visit" in col:
                            col += "s"
                        dat[col] = np.zeros(nbins)
                
                    AvContacts[rbt] = pd.DataFrame(dat)

                
                factor = (self.rank_age_profiles[rbt][rank].values/self.rank_age_profiles[rbt]["all"].values)
                for col in df.columns:
                    AvContacts[rbt][col] += (df[col] * factor).values
                


        Save_dir = self.merged_data_path / "Venue_AvContacts"
        Save_dir.mkdir(exist_ok=True, parents=True)
        with pd.ExcelWriter(Save_dir / f'Average_contacts.xlsx', mode="w") as writer:  
            for rbt in self.binTypes:
                if rbt == "Interaction":
                    continue
                df = pd.DataFrame(AvContacts[rbt])
                df.to_excel(writer, sheet_name=f'{rbt}')
        return 1

    def LoadIMatrices(self):
        with open(self.merged_data_path / "CM_yamls" / f"tracker_IM.yaml") as f:
            self.IM = yaml.load(f, Loader=yaml.FullLoader)
        return 1



    def LoadContactMatrices(self):
        self.Tracker_Contact_Type = "1D"

        for rank in range(0, 2):#self.NRanks):
            with open(self.raw_data_path / "CM_yamls" / f"tracker_{self.Tracker_Contact_Type}_Total_CM_r{rank}_.yaml") as f:
                self.CM_T_rank = yaml.load(f, Loader=yaml.FullLoader)
                #[bin_type][contact_type]["sex"][sex]["contacts"]

            if rank == 0:
                #Create copies of the contact_matrices to be filled in.
                #Error Matrix
                self.CM_T = { 
                    bin_type : { 
                        loc: {
                            sex : self.CM_T_rank[bin_type][loc]["sex"][sex]["contacts"]
                            for sex in self.CM_T_rank[bin_type][loc]["sex"].keys() 
                            }
                        for loc in self.CM_T_rank[bin_type].keys()
                        }
                    for bin_type in self.CM_T_rank.keys() if bin_type != "Interaction" 
                }
                self.CM_T["Interaction"] = { 
                        loc: self.CM_T_rank["Interaction"][loc]["contacts"] for loc in self.CM_T_rank["Interaction"].keys()
                }

      

            else:
                for bin_type in self.binTypes:
                    for loc_plural in self.group_type_names["all"]:
                        loc = self.pluralise_r(loc_plural)
                        NEW = False
                        if loc_plural not in self.group_type_names[rank]:
                            continue
                        if loc_plural in ["global","care_home_visits", "household_visits"]:
                            continue

                        if loc not in self.CM_T[bin_type].keys():
                            NEW = True

                        if bin_type != "Interaction":
                            if NEW:
                                self.CM_T[bin_type][loc] = {}

                            for sex in self.contact_sexes:
                                if NEW:
                                    self.CM_T[bin_type][loc][sex] = np.array(self.CM_T_rank[bin_type][loc]["sex"][sex]["contacts"])
                                else:
                                    self.CM_T[bin_type][loc][sex] += np.array(self.CM_T_rank[bin_type][loc]["sex"][sex]["contacts"])

                        else:
                            if loc in ["global","care_home_visits", "household_visits"]:
                                continue
                            if NEW:
                                self.CM_T[bin_type][loc] = np.array(self.CM_T_rank[bin_type][loc]["contacts"])
                            else:
                                self.CM_T[bin_type][loc] += np.array(self.CM_T_rank[bin_type][loc]["contacts"])
            print(rank, "done")

        Tracker.initalize_CM_Normalisations(self)
        print(self.CM_T.keys())
        return 1



                       
            
#####################################################################################################################################################################
                                ################################### Master Merge ##################################
#####################################################################################################################################################################
 
    def CM_Norm(self, cm, pop_tots, contact_type="global", Reciprocal=True):
        return Tracker.CM_Norm(self, cm, pop_tots, contact_type, Reciprocal)

    def Get_characteristic_time(self,location):
        return Tracker.Get_characteristic_time(self,location)

    def PolicyText(self, Type, contacts, contacts_err, proportional_physical, characteristic_time):
        return Tracker.PolicyText(self, Type, contacts, contacts_err, proportional_physical, characteristic_time)

    def MatrixString(self, matrix, dtypeString="float"):
        return Tracker.MatrixString(self, matrix, dtypeString)

    def pluralise_r(self, loc):
        return Tracker.pluralise_r(self, loc)

    def pluralise(self, loc):
        return Tracker.pluralise(self, loc)

    def Merge(self):
        if self.MPI == True:        
            #self.Travel_Distance()

            self.CumPersonCounts()
            self.LoadIMatrices()
            self.LoadContactMatrices()

            

            if "1D" in self.Tracker_Contact_Type:
                Tracker.initalize_CM_Normalisations(self)
                Tracker.normalise_1D_CM(self)

            if "All" in self.Tracker_Contact_Type:
                Tracker.initalize_CM_All_Normalisations(self)
                Tracker.normalise_All_CM(self)
            Tracker.PrintOutResults(self)

            #self.VenueUniquePops()
            #self.VenuePersonCounts()
            #self.AvContacts()
            pass
        else:
            print("Run was on one core")
