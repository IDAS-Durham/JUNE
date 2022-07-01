from dataclasses import replace
from re import I
import numpy as np
from june.mpi_setup import mpi_comm, mpi_size, mpi_rank
import logging

import yaml
import pandas as pd

from pathlib import Path
from june import paths

from june.world import World
import geopy.distance

from june.groups.group import make_subgroups

AgeAdult = make_subgroups.Subgroup_Params.AgeYoungAdult
ACArray = np.array([0,AgeAdult,100])
DaysOfWeek_Names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

default_interaction_path = (
    paths.configs_path / "defaults/interaction/interaction.yaml"
)

logger = logging.getLogger("tracker")
mpi_logger = logging.getLogger("mpi")

if mpi_rank > 0:
    logger.propagate = False

class Tracker:
    """
    Class to handle the contact tracker.

    Parameters
    ----------
    world:
        instance of World class
    age_bins:
        dictionary mapping of bin stucture and array of bin edges
    contact_sexes:
        list of sexes for which to create contact matix. "male", "female" and or "unisex" (for both together)
    group_types:
        list of world.locations for tracker to loop over 
    record_path:
        path for results directory
    load_interactions_path:
        path for interactions yaml directory
    Tracker_Contact_Type:
        List of type of contact tracking to be implemented ["1D", "All"].

    Returns
    -------
        A Tracker

    """
    def __init__(
        self,        
        world: World,
        age_bins = {"syoa": np.arange(0,101,1)},
        contact_sexes = ["unisex"],
        group_types=None,
        record_path=Path(""),
        load_interactions_path=default_interaction_path,
        Tracker_Contact_Type = ["1D"],
        MaxVenueTrackingSize = np.inf
    ):
        self.world = world
        self.age_bins = age_bins
        self.contact_sexes = contact_sexes
        self.group_types = group_types
        self.timer = None
        self.record_path = record_path
        self.load_interactions_path = load_interactions_path

        #TODO Add check to make sure only contains "1D" or "All"
        self.Tracker_Contact_Type = Tracker_Contact_Type

        self.MaxVenueTrackingSize = MaxVenueTrackingSize

        #If we want to track total persons at each location
        self.initialise_group_names()

        #Maximum number of locations...
        locations = []
        for locs in self.group_type_names:
            if locs in ["global", "shelter_inter", "shelter_intra"]:
                continue

            locations.append(self.pluralise(locs))

        self.venues_which = {}
        for spec in locations:
            if len(getattr(self.world, spec).members) > MaxVenueTrackingSize:
                self.venues_which[spec] = np.random.choice(np.arange(0,len(getattr(self.world, spec).members),1), size=self.MaxVenueTrackingSize, replace=False)
            else:
                self.venues_which[spec] = np.arange(0,len(getattr(self.world, spec).members),1)
            

        self.intitalise_location_counters()

        self.load_interactions(self.load_interactions_path) #Load in premade contact matrices
        self.initialise_contact_matrices()

        # store all ages/ index to age bins in python dict for quick lookup.
        self.hash_ages() 

        #Initalize time, pop and contact counters
        self.intitalise_location_cum_time()
        self.intitalise_location_cum_pop()
        self.intitalise_contact_counters()
        
        self.travel_distance = {}

#####################################################################################################################################################################
                                ################################### Useful functions ##################################
#####################################################################################################################################################################
   
    @staticmethod
    def _random_round(x):
        """
        Round integer randomly up or down

        Parameters
        ----------
            x:
                A float
            
        Returns
        -------
            int

        """
        f = x % 1
        if np.random.uniform(0,1,1) < f:
            return int(x)+1
        else:
            return int(x)


    def intersection(self, list_A, list_B, permute=True):
        """
        Get shared elements in two lists

        Parameters
        ----------
            list_A:
                list of objects
            list_B:
                second list of objects
            permute: defualt = True
                bool, shuffle the returned list 
            
        Returns
        -------
            list of shared elements

        """
        Intersection = np.array(list(set(list_A) & set(list_B)))
        if permute:
            return list(Intersection[np.random.permutation(len(Intersection))])
        else:
            return list(Intersection)

    def union(self, list_A, list_B):
        """
        Get all unique elements in two lists

        Parameters
        ----------
            list_A:
                list of objects
            list_B:
                second list of objects

            
        Returns
        -------
            list of all unique elements

        """
        Union = sorted(list(set(list_A + list_B)))
        return Union

    def pluralise_r(self, loc):
        if loc == "global":
            return loc

        if loc[-3:] == "ies":
            loc = loc[:-3]+"y"
        elif loc[-1] == "s":
            loc = loc[:-1] 
        return loc

    def pluralise(self, loc):
        if loc == "global":
            return loc
        
        if loc[-1] == "y":
            loc = loc[:-1] + "ies"
        else:
            loc = loc + "s"
        return loc

    def Probabilistic_Contacts(self, mean, mean_err, Probabilistic=True):
        """
        Possion variable. How many contacts statisticaly.

        Parameters
        ----------
            mean:
                float, the mean expected counts
            mean_err:
                float, the 1 sigma error on the mean
            Probabilistic:
                bool, True to allow the err to value the possion mean. False otherwise
            
        Returns
        -------
            C_i:
                The randomly distributed number of errors.
        """
        if Probabilistic:
            if mean_err != 0: #Errored input
                C_i = max(0, np.random.normal(mean,mean_err))
                C_i = self._random_round(np.random.poisson(C_i))
            else: #Error on counts treated as zero
                C_i = self._random_round(np.random.poisson(mean)) 
            return C_i
        else:
            return self._random_round(mean) 

    def contract_matrix(self, CM, bins, method = np.sum):
        """
        Rebin the matrix from "syoa" bin type to general given by bins with method.

        Parameters
        ----------
            CM:
                np.array The contact matrix (unnormalised)
            bins:
                np.array, bin edges used for rebinning
            method:
                np.method, The method of contraction. np.sum, np.mean etc 
            
        Returns
        -------
            CM:
                np.array The contracted matrix
        """
        cm = np.zeros( (len(bins)-1,len(bins)-1) )
        for bin_xi in range(len(bins)-1):
            for bin_yi in range(len(bins)-1):
                Win_Xi = (bins[bin_xi],bins[bin_xi+1])
                Win_Yi = (bins[bin_yi],bins[bin_yi+1])

                cm[bin_xi, bin_yi] = method(CM[Win_Xi[0]:Win_Xi[1],Win_Yi[0]:Win_Yi[1]])
        return cm

    def contract_matrices(self, Name, bins=np.arange(0, 100 + 5, 5)):
        """
        Rebin the integer year binning to custom bins specified by list useing produced contact matrix
        Appends new rebinning to self.CM_T.

        Parameters
        ----------
            Name: 
                string, Name of matrix rebinning

            bins:
                array, bin edges used for rebinning
            
        Returns
        -------
            None

        """
        if "1D" in self.Tracker_Contact_Type:
            cm = self.CM_T["syoa"] 
            self.CM_T[Name] = {}

            for group in cm.keys():
                #Recreate new hash ages for the new bins and add bins to bin list.
                Test = [list(item) for item in self.age_bins.values()]
                if list(bins) not in Test:
                    self.age_bins = {Name: bins, **self.age_bins}      
                append = {}
                for sex in self.contact_sexes:
                    append[sex] = np.zeros( (len(bins)-1,len(bins)-1) )
                self.CM_T[Name][group] = append    
                for sex in self.contact_sexes:    
                    
                    self.CM_T[Name][group][sex] =  self.contract_matrix(cm[group][sex], bins, np.sum)  

        if "All" in self.Tracker_Contact_Type:
            cm = self.CM_AC["syoa"] 
            self.CM_AC[Name] = {}

            for group in cm.keys():
                #Recreate new hash ages for the new bins and add bins to bin list.
                Test = [list(item) for item in self.age_bins.values()]
                if list(bins) not in Test:
                    self.age_bins = {Name: bins, **self.age_bins}      
                append = {}
                for sex in self.contact_sexes:
                    append[sex] = np.zeros( (len(bins)-1,len(bins)-1) )
                self.CM_AC[Name][group] = append    
                for sex in self.contact_sexes:    
                    
                    self.CM_AC[Name][group][sex] =  self.contract_matrix(cm[group][sex], bins, np.sum)    

        #Rehash the ages
        self.hash_ages()
        return 1

    def Get_characteristic_time(self,location):
        """
        Get the characteristic time and proportion_pysical time for location. (In hours)

        Parameters
        ----------
            location:
                Location 
            
        Returns
        -------
            None

        """
        if location not in ["global", "shelter_intra", "shelter_inter"]:
            characteristic_time = self.IM[location]["characteristic_time"] / 24
            proportion_pysical = self.IM[location]["proportion_physical"]
        elif location in [ "shelter_intra", "shelter_inter"]:
            characteristic_time = self.IM["shelter"]["characteristic_time"] / 24
            proportion_pysical = self.IM["shelter"]["proportion_physical"]
        else:
            characteristic_time = 1
            proportion_pysical = 0.12 
        return characteristic_time, proportion_pysical

#####################################################################################################################################################################
                                ################################### Initalize ##################################
#####################################################################################################################################################################

    def initialise_group_names(self):
        """
        Get list of names of the location sites and set as class variable
        Intitalise;
            self.group_type_names

        Parameters
        ----------
            None

        Returns
        -------
            None

        """
        group_type_names = []
        for groups in self.group_types:
            if groups is not None and len(groups) != 0:
                spec = groups[0].spec
            else:
                continue

            group_type_names.append(spec)
            if spec == "shelter":
                group_type_names.append(spec+"_intra")
                group_type_names.append(spec+"_inter")
        self.group_type_names = group_type_names
        return 1

    def initialise_contact_matrices(self):
        """
        Create set of empty contact matrices and set as class variable
        Intitalise;
            self.CM_T
            self.CM_AC

            depending on contact tracking type

        Parameters
        ----------
            None
            
        Returns
        -------
            None

        """
        if "1D" in self.Tracker_Contact_Type:
            self.CM_T = {}
            # For each type of contact matrix binning, eg BBC, polymod, SYOA...
            for bin_type, bins in self.age_bins.items():
                CM = np.zeros( (len(bins)-1,len(bins)-1) )
                append = {}
                for sex in self.contact_sexes: #For each sex
                    append[sex] = np.zeros_like(CM)

                self.CM_T[bin_type] = {
                    "global": append #Add in a global matrix tracker
                }
                for spec in self.group_type_names: #Over location
                    append = {}
                    for sex in self.contact_sexes: 
                        append[sex] = np.zeros_like(CM)
                    self.CM_T[bin_type][spec] = (
                        append
                    )

            #Initialize for the input contact matrices.
            self.CM_T["Interaction"] = {}
            for spec in self.IM.keys(): #Over location
                if spec not in self.CM_T["syoa"].keys():
                    continue

                IM = self.IM[spec]["contacts"]
                append =  np.zeros_like(IM)
                self.CM_T["Interaction"][spec] = append

        if "All" in self.Tracker_Contact_Type:
            self.CM_AC = {}
            # For each type of contact matrix binning, eg BBC, polymod, SYOA...
            for bin_type, bins in self.age_bins.items():
                CM = np.zeros( (len(bins)-1,len(bins)-1) )
                append = {}
                for sex in self.contact_sexes: #For each sex
                    append[sex] = np.zeros_like(CM)

                self.CM_AC[bin_type] = {
                    "global": append #Add in a global matrix tracker
                }
                for spec in self.group_type_names: #Over location
                    append = {}
                    for sex in self.contact_sexes: 
                        append[sex] = np.zeros_like(CM)
                    self.CM_AC[bin_type][spec] = (
                        append
                    )

            #Initialize for the input contact matrices.
            self.CM_AC["Interaction"] = {}
            for spec in self.IM.keys(): #Over location
                if spec not in self.CM_AC["syoa"].keys():
                    continue

                IM = self.IM[spec]["contacts"]
                append =  np.zeros_like(IM)
                self.CM_AC["Interaction"][spec] = append
        return 1
        
    def intitalise_contact_counters(self):
        """
        Create set of empty interactions for each person in each location and set as class variable
        Intitalise;
            self.contact_counts

        Parameters
        ----------
            None
            
        Returns
        -------
            None

        """
        self.contact_counts = {
            person.id: {
                spec: 0 for spec in self.group_type_names+["care_home_visits", "household_visits", "global"]
            } for person in self.world.people
        }
        
        return 1

    def intitalise_location_counters(self):
        """
        Create set of empty person counts for each location and set as class variable for all timesteps, days and current day.
        Intitalise;
            self.location_counters
            self.location_counters_day
            self.location_counters_day_i

        Parameters
        ----------
            None
            
        Returns
        -------
            None

        """
        locations = []
        for locs in self.group_type_names:
            if locs in ["global", "shelter_inter", "shelter_intra"]:
                continue

            locations.append(self.pluralise(locs))
        self.location_counters = {
            "Timestamp" : [],
            "delta_t": [],
            "loc" : {
                spec : {
                    N: {
                        sex : [] for sex in self.contact_sexes 
                    } for N in range(min(len(getattr(self.world, spec).members), self.MaxVenueTrackingSize))
                } for spec in locations
            }
        }

        self.location_counters_day = {
            "Timestamp" : [],
            "loc" : {
                spec : {
                    N: {
                        sex : [] for sex in self.contact_sexes 
                    } for N in range(min(len(getattr(self.world, spec).members), self.MaxVenueTrackingSize))
                } for spec in locations
            }
        }

        self.location_counters_day_i = {
            "loc" : {
                spec : {
                    N: {
                        sex : [] for sex in self.contact_sexes 
                    } for N in range(min(len(getattr(self.world, spec).members), self.MaxVenueTrackingSize))
                } for spec in locations
            }
        }
        return 1

    def intitalise_location_cum_pop(self):
        """
        Intitialise the cumalitive population at venues to be tracked
        Intitalise;
            self.location_cum_pop

        Parameters
        ----------
            None
            
        Returns
        -------
            None

        """
        self.location_cum_pop = {}
        for bin_type, bins in self.age_bins.items():
        # For each type of contact matrix binning, eg BBC, polymod, SYOA...
            self.location_cum_pop[bin_type] = {}
            CM = np.zeros(len(bins)-1)
            append = {}
            for sex in self.contact_sexes: #For each sex
                append[sex] = np.zeros_like(CM)

            self.location_cum_pop[bin_type]["global"] = append #Add in a global matrix tracker
            
            for spec in self.group_type_names: #Over location
                append = {}
                for sex in self.contact_sexes: 
                    append[sex] = np.zeros_like(CM)
                self.location_cum_pop[bin_type][spec] = (
                    append
                )

        self.location_cum_pop["Interaction"] = {}
        for spec in  self.IM.keys(): #Over location
            self.location_cum_pop["Interaction"][spec] = np.zeros(len(self.IM[spec]["contacts"]))
        return 1


    def intitalise_location_cum_time(self):
        """
        Intitialise the cumalitive population time at venues to be tracked
        Intitalise;
            self.location_cum_time

        Parameters
        ----------
            None
            
        Returns
        -------
            None

        """
        self.location_cum_time = {
                spec: 0 for spec in self.group_type_names 
        }
        self.location_cum_time["global"] = 0
        return 1

    def hash_ages(self):
        """
        store all ages and age_bin indexes in python dict for quick lookup as class variable
        Sets;
            self.age_idxs
            self.ages

        Parameters
        ----------
            None
            
        Returns
        -------
            None

        """
        self.age_idxs = {}
        for bins_name, bins in self.age_bins.items():    
            self.age_idxs[bins_name] = {
                person.id: np.digitize(person.age, bins)-1 for person in self.world.people
            }
        self.ages = {person.id: person.age for person in self.world.people}
        self.sexes = {person.id: person.sex for person in self.world.people}
        return 1

    def load_interactions(self, interaction_path):
        """
        Load in the initial interaction matrices and set as class variable
        Loads;
            self.IM

        Parameters
        ----------
            interaction_path:
                string, location of the yaml file for interactions
            
        Returns
        -------
            None

        """
        with open(interaction_path) as f:
            interaction_config = yaml.load(f, Loader=yaml.FullLoader)
            self.IM = interaction_config["contact_matrices"]

        for loc in self.IM.keys():
            if "type" not in self.IM[loc].keys():
                Bins, Type = make_subgroups.Get_Defaults(loc)
                self.IM[loc]["type"] = Type
            if "bins" not in self.IM[loc].keys():
                Bins, Type = make_subgroups.Get_Defaults(loc)
                self.IM[loc]["bins"] = Bins
        return 1

#####################################################################################################################################################################
                                ################################### Post Process ##################################
#####################################################################################################################################################################

    def convert_dict_to_df(self):
        """
        Transform contact_counts into pandas dataframe for easy sorting
        Sets;
            self.contacts_df 

        Parameters
        ----------
            None
            
        Returns
        -------
            None

        """
        self.contacts_df = pd.DataFrame.from_dict(self.contact_counts,orient="index")
        self.contacts_df["age"] = pd.Series(self.ages)
        self.contacts_df["sex"] = pd.Series(self.sexes)

        for bins_type, age_idxes in self.age_idxs.items():
            col_name = f"{bins_type}_idx"
            self.contacts_df[col_name] = pd.Series(age_idxes)

        
        return 1


    def calc_age_profiles(self):
        """
        Group persons by their ages for contacts in each location
        Sets;
            self.age_profiles

        Parameters
        ----------
            None
            
        Returns
        -------
            None
        """
        def BinCounts(bins_idx, contact_type, ExpN):
            contacts_loc = self.contacts_df[self.contacts_df[contact_type] != 0]
            AgesCount = contacts_loc.groupby([bins_idx], dropna = False).size()
            AgesCount = AgesCount.reindex(range(ExpN-1), fill_value=0)

            MaleCount = contacts_loc[contacts_loc["sex"] == "m"].groupby([bins_idx], dropna = False).size()
            MaleCount = MaleCount.reindex(range(ExpN-1), fill_value=0)

            FemaleCount = contacts_loc[contacts_loc["sex"] == "f"].groupby([bins_idx], dropna = False).size()
            FemaleCount = FemaleCount.reindex(range(ExpN-1), fill_value=0)
            return {"unisex" : AgesCount.values,"male" : MaleCount.values,"female" : FemaleCount.values}

        self.age_profiles = {}
        for bin_type in self.age_bins.keys():
            self.age_profiles[bin_type] = {}
            bins_idx = f"{bin_type}_idx"
            self.age_profiles[bin_type]["global"]= BinCounts(bins_idx, "global", len(self.age_bins[bin_type]))
            for contact_type in self.location_cum_pop["syoa"].keys():
                self.age_profiles[bin_type][contact_type]= BinCounts(bins_idx, contact_type, len(self.age_bins[bin_type]))

        def Contract(bins_idx, locs):
            CM = np.zeros(len(bins_idx)-1)
            APPEND = {}
            for spec in locs: #Over location
                append = {}
                for sex in self.contact_sexes: 
                    append[sex] = np.zeros_like(CM)
                APPEND[spec] = (
                    append
                )

            for spec in locs: #Over location
                for sex in self.contact_sexes: #Over location
                    for bin_x in range(len(bins_idx)-1):
                        Win = [bins_idx[bin_x], bins_idx[bin_x+1]]
                        APPEND[spec][sex][bin_x] = np.sum(self.location_cum_pop["syoa"][spec][sex][Win[0]:Win[1]])
            return APPEND

        for bin_type, bins in self.age_bins.items():
            if bin_type == "syoa":
                continue
            self.location_cum_pop[bin_type] = Contract(bins, self.location_cum_pop["syoa"].keys())
        return 1
       


    def calc_average_contacts(self):
        """
        Get average number of contacts per location per day per age bin
        Sets and rescales;
            self.average_contacts

        Parameters
        ----------
            None
            
        Returns
        -------
            None

        """
        self.average_contacts = {}
        colsWhich = [col for col in self.contacts_df.columns if col not in [key+"_idx" for key in self.age_bins.keys()] and col not in ["age", "sex"] ]
        self.contacts_df[colsWhich] /= self.timer.total_days
        for bin_type in self.age_bins.keys():
            bins_idx = f"{bin_type}_idx"
            ExpN = len(self.age_bins[bin_type])
            AgesCount = self.contacts_df.groupby(self.contacts_df[bins_idx], dropna = False).mean()[colsWhich]
            AgesCount = AgesCount.reindex(range(ExpN-1), fill_value=0)

            self.average_contacts[bin_type] = (
                AgesCount 
            )
        return 1

    def normalise_1D_CM(self):          
        """
        For 1D tracking
        Normalise the contact matrices based on likelyhood to interact with each demographic. 
        Sets and rescales;
            self.CM_T
            self.CM_T_err

            self.NCM
            self.NCM_err

            self.NCM_R
            self.NCM_R_err


        Parameters
        ----------
            None
            
        Returns
        -------
            None
        """
        #Preform normalisation
        #bin_Keys = list(self.age_bins.keys())
        bin_Keys = self.CM_T.keys()

        # if "Interaction" not in bin_Keys:
        #     bin_Keys.append("Interaction")

        for bin_type in bin_Keys:
                
            matrices = self.CM_T[bin_type]
            for contact_type, cm_spec in matrices.items():
                for sex in self.contact_sexes:
                    

                    if bin_type == "Interaction":
                        if  sex == "unisex":
                            cm = cm_spec
                            age_profile = self.location_cum_pop["Interaction"][contact_type]
                        else:
                            continue
                    else:
                        cm = cm_spec[sex]
                        age_profile = self.location_cum_pop[bin_type][contact_type][sex]

  
                    NCM, NCM_err = self.CM_Norm(cm, np.array(age_profile), contact_type=contact_type, Reciprocal=False)
                    NCM_R, NCM_R_err = self.CM_Norm(cm, np.array(age_profile), contact_type=contact_type, Reciprocal=True)

                    if bin_type == "Interaction":
                        if sex == "unisex":
                            if contact_type == "shelter":
                                shelter_shared = 0.75
                                NCM[0,0] *= shelter_shared**2
                                NCM[1,1] *= shelter_shared**2
                                NCM_err[0,0] *= shelter_shared**2
                                NCM_err[1,1] *= shelter_shared**2
                                NCM_R[0,0] *= shelter_shared**2
                                NCM_R[1,1] *= shelter_shared**2
                                NCM_R_err[0,0] *= shelter_shared**2
                                NCM_R_err[1,1] *= shelter_shared**2
                                cm[0,0] *= shelter_shared**2
                                cm[1,1] *= shelter_shared**2

                            self.NCM["Interaction"][contact_type] = NCM
                            self.NCM_err["Interaction"][contact_type] = NCM_err

                            self.NCM_R["Interaction"][contact_type] = NCM_R
                            self.NCM_R_err["Interaction"][contact_type] = NCM_R_err

                            #Basically just counts of interations so assume a poisson error
                            self.CM_T_err["Interaction"][contact_type] = np.sqrt(cm) / self.timer.total_days
                            self.CM_T["Interaction"][contact_type] = cm / self.timer.total_days
                        else:
                            continue
                    else:
                        self.NCM[bin_type][contact_type][sex] = NCM
                        self.NCM_err[bin_type][contact_type][sex] = NCM_err

                        self.NCM_R[bin_type][contact_type][sex] = NCM_R
                        self.NCM_R_err[bin_type][contact_type][sex] = NCM_R_err

                        #Basically just counts of interations so assume a poisson error
                        self.CM_T_err[bin_type][contact_type][sex] = np.sqrt( cm ) 
                        self.CM_T[bin_type][contact_type][sex] = cm / self.timer.total_days
        return 1

    def normalise_All_CM(self):          
        """
        For All contacts All tracking
        Normalise the contact matrices based on likelyhood to interact with each demographic. 
        Sets and rescales;
            self.CM_AC
            self.CM_AC_err

            self.NCM_AC
            self.NCM_AC_err

            self.NCM_AC_R
            self.NCM_AC_R_err


        Parameters
        ----------
            None
            
        Returns
        -------
            None
        """
        #Preform normalisation
        #bin_Keys = list(self.age_bins.keys())
        bin_Keys = self.CM_AC.keys()

        # if "Interaction" not in bin_Keys:
        #     bin_Keys.append("Interaction")

        for bin_type in bin_Keys:
                
            matrices = self.CM_AC[bin_type]
            for contact_type, cm_spec in matrices.items():
                for sex in self.contact_sexes:
                    

                    if bin_type == "Interaction":
                        if  sex == "unisex":
                            cm = cm_spec
                            age_profile = self.location_cum_pop["Interaction"][contact_type]
                        else:
                            continue
                    else:
                        cm = cm_spec[sex]
                        age_profile = self.location_cum_pop[bin_type][contact_type][sex]
  
                    NCM, NCM_err = self.CM_Norm(cm, np.array(age_profile), contact_type=contact_type, Reciprocal=False)
                    NCM_R, NCM_R_err = self.CM_Norm(cm, np.array(age_profile), contact_type=contact_type, Reciprocal=True)

                    if bin_type == "Interaction":
                        if sex == "unisex":
                            self.NCM_AC["Interaction"][contact_type] = NCM
                            self.NCM_AC_err["Interaction"][contact_type] = NCM_err

                            self.NCM_AC_R["Interaction"][contact_type] = NCM_R
                            self.NCM_AC_R_err["Interaction"][contact_type] = NCM_R_err

                            #Basically just counts of interations so assume a poisson error
                            self.CM_AC_err["Interaction"][contact_type] = np.sqrt(cm) / self.timer.total_days
                            self.CM_AC["Interaction"][contact_type] = cm / self.timer.total_days
                        else:
                            continue
                    else:
                        self.NCM_AC[bin_type][contact_type][sex] = NCM
                        self.NCM_AC_err[bin_type][contact_type][sex] = NCM_err

                        self.NCM_AC_R[bin_type][contact_type][sex] = NCM_R
                        self.NCM_AC_R_err[bin_type][contact_type][sex] = NCM_R_err

                        #Basically just counts of interations so assume a poisson error
                        self.CM_AC_err[bin_type][contact_type][sex] = np.sqrt( cm ) 
                        self.CM_AC[bin_type][contact_type][sex] = cm / self.timer.total_days
        return 1

    
    def CM_Norm(self, cm, pop_tots, contact_type="global", Reciprocal=True):
        """
        Normalise the contact matrices using population at location data and time of simulation run time.

        Parameters
        ----------
            cm:
                np.array contact matrix
            pop_tots:
                np.array total counts of visits of each age bin for entire simulation time. (1 person can go to same location more than once)
            contact_type:
                List of the contact_type locations (or none to grab all of them)
            Reciprocal:
                bool, add in reciprocal contacts with reweighting for demographic sizes
        Returns
        -------
            cm:
                np.array contact matrix
            cm_err:
                np.array contact matrix errors

        """
        #Normalise based on characteristic time.
        
        #Normalisation over charecteristic time and population
        factor = (self.Get_characteristic_time(location=contact_type)[0]*np.sum(pop_tots))/self.location_cum_time[contact_type]
        if np.isnan(factor):
            factor = 0
            
        #Create blanks to fill
        norm_cm = np.zeros_like( cm )
        norm_cm_err = np.zeros_like( cm )

        #Loop over elements
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                if Reciprocal: #Count contacts j to i also
                    F_i = 1
                    F_j = 1
                else: #Only count contacts i to j
                    F_i = 2
                    F_j = 0

                #Population rescaling
                w = (pop_tots[j] / pop_tots[i])

                if pop_tots[i] == 0 or pop_tots[j] == 0:
                    continue

                norm_cm[i,j] = (
                    0.5*(F_i*cm[i,j]/pop_tots[i] + (F_j*cm[j,i]/pop_tots[j])*w)*factor
                )
                norm_cm_err[i,j] = (
                    0.5*np.sqrt( 
                        (F_i*np.sqrt(cm[i,j]*pop_tots[i])/pop_tots[i])**2 + 
                        (F_j*np.sqrt(cm[j,i]*pop_tots[j])/pop_tots[j]*w)**2 
                    )*factor
                )
        return norm_cm, norm_cm_err

    def initalize_CM_Normalisations(self):
        """
        Create the CM Normalisation arrays from the CM_T template

        Initalises
        ----------
            self.CM_T_err

            self.NCM
            self.NCM_err

            self.NCM_R
            self.NCM_R_err

        Parameters
        ----------
            None

        Returns
        -------
            None

        """
        
        #Create copies of the contact_matrices to be filled in.
        #Error Matrix
        self.CM_T_err = { 
            bin_type : { 
                loc: {
                    sex : np.zeros_like(self.CM_T[bin_type][loc][sex])
                    for sex in self.CM_T[bin_type][loc].keys() 
                    }
                for loc in self.CM_T[bin_type].keys()
                }
            for bin_type in self.CM_T.keys() if bin_type != "Interaction" 
        }
        self.CM_T_err["Interaction"] = { 
                loc: np.zeros_like(self.CM_T["Interaction"][loc]) for loc in self.CM_T["Interaction"].keys()
        }

        #Normalised Matrices
        self.NCM = { 
            bin_type : { 
                loc: {
                    sex : np.zeros_like(self.CM_T[bin_type][loc][sex])
                    for sex in self.CM_T[bin_type][loc].keys() 
                    }
                for loc in self.CM_T[bin_type].keys()
                }
            for bin_type in self.CM_T.keys() if bin_type != "Interaction" 
        }
        self.NCM["Interaction"] = { 
                loc: np.zeros_like(self.CM_T["Interaction"][loc]) for loc in self.CM_T["Interaction"].keys()
        }

        self.NCM_err = { 
            bin_type : { 
                loc: {
                    sex : np.zeros_like(self.CM_T[bin_type][loc][sex])
                    for sex in self.CM_T[bin_type][loc].keys() 
                    }
                for loc in self.CM_T[bin_type].keys()
                }
            for bin_type in self.CM_T.keys() if bin_type != "Interaction" 
        }
        self.NCM_err["Interaction"] = { 
                loc: np.zeros_like(self.CM_T["Interaction"][loc]) for loc in self.CM_T["Interaction"].keys()
        }

        #Normalised Matrices with reciprocal contacts
        self.NCM_R = { 
            bin_type : { 
                loc: {
                    sex : np.zeros_like(self.CM_T[bin_type][loc][sex])
                    for sex in self.CM_T[bin_type][loc].keys() 
                    }
                for loc in self.CM_T[bin_type].keys()
                }
            for bin_type in self.CM_T.keys() if bin_type != "Interaction" 
        }
        self.NCM_R["Interaction"] = { 
                loc: np.zeros_like(self.CM_T["Interaction"][loc]) for loc in self.CM_T["Interaction"].keys()
        }

        self.NCM_R_err = { 
            bin_type : { 
                loc: {
                    sex : np.zeros_like(self.CM_T[bin_type][loc][sex])
                    for sex in self.CM_T[bin_type][loc].keys() 
                    }
                for loc in self.CM_T[bin_type].keys()
                }
            for bin_type in self.CM_T.keys() if bin_type != "Interaction" 
        }
        self.NCM_R_err["Interaction"] = { 
                loc: np.zeros_like(self.CM_T["Interaction"][loc]) for loc in self.CM_T["Interaction"].keys()
        }
        return 1

    def initalize_CM_All_Normalisations(self):
        """
        Create the CM Normalisation arrays from the CM_AC template

        Initalises
        ----------
            self.CM_AC_err

            self.NCM_AC
            self.NCM_AC_err

            self.NCM_AC_R
            self.NCM_AC_R_err

        Parameters
        ----------
            None

        Returns
        -------
            None

        """
        #Error Matrix
        self.CM_AC_err = { 
            bin_type : { 
                loc: {
                    sex : np.zeros_like(self.CM_AC[bin_type][loc][sex])
                    for sex in self.CM_AC[bin_type][loc].keys() 
                    }
                for loc in self.CM_AC[bin_type].keys()
                }
            for bin_type in self.CM_AC.keys() if bin_type != "Interaction" 
        }
        self.CM_AC_err["Interaction"] = { 
                loc: np.zeros_like(self.CM_AC["Interaction"][loc]) for loc in self.CM_AC["Interaction"].keys()
        }

        #Normalised Matrices
        self.NCM_AC = { 
            bin_type : { 
                loc: {
                    sex : np.zeros_like(self.CM_AC[bin_type][loc][sex])
                    for sex in self.CM_AC[bin_type][loc].keys() 
                    }
                for loc in self.CM_AC[bin_type].keys()
                }
            for bin_type in self.CM_AC.keys() if bin_type != "Interaction" 
        }
        self.NCM_AC["Interaction"] = { 
                loc: np.zeros_like(self.CM_AC["Interaction"][loc]) for loc in self.CM_AC["Interaction"].keys()
        }

        self.NCM_AC_err = { 
            bin_type : { 
                loc: {
                    sex : np.zeros_like(self.CM_AC[bin_type][loc][sex])
                    for sex in self.CM_AC[bin_type][loc].keys() 
                    }
                for loc in self.CM_AC[bin_type].keys()
                }
            for bin_type in self.CM_AC.keys() if bin_type != "Interaction" 
        }
        self.NCM_AC_err["Interaction"] = { 
                loc: np.zeros_like(self.CM_AC["Interaction"][loc]) for loc in self.CM_AC["Interaction"].keys()
        }

        #Normalised Matrices with reciprocal contacts
        self.NCM_AC_R = { 
            bin_type : { 
                loc: {
                    sex : np.zeros_like(self.CM_AC[bin_type][loc][sex])
                    for sex in self.CM_AC[bin_type][loc].keys() 
                    }
                for loc in self.CM_AC[bin_type].keys()
                }
            for bin_type in self.CM_AC.keys() if bin_type != "Interaction" 
        }
        self.NCM_AC_R["Interaction"] = { 
                loc: np.zeros_like(self.CM_AC["Interaction"][loc]) for loc in self.CM_AC["Interaction"].keys()
        }

        self.NCM_AC_R_err = { 
            bin_type : { 
                loc: {
                    sex : np.zeros_like(self.CM_AC[bin_type][loc][sex])
                    for sex in self.CM_AC[bin_type][loc].keys() 
                    }
                for loc in self.CM_AC[bin_type].keys()
                }
            for bin_type in self.CM_AC.keys() if bin_type != "Interaction" 
        }
        self.NCM_AC_R_err["Interaction"] = { 
                loc: np.zeros_like(self.CM_AC["Interaction"][loc]) for loc in self.CM_AC["Interaction"].keys()
        }
        return 1


    def post_process_simulation(self, save=True):
        """
        Perform some post simulation checks and calculations.
            Create contact dataframes
            Get age profiles over the age bins and locations
            Get average contacts by location
            Normalise contact matrices by population demographics

            Print out results to Yaml in Results_Path directory

        Parameters
        ----------
            save:
                bool, Save out contact matrices
            
        Returns
        -------
            None

        """
        if self.group_type_names == []:
            return 1

  

        self.convert_dict_to_df()
        self.calc_age_profiles()
        self.calc_average_contacts()




        if "1D" in self.Tracker_Contact_Type:
            self.initalize_CM_Normalisations()
            self.normalise_1D_CM()

        if "All" in self.Tracker_Contact_Type:
            self.initalize_CM_All_Normalisations()
            self.normalise_All_CM()


        if mpi_rank == 0:
            self.PrintOutResults()

        if save:
            if mpi_size == 1:
                folder_name = "merged_data_output"
            else:
                folder_name = "raw_data_output"

            tracker_dir = self.record_path / "Tracker" / folder_name
            tracker_dir.mkdir(exist_ok=True, parents=True)
            self.tracker_tofile(tracker_dir)
        return 1


#####################################################################################################################################################################
                                ################################### Run tracker ##################################
#####################################################################################################################################################################
    
    def get_active_subgroup(self, person):
        """
        Get subgroup index for interaction metric
        eg. household has subgroups[subgroup_type]: kids[0], young_adults[1], adults[2], old[3]
        subgroup_type is the integer representing the type of person you're wanting to look at.

        Parameters
        ----------
            Person:
                The JUNE person
            
        Returns
        -------
            active_subgroups:
                list of subgroup indexes

        """
        active_subgroups = []
        subgroup_ids = []
        for subgroup in person.subgroups.iter():
            if subgroup is None or subgroup.group.spec == "commute_hub":
                continue
            if person in subgroup.people:
                subgroup_id = f"{subgroup.group.spec}_{subgroup.group.id}"
                if subgroup_id in subgroup_ids:
                    # gotcha: if you're receiving household visits, then you're active in residence
                    # and leisure -- but they are actually the same location...
                    continue
                active_subgroups.append( subgroup )
                subgroup_ids.append(subgroup_id)
        return active_subgroups
        
    def get_contacts_per_subgroup(self, subgroup_type, group):
        """
        Get contacts that a person of subgroup type `subgroup_type` will have with each of the other subgroups,
        in a given group.
        eg. household has subgroups[subgroup_type]: kids[0], young_adults[1], adults[2], old[3]
        subgroup_type is the integer representing the type of person you're wanting to look at.

        Parameters
        ----------
            subgroup_type:
                index of subgroup for the interaction matrix
            group:
                group. Location and group of people at that location
            
        Returns
        -------
            contacts_per_subgroup:
                Mean number contacts in the time period 
            
            contacts_per_subgroup_error:
                Error on mean number contacts in the time period 
        """
        
        spec = group.spec
        cms = self.IM[spec]["contacts"]
        if "contacts_err" in self.IM[spec].keys():
            cms_err = self.IM[spec]["contacts_err"]
        else:
            cms_err = np.zeros_like(cms)

        NSubgroups = len(group.subgroups)
        if group.spec == "school":
            NSubgroups = 2
            #School has many subgroups 0th being for teachers. Rest for year groups
            if subgroup_type == 0:
                pass
            else:
                subgroup_type = 1

        delta_t = self.timer.delta_time.seconds / (3600*24) #In Days
        characteristic_time = self.Get_characteristic_time(location=spec)[0] #In Days

        factor = delta_t / characteristic_time
        contacts_per_subgroup = [
            cms[subgroup_type][ii]*factor for ii in range(NSubgroups)
        ]
        contacts_per_subgroup_error = [
            cms_err[subgroup_type][ii]*factor for ii in range(NSubgroups)
        ]
        return contacts_per_subgroup, contacts_per_subgroup_error
        
    def simulate_1d_contacts(self, group):
        """
        Construct contact matrices. 
        For group at a location we loop over all people and sample from the selection of availible contacts to build more grainual contact matrices.
        Sets;
            self.CM_T
            self.contact_counts

        Parameters
        ----------
            group:
                The group of interest to build contacts
            
        Returns
        -------
            None

        """
        #Loop over people
        if len(group.people) < 2:
            return 1

        
        for person in group.people:
            
            #Shelter we want family groups
            if group.spec == "shelter":
                groups_inter = [list(sub.people) for sub in group.families]
            else: #Want subgroups as defined in groups
                groups_inter = [list(sub.people) for sub in group.subgroups]

            #Work out which subgroup they are in...
            person_subgroup_idx = -1
            for sub_i in range(len(groups_inter)):
                if person in groups_inter[sub_i]:
                    person_subgroup_idx = sub_i
                    break
            if person_subgroup_idx == -1:
                continue

            if group.spec == "school":
                #Allow teachers to mix with ALL students
                if person_subgroup_idx == 0:
                    groups_inter = [list(group.teachers.people), list(group.students)]
                    person_subgroup_idx = 0
                #Allow students to only mix in their classes.
                else:
                    groups_inter = [list(group.teachers.people), list(group.subgroups[person_subgroup_idx].people)]
                    person_subgroup_idx = 1
   
   
            #Get contacts person expects
            contacts_per_subgroup, contacts_per_subgroup_error = self.get_contacts_per_subgroup(person_subgroup_idx, group)
            
            total_contacts = 0


            contact_subgroups = np.arange(0, len(groups_inter), 1)
            for subgroup_contacts, subgroup_contacts_error, contact_subgroup_idx in zip(contacts_per_subgroup, contacts_per_subgroup_error, contact_subgroups):
                #Degugging print out...
                # potential contacts is one less if you're in that subgroup - can't contact yourself!
                subgroup_people = groups_inter[contact_subgroup_idx]
                subgroup_people_without = subgroup_people.copy()
                
                #Person in this subgroup
                if person in subgroup_people:
                    inside = True
                    subgroup_people_without.remove(person)
                else:
                    inside = False

                #is_same_subgroup = subgroup.subgroup_type == subgroup_idx
                if len(subgroup_people) - inside <= 0:
                    continue
                int_contacts = self.Probabilistic_Contacts(subgroup_contacts, subgroup_contacts_error, Probabilistic=True)

                contact_ids_inter = []
                contact_ids_intra = []
                contact_ids = []
                contact_ages = []

                if inside:
                    contacts_index = np.random.choice(len(subgroup_people_without), int_contacts, replace=True)
                else:
                    contacts_index = np.random.choice(len(subgroup_people), int_contacts, replace=True)

                #Shelters a special case...
                #Interaction Matrix
                if group.spec == "shelter": 
                    if inside:
                        self.CM_T["Interaction"][group.spec][0, 0] += int_contacts
                        self.CM_T["Interaction"][group.spec][1, 1] += int_contacts
                    else:
                        self.CM_T["Interaction"][group.spec][0,1] += int_contacts
                        self.CM_T["Interaction"][group.spec][1,0] += int_contacts

                else:
                    self.CM_T["Interaction"][group.spec][person_subgroup_idx, contact_subgroup_idx] += int_contacts
                
                #Get the ids
                for contacts_index_i in contacts_index:  
                    if inside:
                        contact = subgroup_people_without[contacts_index_i]
                    else: 
                        contact = subgroup_people[contacts_index_i]

                    if group.spec == "shelter":
                        if inside:
                            contact_ids_intra.append(contact.id)
                        else: 
                            contact_ids_inter.append(contact.id)
                    contact_ids.append(contact.id)
                    contact_ages.append(contact.age)

                
                age_idx = self.age_idxs["syoa"][person.id]
                
                contact_age_idxs = [
                    self.age_idxs["syoa"][contact_id] for contact_id in contact_ids
                ]

                for cidx in contact_age_idxs:
                    self.CM_T["syoa"]["global"]["unisex"][age_idx,cidx] += 1
                    self.CM_T["syoa"][group.spec]["unisex"][age_idx,cidx] += 1
                    if person.sex == "m" and "male" in self.contact_sexes:
                        self.CM_T["syoa"]["global"]["male"][age_idx,cidx] += 1
                        self.CM_T["syoa"][group.spec]["male"][age_idx,cidx] += 1
                    if person.sex == "f" and "female" in self.contact_sexes:
                        self.CM_T["syoa"]["global"]["female"][age_idx,cidx] += 1
                        self.CM_T["syoa"][group.spec]["female"][age_idx,cidx] += 1
                    total_contacts += 1

                #For shelter only. We check over inter and intra groups
                if group.spec == "shelter":
                    #Inter
                    contact_age_idxs = [
                        self.age_idxs["syoa"][contact_id] for contact_id in contact_ids_inter
                    ]
                    for cidx in contact_age_idxs:
                        
                        self.CM_T["syoa"][group.spec+"_inter"]["unisex"][age_idx,cidx] += 1
                        if person.sex == "m" and "male" in self.contact_sexes:
                            self.CM_T["syoa"][group.spec+"_inter"]["male"][age_idx,cidx] += 1
                        if person.sex == "f" and "female" in self.contact_sexes:
                            self.CM_T["syoa"][group.spec+"_inter"]["female"][age_idx,cidx] += 1

                    #Intra
                    contact_age_idxs = [
                        self.age_idxs["syoa"][contact_id] for contact_id in contact_ids_intra
                    ]
                    for cidx in contact_age_idxs:
                        self.CM_T["syoa"][group.spec+"_intra"]["unisex"][age_idx,cidx] += 1
                        if person.sex == "m" and "male" in self.contact_sexes:
                            self.CM_T["syoa"][group.spec+"_intra"]["male"][age_idx,cidx] += 1
                        if person.sex == "f" and "female" in self.contact_sexes:
                            self.CM_T["syoa"][group.spec+"_intra"]["female"][age_idx,cidx] += 1

            self.contact_counts[person.id]["global"] += total_contacts
            self.contact_counts[person.id][group.spec] += total_contacts
            if group.spec == "shelter":
                self.contact_counts[person.id][group.spec+"_inter"] += total_contacts
                self.contact_counts[person.id][group.spec+"_intra"] += total_contacts

        return 1

    def simulate_All_contacts(self, group):
        """
        Construct contact matrices for all contacts all
        For group at a location we loop over all people and sample from the selection of availible contacts to build more grainual contact matrices.
        Sets;
            self.CM_AC

        Parameters
        ----------
            group:
                The group of interest to build contacts
            
        Returns
        -------
            None

        """
        #Loop over people
        if len(group.people) < 2:
            return 1

        for person in group.people:
            #Shelter we want family groups
            if group.spec == "shelter":
                groups_inter = [list(sub.people) for sub in group.families]
            else: #Want subgroups as defined in groups
                groups_inter = [list(sub.people) for sub in group.subgroups]

            #Work out which subgroup they are in...
            person_subgroup_idx = -1
            for sub_i in range(len(groups_inter)):
                if person in groups_inter[sub_i]:
                    person_subgroup_idx = sub_i
                    break
            if person_subgroup_idx == -1:
                continue

            if group.spec == "school":
                #Allow teachers to mix with ALL students
                if person_subgroup_idx == 0:
                    groups_inter = [list(group.teachers.people), list(group.students)]
                    person_subgroup_idx = 0
                #Allow students to only mix in their classes.
                else:
                    groups_inter = [list(group.teachers.people), list(group.subgroups[person_subgroup_idx].people)]
                    person_subgroup_idx = 1
   
            contact_subgroups = np.arange(0, len(groups_inter), 1)
            for contact_subgroup_idx in contact_subgroups:
                subgroup_people = groups_inter[contact_subgroup_idx]
                subgroup_people_without = subgroup_people.copy()
                
                #Person in this subgroup
                if person in subgroup_people:
                    inside = True
                    subgroup_people_without.remove(person)
                else:
                    inside = False
                #Interaction Matrix

                #Shelters a special case...
                #Interaction Matrix #TODO
                if group.spec == "shelter": 
                    if inside:
                        self.CM_AC["Interaction"][group.spec][0, 0] += len(subgroup_people_without)
                        self.CM_AC["Interaction"][group.spec][1, 1] += len(subgroup_people_without)
                    else:
                        self.CM_AC["Interaction"][group.spec][person_subgroup_idx, contact_subgroup_idx] += len(subgroup_people_without)
                        self.CM_AC["Interaction"][group.spec][contact_subgroup_idx, person_subgroup_idx] += len(subgroup_people_without)
                else:
                    self.CM_AC["Interaction"][group.spec][person_subgroup_idx, contact_subgroup_idx] += len(subgroup_people_without)
                

                contact_ids_inter = []
                contact_ids_intra = []
                contact_ids = []
                contact_ages = []

                #Get the ids 
                for contact in subgroup_people_without:
                    if group.spec == "shelter":
                        if inside:
                            contact_ids_intra.append(contact.id)
                        else: 
                            contact_ids_inter.append(contact.id)
                    contact_ids.append(contact.id)
                    contact_ages.append(contact.age)


                age_idx = self.age_idxs["syoa"][person.id]
                
                contact_age_idxs = [
                    self.age_idxs["syoa"][contact_id] for contact_id in contact_ids
                ]
                for cidx in contact_age_idxs:
                    self.CM_AC["syoa"]["global"]["unisex"][age_idx,cidx] += 1
                    self.CM_AC["syoa"][group.spec]["unisex"][age_idx,cidx] += 1
                    if person.sex == "m" and "male" in self.contact_sexes:
                        self.CM_AC["syoa"]["global"]["male"][age_idx,cidx] += 1
                        self.CM_AC["syoa"][group.spec]["male"][age_idx,cidx] += 1
                    if person.sex == "f" and "female" in self.contact_sexes:
                        self.CM_AC["syoa"]["global"]["female"][age_idx,cidx] += 1
                        self.CM_AC["syoa"][group.spec]["female"][age_idx,cidx] += 1

                #For shelter only. We check over inter and intra groups
                if group.spec == "shelter":
                    #Inter
                    contact_age_idxs = [
                        self.age_idxs["syoa"][contact_id] for contact_id in contact_ids_inter
                    ]
                    for cidx in contact_age_idxs:
                        self.CM_AC["syoa"][group.spec+"_inter"]["unisex"][age_idx,cidx] += 1
                        if person.sex == "m" and "male" in self.contact_sexes:
                            self.CM_AC["syoa"][group.spec+"_inter"]["male"][age_idx,cidx] += 1
                        if person.sex == "f" and "female" in self.contact_sexes:
                            self.CM_AC["syoa"][group.spec+"_inter"]["female"][age_idx,cidx] += 1

                    #Intra
                    contact_age_idxs = [
                        self.age_idxs["syoa"][contact_id] for contact_id in contact_ids_intra
                    ]
                    for cidx in contact_age_idxs:
                        self.CM_AC["syoa"][group.spec+"_intra"]["unisex"][age_idx,cidx] += 1
                        if person.sex == "m" and "male" in self.contact_sexes:
                            self.CM_AC["syoa"][group.spec+"_intra"]["male"][age_idx,cidx] += 1
                        if person.sex == "f" and "female" in self.contact_sexes:
                            self.CM_AC["syoa"][group.spec+"_intra"]["female"][age_idx,cidx] += 1
        return 1

    def simulate_pop_time_venues(self, group):
        """
        Get the population and cumalative time at all venues over all timesteps.
        Sets;
            self.location_cum_pop
            self.location_cum_time

        Parameters
        ----------
            group:
                The group of interest to build contacts
            
        Returns
        -------
            None

        """
        #Loop over people
        if len(group.people) < 2:
            return 1


        for subgroup, sub_i in zip(group.subgroups, range(len(group.subgroups))):
            if group.spec == "school": #change subgroups to Teachers, Students
                if sub_i > 0:
                    sub_i = 1
            if group.spec == "shelter":
                self.location_cum_pop["Interaction"][group.spec][sub_i] += len(group.people)
            else:
                self.location_cum_pop["Interaction"][group.spec][sub_i] += len(subgroup.people)
          
        
        for person in group.people:
            #Only sum those which had any contacts

            age_idx = self.age_idxs["syoa"][person.id]
            self.location_cum_pop["syoa"]["global"]["unisex"][age_idx] += 1
            self.location_cum_pop["syoa"][group.spec]["unisex"][age_idx] += 1
            if group.spec == "shelter":
                self.location_cum_pop["syoa"][group.spec+"_inter"]["unisex"][age_idx] += 1
                self.location_cum_pop["syoa"][group.spec+"_intra"]["unisex"][age_idx] += 1
            if person.sex == "m" and "male" in self.contact_sexes:
                self.location_cum_pop["syoa"]["global"]["male"][age_idx] += 1
                self.location_cum_pop["syoa"][group.spec]["male"][age_idx] += 1
                if group.spec == "shelter":
                    self.location_cum_pop["syoa"][group.spec+"_inter"]["male"][age_idx] += 1
                    self.location_cum_pop["syoa"][group.spec+"_intra"]["male"][age_idx] += 1
            if person.sex == "f" and "female" in self.contact_sexes:
                self.location_cum_pop["syoa"]["global"]["female"][age_idx] += 1
                self.location_cum_pop["syoa"][group.spec]["female"][age_idx] += 1
                if group.spec == "shelter":
                    self.location_cum_pop["syoa"][group.spec+"_inter"]["female"][age_idx] += 1
                    self.location_cum_pop["syoa"][group.spec+"_intra"]["female"][age_idx] += 1
  
        self.location_cum_time["global"] += (len(group.people)*self.timer.delta_time.seconds) / (3600*24) #In Days
        self.location_cum_time[group.spec] += (len(group.people)*self.timer.delta_time.seconds) / (3600*24) #In Days
        if group.spec == "shelter":
            self.location_cum_time[group.spec+"_inter"] += (len(group.people)*self.timer.delta_time.seconds) / (3600*24) #In Days
            self.location_cum_time[group.spec+"_intra"] += (len(group.people)*self.timer.delta_time.seconds) / (3600*24) #In Days
        return 1


    def simulate_attendance(self, group, super_group_name, timer, counter):
        """
        Update person counts at location

        Sets;
            self.location_counters

        Parameters
        ----------
            group:
                The group of interest to build contacts
            super_groups_name:
                location name
            timer:
                timestamp of the time step
            counter:
                venue number in locations list
            
        Returns
        -------
            None

        """
        people = [p.id for p in group.people]
        men = [p.id for p in group.people if p.sex == "m"]
        women = [p.id for p in group.people if p.sex == "f"]
        if super_group_name in self.location_counters["loc"].keys():
            #By dt
            self.location_counters["loc"][super_group_name][counter]["unisex"].append(len(people))
            NewPeople = self.union(self.location_counters_day_i["loc"][super_group_name][counter]["unisex"], people)
            if "male" in self.contact_sexes:
                self.location_counters["loc"][super_group_name][counter]["male"].append(len(men))
                NewMen = self.union(self.location_counters_day_i["loc"][super_group_name][counter]["male"], men)
            if "female" in self.contact_sexes:
                self.location_counters["loc"][super_group_name][counter]["female"].append(len(women)) 
                NewWomen = self.union(self.location_counters_day_i["loc"][super_group_name][counter]["female"], women)

            #By Date 
            if timer.date.hour == timer.initial_date.hour and timer.date.minute== 0 and timer.date.second == 0:
                self.location_counters_day_i["loc"][super_group_name][counter]["unisex"] = people
                self.location_counters_day["loc"][super_group_name][counter]["unisex"].append(len(people))
                if "male" in self.contact_sexes:
                    self.location_counters_day_i["loc"][super_group_name][counter]["male"] = men
                    self.location_counters_day["loc"][super_group_name][counter]["male"].append(len(men))
                if "female" in self.contact_sexes:
                    self.location_counters_day_i["loc"][super_group_name][counter]["female"] = women
                    self.location_counters_day["loc"][super_group_name][counter]["female"].append(len(women))
            else:
                self.location_counters_day_i["loc"][super_group_name][counter]["unisex"] = NewPeople
                self.location_counters_day["loc"][super_group_name][counter]["unisex"][-1] = len(NewPeople)

                if "male" in self.contact_sexes:
                    self.location_counters_day_i["loc"][super_group_name][counter]["male"] = NewMen
                    self.location_counters_day["loc"][super_group_name][counter]["male"][-1] = len(NewMen)
                if "female" in self.contact_sexes:
                    self.location_counters_day_i["loc"][super_group_name][counter]["female"] = NewWomen
                    self.location_counters_day["loc"][super_group_name][counter]["female"][-1] = len(NewWomen)

    def simulate_traveldistance(self, day):
        """
        Simulate travels distances from distance to residence from venue

        Sets;
            self.travel_distance

        Parameters
        ----------
            day:
                str, day of the week for timestep
            
        Returns
        -------
            None

        """

        #Only track over Monday
        if day != "Monday":
            return 1

        self.travel_distance[day] = {}
        for loc in self.location_counters_day_i["loc"].keys():
            self.travel_distance[day][loc] = []
            grouptype = getattr(self.world, loc)
            if grouptype is not None:
                counter = 0  
                groups_which = np.array(grouptype.members)[np.array(self.venues_which[loc])]               
                for group in groups_which: #Loop over all locations.
                    if group.external:
                        counter += 1
                        continue

                    venue_coords = group.coordinates

                    for ID in self.location_counters_day_i["loc"][loc][counter]["unisex"]:
                        person = self.world.people.get_from_id(ID)
                        if person.residence == None:
                            continue
                        household_coords = person.residence.group.area.coordinates
                        self.travel_distance[day][loc].append(geopy.distance.geodesic(household_coords, venue_coords).km)
                    counter += 1
        return 1

#####################################################################################################################################################################
                                ################################### Tracker running ##################################
#####################################################################################################################################################################

    def trackertimestep(self, all_super_groups, timer):
        """
        Loop over all locations at each timestamp to get contact matrices and location population counts.

        Parameters
        ----------
            all_super_groups:
                List of all groups to track contacts over
            date:
                timestamp of the time step (for location populations over time)
            
        Returns
        -------
            None

        """
        self.timer = timer
        self.location_counters["Timestamp"].append(self.timer.date)
        self.location_counters["delta_t"].append(self.timer.delta_time.seconds/3600)

        if self.timer.date.hour == self.timer.initial_date.hour and self.timer.date.minute== 0 and self.timer.date.second == 0:
            self.location_counters_day["Timestamp"].append(self.timer.date)

        DaysElapsed = len(self.location_counters_day["Timestamp"])-1
        day = self.timer.day_of_week

        if DaysElapsed > 0 and DaysElapsed <= 7:
            #Only run after first day completed first day
            self.simulate_traveldistance(day)

        for super_group_name in all_super_groups:
            if "visits" in super_group_name:
                continue
            grouptype = getattr(self.world, super_group_name)
            if grouptype is not None:

                #Venue type not in domain
                if super_group_name not in self.venues_which.keys():
                    continue

                counter = 0       
                Skipped_E = 0
                groups_which = np.array(grouptype.members)[np.array(self.venues_which[super_group_name])]
                for group in groups_which: #Loop over all locations.
                    if group.spec in self.group_type_names:
                        if counter == 0:
                            logger.info(f"Rank {mpi_rank} -- tracking contacts -- {len(self.venues_which[super_group_name])} of {len(grouptype.members)} of type {group.spec}")                    
                        if group.external:
                            Skipped_E += 1
                            counter += 1
                            continue #Skip external venues to the domain.

                        self.simulate_pop_time_venues(group)
                        self.simulate_attendance(group, super_group_name, self.timer, counter)
                        if "1D" in self.Tracker_Contact_Type:
                            self.simulate_1d_contacts(group)
                        if "All" in self.Tracker_Contact_Type:
                            self.simulate_All_contacts(group)
                        counter += 1
                #if counter > 0:
                #    logger.info(f"Rank {mpi_rank} -- external skipped -- {Skipped_E} out of {len(grouptype.members)} for {group.spec}")
        return 1

#####################################################################################################################################################################
                                ################################### Saving tracker results ##################################
#####################################################################################################################################################################

    def tracker_tofile(self, tracker_path):
        """
        Save tracker log. Including;
            Input interaction matrices
            Outputs over each contact matrix type syoa, AC, etc etc

        Parameters
        ----------
            tracker_path:
                str, path to save tracker results
            
        Returns
        -------
            None

        """

        if mpi_size == 1:
            mpi_rankname = ""
            folder_name = "merged_data_output"
            MPI = False
        else:
            mpi_rankname = f"_r{mpi_rank}_"
            folder_name = "raw_data_output"
            MPI = True

        self.Save_CM_JSON(
            dir=tracker_path, 
            folder=folder_name,
            filename=f"tracker_Simulation_Params{mpi_rankname}.yaml", 
            jsonfile=self.tracker_Simulation_Params()
        )

        # Save out the IM
        # self.Save_CM_JSON(
        #     dir=self.record_path / "Tracker" / folder_name / "CM_yamls", 
        #     folder=folder_name,
        #     filename=f"tracker_IM{mpi_rankname}.yaml", 
        #     jsonfile=self.tracker_IMJSON()
        # )

        #All Identical so don't need to do anything here
        if mpi_rank == 0:
            # Save out the IM
            self.Save_CM_JSON(
                dir=self.record_path / "Tracker" / "merged_data_output" / "CM_yamls", 
                folder=folder_name,
                filename=f"tracker_IM.yaml", 
                jsonfile=self.tracker_IMJSON()
            )

        ################################### Saving 1D Contacts tracker results ##################################
        if "1D" in self.Tracker_Contact_Type:
            Tracker_Type = "1D"

            jsonfile = {}
            for binType in list(self.CM_T.keys()):
                jsonfile[binType] = self.tracker_CMJSON(binType=binType, CM=self.CM_T, CM_err=self.CM_T_err)  
            # Save out the CM totals
            self.Save_CM_JSON(
                dir=self.record_path / "Tracker" / folder_name / "CM_yamls", 
                folder=folder_name,
                filename=f"tracker_{Tracker_Type}_Total_CM{mpi_rankname}.yaml", 
                jsonfile=jsonfile
            )

            if MPI == False:
                jsonfile = {}
                for binType in list(self.NCM.keys()):
                    jsonfile[binType] = self.tracker_CMJSON(binType=binType, CM=self.NCM, CM_err=self.NCM_err) 
                # Save out the Normalised CM 
                self.Save_CM_JSON(
                    dir=self.record_path / "Tracker" / folder_name / "CM_yamls", 
                    folder=folder_name,
                    filename=f"tracker_{Tracker_Type}_NCM{mpi_rankname}.yaml", 
                    jsonfile=jsonfile
                )

                jsonfile = {}
                for binType in list(self.NCM_R.keys()):
                    jsonfile[binType] = self.tracker_CMJSON(binType=binType, CM=self.NCM_R, CM_err=self.NCM_R_err)  
                # Save out the Normalised CM with Reciprocal contacts 
                self.Save_CM_JSON(
                    dir=self.record_path / "Tracker" / folder_name / "CM_yamls", 
                    folder=folder_name,
                    filename=f"tracker_{Tracker_Type}_NCM_R{mpi_rankname}.yaml", 
                    jsonfile=jsonfile
                )

        ################################### Saving All Contacts tracker results ##################################
        if "All" in self.Tracker_Contact_Type:
            Tracker_Type = "All"

            jsonfile = {}
            for binType in list(self.CM_AC.keys()):
                jsonfile[binType] = self.tracker_CMJSON(binType=binType, CM=self.CM_AC, CM_err=self.CM_AC_err)  
            # Save out the CM totals
            self.Save_CM_JSON(
                dir=self.record_path / "Tracker" / folder_name / "CM_yamls", 
                folder=folder_name,
                filename=f"tracker_{Tracker_Type}_Total_CM{mpi_rankname}.yaml", 
                jsonfile=jsonfile
            )

            if MPI == False:
                jsonfile = {}
                for binType in list(self.NCM_AC.keys()):
                    jsonfile[binType] = self.tracker_CMJSON(binType=binType, CM=self.NCM_AC, CM_err=self.NCM_AC_err) 
                # Save out the Normalised CM 
                self.Save_CM_JSON(
                    dir=self.record_path / "Tracker" / folder_name / "CM_yamls", 
                    folder=folder_name,
                    filename=f"tracker_{Tracker_Type}_NCM{mpi_rankname}.yaml", 
                    jsonfile=jsonfile
                )

                jsonfile = {}
                for binType in list(self.NCM_AC_R.keys()):
                    jsonfile[binType] = self.tracker_CMJSON(binType=binType, CM=self.NCM_AC_R, CM_err=self.NCM_AC_R_err)  
                # Save out the Normalised CM with Reciprocal contacts 
                self.Save_CM_JSON(
                    dir=self.record_path / "Tracker" / folder_name / "CM_yamls", 
                    folder=folder_name,
                    filename=f"tracker_{Tracker_Type}_NCM_R{mpi_rankname}.yaml", 
                    jsonfile=jsonfile
                )

        ################################### Saving Venue tracker results ##################################
        VD_dir = self.record_path / "Tracker" / folder_name / "Venue_Demographics"
        VD_dir.mkdir(exist_ok=True, parents=True)
        for bin_types in self.age_profiles.keys():
            dat = self.age_profiles[bin_types]
            bins = self.age_bins[bin_types]
            with pd.ExcelWriter(VD_dir / f'PersonCounts_{bin_types}{mpi_rankname}.xlsx', mode="w") as writer:  
                for local in dat.keys(): 

                    df = pd.DataFrame(dat[local])
                    if bin_types == "syoa":
                        df["Ages"] = [f"{low}" for low,high in zip(bins[:-1], bins[1:])]
                    else:
                        df["Ages"] = [f"{low}-{high-1}" for low,high in zip(bins[:-1], bins[1:])]
                    df = df.set_index("Ages")
                    df.loc['Total']= df.sum()
                    df.to_excel(writer, sheet_name=f'{local}')

        VTD_dir = self.record_path / "Tracker" / folder_name / "Venue_TotalDemographics"
        VTD_dir.mkdir(exist_ok=True, parents=True)
        for bin_types in self.location_cum_pop.keys(): 
            dat = self.location_cum_pop[bin_types]
            with pd.ExcelWriter(VTD_dir / f'CumPersonCounts_{bin_types}{mpi_rankname}.xlsx', mode="w") as writer:  
                for local in dat.keys(): 

                    df = pd.DataFrame(dat[local])
                    df.to_excel(writer, sheet_name=f'{local}')

        Dist_dir = self.record_path / "Tracker" / folder_name / "Venue_TravelDist"
        Dist_dir.mkdir(exist_ok=True, parents=True)
        days = list(self.travel_distance.keys())
        with pd.ExcelWriter(Dist_dir / f'Distance_traveled{mpi_rankname}.xlsx', mode="w") as writer:  
            for local in self.travel_distance[days[0]].keys(): 
                df = pd.DataFrame()
                bins = np.arange( 0, 50, 0.05)
                df["bins"] = (bins[:-1]+bins[1:]) / 2
                for day in days:
                    df[day] = np.histogram( self.travel_distance[day][local], bins=bins, density=False)[0]
                df.to_excel(writer, sheet_name=f'{local}')
                    

        V_dir = self.record_path / "Tracker" / folder_name / "Venue_UniquePops"
        V_dir.mkdir(exist_ok=True, parents=True)

        # Save out persons per location
        timestamps = self.location_counters["Timestamp"]
        delta_ts = self.location_counters["delta_t"]
        for sex in self.contact_sexes:
            with pd.ExcelWriter(V_dir / f'Venues_{sex}_Counts_BydT{mpi_rankname}.xlsx', mode="w") as writer:  
                for loc in self.location_counters["loc"].keys():
                    df = pd.DataFrame()
                    df["t"] = timestamps
                    df["dt"] = delta_ts
                    NVenues = len(self.location_counters["loc"][loc].keys())

                    loc_j=0
                    for loc_i in range(NVenues):
                        if np.sum(self.location_counters["loc"][loc][loc_i]["unisex"]) == 0:
                            continue
                        df[loc_j] = self.location_counters["loc"][loc][loc_i][sex]
                        loc_j+=1

                        if loc_j > 600:
                            break

                    df.to_excel(writer, sheet_name=f'{loc}')

        timestamps = self.location_counters_day["Timestamp"]
        for sex in self.contact_sexes:
            with pd.ExcelWriter(V_dir/ f'Venues_{sex}_Counts_ByDate{mpi_rankname}.xlsx', mode="w") as writer:  
                for loc in self.location_counters_day["loc"].keys():
                    df = pd.DataFrame()
                    df["t"] = timestamps

                    NVenues = len(self.location_counters_day["loc"][loc].keys())
                    loc_j=0
                    for loc_i in range(NVenues):
                        if np.sum(self.location_counters_day["loc"][loc][loc_i]["unisex"]) == 0:
                            continue
                        df[loc_j] = self.location_counters_day["loc"][loc][loc_i][sex]
                        loc_j+=1

                        if loc_j > 600:
                            break
                    df.to_excel(writer, sheet_name=f'{loc}')

        # Save contacts per location
        Av_dir = self.record_path / "Tracker" / folder_name / "Venue_AvContacts"
        Av_dir.mkdir(exist_ok=True, parents=True)
        with pd.ExcelWriter(Av_dir / f'Average_contacts{mpi_rankname}.xlsx', mode="w") as writer:  
            for rbt in self.average_contacts.keys():
                df = self.average_contacts[rbt]
                df.to_excel(writer, sheet_name=f'{rbt}')

        #Save out cumulative time 
        CT_dir = self.record_path / "Tracker" / folder_name / "Venue_CumTime"
        CT_dir.mkdir(exist_ok=True, parents=True)
        df = pd.DataFrame.from_dict(self.location_cum_time, orient='index').T
        with pd.ExcelWriter(CT_dir / f'CumTime{mpi_rankname}.xlsx', mode="w") as writer:  
            df.to_excel(writer)
        

        return 1

    def Save_CM_JSON(self, dir, folder, filename, jsonfile):
        junk_dir = self.record_path / "Tracker" / folder / "junk"
        junk_dir.mkdir(exist_ok=True, parents=True)

        dir.mkdir(exist_ok=True, parents=True)
        with open(junk_dir / filename, "w") as f:
                yaml.dump(
                    jsonfile,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    default_style=None,
                    sort_keys=False,
                )
        with open(junk_dir / filename, 'r') as f, open(dir / filename, 'w') as fo:
            for line in f:
                fo.write(line.replace('"', '').replace("'", ""))
        return 1

    def tracker_Simulation_Params(self):
        """
        Get JSON output for Simulation parameters

        Parameters
        ----------
            None
            
        Returns
        -------
            jsonfile:
                json of simulation parameters. total days, weekend/day names.

        """
        jsonfile = {}
        jsonfile["MPI_size"] = mpi_size
        jsonfile["MPI_rank"] = mpi_rank
        jsonfile["total_days"] = self.timer.total_days
        jsonfile["Weekend_Names"] =  self.MatrixString(np.array(self.timer.day_types["weekend"]))
        jsonfile["Weekday_Names"] = self.MatrixString(np.array(self.timer.day_types["weekday"]))

        jsonfile["NVenues"] = {}
        for locations in self.location_counters_day["loc"].keys():
            jsonfile["NVenues"][locations] = len(self.location_counters_day["loc"][locations])
        jsonfile["NPeople"] = len(self.world.people)
        jsonfile["binTypes"] = self.MatrixString(np.array(list(self.CM_T.keys())))
        jsonfile["sexes"] = self.MatrixString(np.array(self.contact_sexes))
        jsonfile["trackerTypes"] = self.MatrixString(np.array(self.Tracker_Contact_Type))
        return jsonfile

    def tracker_IMJSON(self):
        """
        Get JSON output for the interaction matrix inputs to the contact tracker model

        Parameters
        ----------
            None
            
        Returns
        -------
            jsonfile:
                json of interaction matrices information

        """
        jsonfile = {}
        for local in self.IM.keys():
            jsonfile[local] = {}
            for item in self.IM[local].keys():
                if item in ["contacts", "contacts_err", "proportion_physical"]:
                    append = self.MatrixString(np.array(self.IM[local][item]))
                elif item in ["bins"]:
                    append = self.MatrixString(np.array(self.IM[local][item]), dtypeString="int")
                elif item in ["characteristic_time", "type"]:
                    append = self.IM[local][item]
                jsonfile[local][item] = append
        return jsonfile
        
    def tracker_CMJSON(self, binType, CM, CM_err):
        """
        Get final JUNE simulated contact matrix.

        Parameters
        ----------
            binType:
                Name of bin type syoa, AC etc
            sex:
                Sex contact matrix
            SkipLocs:
                list of location names which to skip in the output json
            
        Returns
        -------
            jsonfile:
                json of interaction matrices information

        """
       
        jsonfile = {}
        if binType == "Interaction":
            for local in CM[binType].keys():
                jsonfile[local] = {}

                c_time = self.IM[local]["characteristic_time"]
                I_bintype = self.IM[local]["type"]
                bins = self.IM[local]["bins"]
                p_physical = np.array(self.IM[local]["proportion_physical"])

                jsonfile[local]["proportion_physical"] = self.MatrixString(p_physical)
                jsonfile[local]["characteristic_time"] = c_time
                jsonfile[local]["type"] = I_bintype
                if I_bintype == "Age":
                    jsonfile[local]["bins"] = self.MatrixString(np.array(bins), dtypeString="int")
                elif I_bintype == "Discrete":
                    jsonfile[local]["bins"] = self.MatrixString(np.array(bins), dtypeString="float")

                jsonfile[local]["contacts"] = self.MatrixString(np.array(CM[binType][local]))
                jsonfile[local]["contacts_err"] = self.MatrixString(np.array(CM_err[binType][local]))
        else:
            def expand_proportional(self, PM, bins_I, bins_I_Type, bins_target):
                if bins_I_Type != "Age":
                    ACBins = any(x in ["students", "teachers", "adults", "children"] for x in bins_I)
                    if ACBins:
                        bins_I = np.array([0,AgeAdult, 100])
                    else:
                        return PM
                expand_bins = self.age_bins["syoa"]
                Pmatrix = np.zeros((len(expand_bins)-1, len(expand_bins)-1))
                if PM.shape == (1,1):
                    bins_I = np.array([0,100])
                for bin_xi in range(len(bins_I)-1):
                    for bin_yi in range(len(bins_I)-1):
                        Win_Xi = (bins_I[bin_xi],bins_I[bin_xi+1])
                        Win_Yi = (bins_I[bin_yi],bins_I[bin_yi+1])
                        Pmatrix[Win_Xi[0]:Win_Xi[1], Win_Yi[0]:Win_Yi[1]] = PM[bin_xi, bin_yi]
                Pmatrix = self.contract_matrix(Pmatrix, bins_target, method=np.mean)
                return Pmatrix

            locallists = list(CM[binType].keys())
            locallists.sort()
            for local in locallists:
                local = str(local)
                jsonfile[local] = {}

                if "shelter" in local:
                    local_c = "shelter"
                else:
                    local_c = local

                if local == "global":
                    c_time = 24
                    p_physical = np.array([[0.12]])
                else:
                    c_time = self.IM[local_c]["characteristic_time"]
                    p_physical = expand_proportional(
                        self,
                        np.array(self.IM[local_c]["proportion_physical"]),
                        self.IM[local_c]["bins"],
                        self.IM[local_c]["type"],
                        self.age_bins[binType],
                    )

                bins = self.MatrixString(np.array(self.age_bins[binType]),dtypeString="int")
                p_physical = self.MatrixString(p_physical)

                jsonfile[local]["proportion_physical"] = p_physical
                jsonfile[local]["characteristic_time"] = c_time
                jsonfile[local]["type"] = "Age"
                jsonfile[local]["bins"] = bins

                jsonfile[local]["sex"] = {} 
                for sex in self.contact_sexes:
                    jsonfile[local]["sex"][sex] = {} 
                    jsonfile[local]["sex"][sex]["contacts"] = self.MatrixString(np.array(CM[binType][local][sex]))
                    jsonfile[local]["sex"][sex]["contacts_err"] = self.MatrixString(np.array(CM_err[binType][local][sex]))
        return jsonfile

    def MatrixString(self, matrix, dtypeString="float"):
        """
        Take square matrix array into a string for clarity of printing

        Parameters
        ----------
            matrix:
                np.array matrix
            dtypeString:
                str, 'int' or 'float'
            
        Returns
        -------
            string:
                one line string respresentation of matrix

        """
        string = '['
        if len(matrix.shape) == 1:
            for i in range(matrix.shape[0]):
                if isinstance(matrix[i], str):
                    string += matrix[i]
                else:
                    if np.isnan(matrix[i]) or np.isinf(matrix[i]):
                        matrix[i] = 0
                    
                    if dtypeString == 'float':
                        string += '%.2f' % matrix[i]
                    if dtypeString == 'int':
                        string += '%.0f' % matrix[i]

                if i < matrix.shape[0]-1:
                    string+=','

        if len(matrix.shape) == 2:
            for i in range(matrix.shape[0]):
                string += '['
                for j in range(matrix.shape[1]):
                    if np.isnan(matrix[i,j]) or np.isinf(matrix[i,j]):
                        matrix[i,j] = 0

                    if dtypeString == 'float':
                        string += '%.2f' % matrix[i,j]
                    if dtypeString == 'int':
                        string += '%.0f' % matrix[i,j]

                    if j < matrix.shape[1]-1:
                        string+=','
                string+=']'
                if i < matrix.shape[0]-1:
                        string+=','
        string+=']'
        return string

#####################################################################################################################################################################
                                ################################### Print out tracker results ##################################
#####################################################################################################################################################################

    def PolicyText(self, Type, contacts, contacts_err, proportional_physical, characteristic_time):
        """
        Clear print out of key results from contact matrix tracker for a given location.

        Parameters
        ----------
            Type:
                string bin type, syoa etc
            contacts:
                np.array contact matrix
            contacts_err:
                np.array contact matrix errors
            proportional_physical:
                np.array proportion of physical contact matrix
            characteristic_time:
                np.float The characteristic time at location in hours
        Returns
        -------
            None

        """
        print("  %s:" % Type)
        print("    contacts: %s" % self.MatrixString(contacts))
        print("    contacts_err: %s" % self.MatrixString(contacts_err))
        print("    proportion_physical: %s" % self.MatrixString(proportional_physical))
        print("    characteristic_time: %.2f" % characteristic_time)
        return 1

    def PrintOutResults(self, WhichLocals = [], sex="unisex", binType = "Interaction"):
        """
        Clear printout of results from contact tracker. Loop over all locations for contact matrix of sex and binType

        Parameters
        ----------
            WhichLocals:
                list of location names to print results for
            sex:
                Sex contact matrix
            binType:
                Name of bin type syoa, AC etc
           
            
        Returns
        -------
            None
        """
        if "1D" in self.Tracker_Contact_Type:
            print("Results from 1D interactions...")
            print("")
            if len(WhichLocals) == 0:
                WhichLocals = self.CM_T[binType].keys()

            for local in WhichLocals:            
                contact = self.NCM[binType][local]
                contact_err = self.NCM_err[binType][local]

                
                if local in self.IM.keys():
                    proportional_physical = np.array(self.IM[local]["proportion_physical"])
                    characteristic_time = self.IM[local]["characteristic_time"]
                else:
                    proportional_physical = np.array(0)
                    characteristic_time = 0

                self.PolicyText(local, contact, contact_err, proportional_physical, characteristic_time)
                print("")
                interact = np.array(self.IM[local]["contacts"]) 
                print("    Ratio of contacts and feed in values: %s" % self.MatrixString(contact/interact))
                print("")

        if "All" in self.Tracker_Contact_Type:
            print("Results from all contacts all interactions...")
            print("")

            if len(WhichLocals) == 0:
                WhichLocals = self.CM_AC[binType].keys()

            for local in WhichLocals:            
                contact = self.NCM_AC[binType][local]
                contact_err = self.NCM_AC_err[binType][local]

                
                if local in self.IM.keys():
                    proportional_physical = np.array(self.IM[local]["proportion_physical"])
                    characteristic_time = self.IM[local]["characteristic_time"]
                else:
                    proportional_physical = np.array(0)
                    characteristic_time = 0

                self.PolicyText(local, contact, contact_err, proportional_physical, characteristic_time)
                print("")
                interact = np.array(self.IM[local]["contacts"]) 
                print("    Ratio of contacts and feed in values: %s" % self.MatrixString(contact/interact))
                print("")
        return 1