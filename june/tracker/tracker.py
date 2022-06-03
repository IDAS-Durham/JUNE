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
import geopy.distance

from june.groups.group import make_subgroups

AgeAdult = make_subgroups.Subgroup_Params.AgeYoungAdult
ACArray = np.array([0,AgeAdult,100])
DaysOfWeek_Names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

default_interaction_path = (
    paths.configs_path / "defaults/interaction/interaction.yaml"
)

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
    track_contacts_count:
        bool flag to count people at each location for each timestep
    timer:
        timer object to keep track of time in simualtion
    record_path:
        path for results directory
    load_interactions_path:
        path for interactions yaml directory

    Following used for testing of code if module is reloaded.
    contact_counts: defualt = None
        dictionary mapping counting all contacts in each location for each person
    location_counts: defualt = None
        dictionary mapping of locations and total persons at each time stamp
    contact_matrices: defualt = None
        dictionary mapping the group specs with their contact matrices   

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
        timer=None,
        record_path=Path(""),
        load_interactions_path=default_interaction_path,

        contact_counts=None,
        location_counts=None,
        location_counts_day=None,
        travel_distance = None,
        contact_matrices=None,

        location_cum_pop=None,
        location_cum_time=None,
    ):
        self.world = world
        self.age_bins = age_bins
        self.contact_sexes = contact_sexes
        self.group_types = group_types
        self.timer = timer
        self.location_counters = location_counts
        self.location_counters_day = location_counts_day
        self.record_path = record_path
        self.load_interactions_path = load_interactions_path

        #If we want to track total persons at each location
        self.initialise_group_names()

        if location_counts == None and location_counts_day == None:
            self.intitalise_location_counters()

        self.load_interactions(self.load_interactions_path) #Load in premade contact matrices

        if contact_matrices == None:
            self.initialise_contact_matrices()
        else:
            self.contact_matrices = contact_matrices
        self.contact_types = (
            list(self.contact_matrices["syoa"].keys()) 
            + ["care_home_visits", "household_visits"]
        )
        
        # store all ages/ index to age bins in python dict for quick lookup.
        self.hash_ages() 

        #Initalize time, pop and contact counters
        if contact_counts == None:
            self.intitalise_contact_counters()
        else:
            self.contact_counts = contact_counts

        if location_cum_pop == None:
            self.intitalise_location_cum_pop()
        else:
            self.location_cum_pop = location_cum_pop

        if location_cum_time == None:
            self.intitalise_location_cum_time()
        else:
            self.location_cum_time = location_cum_time

        if travel_distance == None:
            self.travel_distance = {}
        else:
            self.travel_distance = travel_distance


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

    def Probabilistic_Contacts(self, mean, mean_err, Probabilistic=True):
        """
        Possion variable. How many contacts statisticaly.

        Parameters
        ----------
            mean:
                float, the mean expected counts
            mean_err:
                float, the 1 sigma error on the mean
            
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
        Appends new rebinning to self.contact_matrices.

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
        cm = self.contact_matrices["syoa"] 
        self.contact_matrices[Name] = {}

        for group in cm.keys():
            #Recreate new hash ages for the new bins and add bins to bin list.
            Test = [list(item) for item in self.age_bins.values()]
            if list(bins) not in Test:
                self.age_bins = {Name: bins, **self.age_bins}      
            append = {}
            for sex in self.contact_sexes:
                append[sex] = np.zeros( (len(bins)-1,len(bins)-1) )
            self.contact_matrices[Name][group] = append    
            for sex in self.contact_sexes:    
                
                self.contact_matrices[Name][group][sex] =  self.contract_matrix(cm[group][sex], bins, np.sum)                
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
            characteristic_time = self.interaction_matrices[location]["characteristic_time"] / 24
            proportion_pysical = self.interaction_matrices[location]["proportion_physical"]
        elif location in [ "shelter_intra", "shelter_inter"]:
            characteristic_time = self.interaction_matrices["shelter"]["characteristic_time"] / 24
            proportion_pysical = self.interaction_matrices["shelter"]["proportion_physical"]
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
            self.contact_matrices

        Parameters
        ----------
            None
            
        Returns
        -------
            None

        """
        self.contact_matrices = {}
        # For each type of contact matrix binning, eg BBC, polymod, SYOA...
        for bin_type, bins in self.age_bins.items():
            CM = np.zeros( (len(bins)-1,len(bins)-1) )
            append = {}
            for sex in self.contact_sexes: #For each sex
                append[sex] = np.zeros_like(CM)

            self.contact_matrices[bin_type] = {
                "global": append #Add in a global matrix tracker
            }
            for spec in self.group_type_names: #Over location
                append = {}
                for sex in self.contact_sexes: 
                    append[sex] = np.zeros_like(CM)
                self.contact_matrices[bin_type][spec] = (
                    append
                )

        #Initialize for the input contact matrices.
        self.contact_matrices["Interaction"] = {}
        for spec in self.interaction_matrices.keys(): #Over location
            if spec not in self.contact_matrices["syoa"].keys():
                continue

            IM = self.interaction_matrices[spec]["contacts"]
            append =  np.zeros_like(IM)
            self.contact_matrices["Interaction"][spec] = append
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
                spec: 0 for spec in self.contact_types 
            } for person in self.world.people
        }
        
        return 1

    def intitalise_location_counters(self):
        """
        Create set of empty person counts for each location and set as class variable
        Intitalise;
            self.location_counters

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
            if locs[-1] == "y":
                locations.append(locs[:-1]+"ies")
            elif locs[-1] == "s":
                locations.append(locs+"s")
            else:
                locations.append(locs+"s")
        self.location_counters = {
            "Timestamp" : [],
            "delta_t": [],
            "loc" : {
                spec : {
                    N: {
                        sex : [] for sex in self.contact_sexes 
                    } for N in range(len(getattr(self.world, spec).members))
                } for spec in locations
            }
        }

        self.location_counters_day = {
            "Timestamp" : [],
            "loc" : {
                spec : {
                    N: {
                        sex : [] for sex in self.contact_sexes 
                    } for N in range(len(getattr(self.world, spec).members))
                } for spec in locations
            }
        }

        self.location_counters_day_i = {
            "loc" : {
                spec : {
                    N: {
                        sex : [] for sex in self.contact_sexes 
                    } for N in range(len(getattr(self.world, spec).members))
                } for spec in locations
            }
        }
        return 1

    def intitalise_location_cum_pop(self):
        """
        class variable
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
        for spec in  self.interaction_matrices.keys(): #Over location
            if spec not in self.contact_matrices["syoa"].keys():
                continue
            self.location_cum_pop["Interaction"][spec] = np.zeros(self.contact_matrices["Interaction"][spec].shape[0])
        return 1


    def intitalise_location_cum_time(self):
        """
        class variable
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
            self.interaction_matrices

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
            self.interaction_matrices = interaction_config["contact_matrices"]

        for loc in self.interaction_matrices.keys():
            if "type" not in self.interaction_matrices[loc].keys():
                Bins, Type = make_subgroups.Get_Defaults(loc)
                self.interaction_matrices[loc]["type"] = Type
            if "bins" not in self.interaction_matrices[loc].keys():
                Bins, Type = make_subgroups.Get_Defaults(loc)
                self.interaction_matrices[loc]["bins"] = Bins
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

    def normalise_contact_matrices(self, PM=True):          
        """
        Normalise the contact matrices based on likelyhood to interact with each demographic. 
        Sets and rescales;
            self.contact_matrices
            self.contact_matrices_err

            self.normalised_contact_matrices
            self.normalised_contact_matrices_err


        Parameters
        ----------
            None
            
        Returns
        -------
            None
        """
        #Create copies of the contact_matrices to be filled in.
        self.normalised_contact_matrices = { 
            bin_type : { 
                loc: {
                    sex : self.contact_matrices[bin_type][loc][sex]
                    for sex in self.contact_matrices[bin_type][loc].keys() 
                    }
                for loc in self.contact_matrices[bin_type].keys()
                }
            for bin_type in self.contact_matrices.keys() if bin_type != "Interaction" 
        }
        self.normalised_contact_matrices["Interaction"] = { 
                loc: self.contact_matrices["Interaction"][loc] for loc in self.contact_matrices["Interaction"].keys()
        }

        self.normalised_contact_matrices_err = { 
            bin_type : { 
                loc: {
                    sex : self.contact_matrices[bin_type][loc][sex]
                    for sex in self.contact_matrices[bin_type][loc].keys() 
                    }
                for loc in self.contact_matrices[bin_type].keys()
                }
            for bin_type in self.contact_matrices.keys() if bin_type != "Interaction" 
        }
        self.normalised_contact_matrices_err["Interaction"] = { 
                loc: self.contact_matrices["Interaction"][loc] for loc in self.contact_matrices["Interaction"].keys()
        }

        self.contact_matrices_err = { 
            bin_type : { 
                loc: {
                    sex : self.contact_matrices[bin_type][loc][sex]
                    for sex in self.contact_matrices[bin_type][loc].keys() 
                    }
                for loc in self.contact_matrices[bin_type].keys()
                }
            for bin_type in self.contact_matrices.keys() if bin_type != "Interaction" 
        }
        self.contact_matrices_err["Interaction"] = { 
                loc: self.contact_matrices["Interaction"][loc] for loc in self.contact_matrices["Interaction"].keys()
        }

        #Preform normalisation
        bin_Keys = list(self.age_bins.keys())

        if "Interaction" not in bin_Keys:
            bin_Keys.append("Interaction")

        for bin_type in bin_Keys:
                
            matrices = self.contact_matrices[bin_type]
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
  
                    norm_cm, norm_cm_err = self.CM_Norm(cm, np.array(age_profile), bin_type, contact_type=contact_type, PM=PM)

                    if bin_type == "Interaction":
                        if  sex == "unisex":
                            self.normalised_contact_matrices["Interaction"][contact_type] = norm_cm
                            self.normalised_contact_matrices_err["Interaction"][contact_type] = norm_cm_err

                            #Basically just counts of interations so assume a poisson error
                            self.contact_matrices_err["Interaction"][contact_type] = np.sqrt(self.contact_matrices_err[bin_type][contact_type])
                        else:
                            continue
                    else:
                        self.normalised_contact_matrices[bin_type][contact_type][sex] = norm_cm
                        self.normalised_contact_matrices_err[bin_type][contact_type][sex] = norm_cm_err

                        #Basically just counts of interations so assume a poisson error
                        self.contact_matrices_err[bin_type][contact_type][sex] = np.sqrt(self.contact_matrices_err[bin_type][contact_type][sex]) 
        return 1

    
    def CM_Norm(self, cm, pop_tots, bin_type, contact_type="global", PM=True):
        """
        Normalise the contact matrices using population at location data and time of simulation run time.

        Parameters
        ----------
            cm:
                np.array contact matrix
            bins:
                np.array Bin edges 
            global_age_profile:
                np.array total counts of persons in each bin for entire population
            pop_tots:
                np.array total counts of visits of each age bin for entire simulation time. (1 person can go to same location more than once)
            contact_type:
                List of the contact_type locations (or none to grab all of them)
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
        #Create blanks to fill
        norm_cm = np.zeros( cm.shape )
        norm_cm_err = np.zeros( cm.shape )

        if bin_type == "Interaction":
            print("")
            print("contact_type='%s'" % contact_type)
            print("Population matrix=%s" % PM)
            print("CM=np.array(%s)" % [list(cm[i]) for i in range(cm.shape[0])])
            print("C=%s" % self.Get_characteristic_time(location=contact_type)[0])
            print("CT=%s" % self.location_cum_time[contact_type])
            print("Pop_Tots=np.array(%s)" % list(pop_tots))
            print("IM=np.array(%s)" % self.interaction_matrices[contact_type]["contacts"])
            print("")

        #Loop over elements
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                if PM: #Count contacts j to i also
                    F_i = 1
                    F_j = 1
                else: #Only count contacts i to j
                    F_i = 2
                    F_j = 0

                #Population rescaling
                w = (pop_tots[j] / pop_tots[i])
   
                norm_cm[i,j] = (
                    0.5*(F_i*cm[i,j]/pop_tots[i] + (F_j*cm[j,i]/pop_tots[j])*w)*factor
                )

                #TODO Think about this error? 
                norm_cm_err[i,j] = (
                    0.5*np.sqrt( 
                        (F_i*np.sqrt(cm[i,j]*pop_tots[i])/pop_tots[i])**2 + 
                        (F_j*np.sqrt(cm[j,i]*pop_tots[j])/pop_tots[j]*w)**2 
                    )*factor
                )


        
        return norm_cm, norm_cm_err

    def post_process_simulation(self, save=True, PM = True):
        """
        Perform some post simulation checks and calculations.
            Create contact dataframes
            Get age profiles over the age bins and locations
            Get average contacts by location
            Normalise contact matrices by population demographics

            Print out results to Yaml in Results_Path directory

        Parameters
        ----------
            None
            
        Returns
        -------
            None

        """
        if self.group_type_names == []:
            return 1

        self.convert_dict_to_df()
        self.calc_age_profiles()
        self.calc_average_contacts()
        self.normalise_contact_matrices(PM=PM)

        self.PrintOutResults()

        if save:
            tracker_dir = self.record_path / "Tracker" / "data_output"
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
        cms = self.interaction_matrices[spec]["contacts"]
        if "contacts_err" in self.interaction_matrices[spec].keys():
            cms_err = self.interaction_matrices[spec]["contacts_err"]
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
        
    def simulate_1d_contacts(self, group, Contact_All = False):
        """
        Construct contact matrices. 
        For group at a location we loop over all people and sample from the selection of availible contacts to build more grainual contact matrices.
        Sets;
            self.contact_matrices
            self.contact_counts

        Parameters
        ----------
            group:
                The group of interest to build contacts
            
        Returns
        -------
            None

        """
        #Used to get print out for debugging which CM element is playing up...
        # CM_Which_dict = {}
        # if self.interaction_matrices[group.spec]["type"] == "Age":
        #     for bin_i in range(len(self.interaction_matrices[group.spec]["bins"])-1):
        #         bin_i_name = "%s-%s" % (self.interaction_matrices[group.spec]["bins"][bin_i],self.interaction_matrices[group.spec]["bins"][bin_i+1]-1)
        #         CM_Which_dict[bin_i] = {}
        #         for bin_j in range(len(self.interaction_matrices[group.spec]["bins"])-1):
        #             bin_j_name = "%s-%s" % (self.interaction_matrices[group.spec]["bins"][bin_j],self.interaction_matrices[group.spec]["bins"][bin_j+1]-1)
        #             CM_Which_dict[bin_i][bin_j] = f"{bin_i_name}:{bin_j_name}"
        # elif self.interaction_matrices[group.spec]["type"] == "Discrete":
        #     for bin_i in range(len(self.interaction_matrices[group.spec]["bins"])):
        #         bin_i_name = self.interaction_matrices[group.spec]["bins"][bin_i]
        #         CM_Which_dict[bin_i] = {}
        #         for bin_j in range(len(self.interaction_matrices[group.spec]["bins"])):
        #             bin_j_name = self.interaction_matrices[group.spec]["bins"][bin_j]
        #             CM_Which_dict[bin_i][bin_j] = f"{bin_i_name}:{bin_j_name}"

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
                #CM_Which = CM_Which_dict[person_subgroup_idx][contact_subgroup_idx]
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

                if Contact_All == False:
                    if inside:
                        contacts_index = np.random.choice(len(subgroup_people_without), int_contacts, replace=True)
                    else:
                        contacts_index = np.random.choice(len(subgroup_people), int_contacts, replace=True)

                    #Interaction Matrix
                    self.contact_matrices["Interaction"][group.spec][person_subgroup_idx, contact_subgroup_idx] += int_contacts

                else:
                    if inside:
                        N_Potential_Contacts = len(subgroup_people_without)
                        contacts_index = np.random.choice(len(subgroup_people_without), N_Potential_Contacts, replace=False)
                    else:
                        N_Potential_Contacts = len(subgroup_people)
                        contacts_index = np.random.choice(len(subgroup_people), N_Potential_Contacts, replace=False)

                    #Interaction Matrix
                    self.contact_matrices["Interaction"][group.spec][person_subgroup_idx, contact_subgroup_idx] += N_Potential_Contacts


                
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
                    self.contact_matrices["syoa"]["global"]["unisex"][age_idx,cidx] += 1
                    self.contact_matrices["syoa"][group.spec]["unisex"][age_idx,cidx] += 1

                    #self.contact_matrices["syoa"]["global"]["unisex"][age_idx,cidx] += 1/2
                    #self.contact_matrices["syoa"][group.spec]["unisex"][age_idx,cidx] += 1/2
                    #self.contact_matrices["syoa"]["global"]["unisex"][cidx,age_idx] += 1/2
                    #self.contact_matrices["syoa"][group.spec]["unisex"][cidx,age_idx] += 1/2
                    if person.sex == "m" and "male" in self.contact_sexes:
                        self.contact_matrices["syoa"]["global"]["male"][age_idx,cidx] += 1
                        self.contact_matrices["syoa"][group.spec]["male"][age_idx,cidx] += 1

                        #self.contact_matrices["syoa"]["global"]["male"][age_idx,cidx] += 1/2
                        #self.contact_matrices["syoa"][group.spec]["male"][age_idx,cidx] += 1/2
                        #self.contact_matrices["syoa"]["global"]["male"][cidx,age_idx] += 1/2
                        #self.contact_matrices["syoa"][group.spec]["male"][cidx,age_idx] += 1/2
                    if person.sex == "f" and "female" in self.contact_sexes:
                        self.contact_matrices["syoa"]["global"]["female"][age_idx,cidx] += 1
                        self.contact_matrices["syoa"][group.spec]["female"][age_idx,cidx] += 1

                        #self.contact_matrices["syoa"]["global"]["female"][age_idx,cidx] += 1/2
                        #self.contact_matrices["syoa"][group.spec]["female"][age_idx,cidx] += 1/2
                        #self.contact_matrices["syoa"]["global"]["female"][cidx,age_idx] += 1/2
                        #self.contact_matrices["syoa"][group.spec]["female"][cidx,age_idx] += 1/2

                    total_contacts += 1

                #For shelter only. We check over inter and intra groups
                if group.spec == "shelter":
                    #Inter
                    contact_age_idxs = [
                        self.age_idxs["syoa"][contact_id] for contact_id in contact_ids_inter
                    ]
                    for cidx in contact_age_idxs:
                        self.contact_matrices["syoa"][group.spec+"_inter"]["unisex"][age_idx,cidx] += 1

                        #self.contact_matrices["syoa"][group.spec+"_inter"]["unisex"][age_idx,cidx] += 1/2
                        #self.contact_matrices["syoa"][group.spec+"_inter"]["unisex"][cidx,age_idx] += 1/2
                        if person.sex == "m" and "male" in self.contact_sexes:
                            self.contact_matrices["syoa"][group.spec+"_inter"]["male"][age_idx,cidx] += 1

                            #self.contact_matrices["syoa"][group.spec+"_inter"]["male"][age_idx,cidx] += 1/2
                            #self.contact_matrices["syoa"][group.spec+"_inter"]["male"][cidx,age_idx] += 1/2
                        if person.sex == "f" and "female" in self.contact_sexes:
                            self.contact_matrices["syoa"][group.spec+"_inter"]["female"][age_idx,cidx] += 1

                            #self.contact_matrices["syoa"][group.spec+"_inter"]["female"][age_idx,cidx] += 1/2
                            #self.contact_matrices["syoa"][group.spec+"_inter"]["female"][cidx,age_idx] += 1/2


                    #Intra
                    contact_age_idxs = [
                        self.age_idxs["syoa"][contact_id] for contact_id in contact_ids_intra
                    ]
                    for cidx in contact_age_idxs:
                        self.contact_matrices["syoa"][group.spec+"_intra"]["unisex"][age_idx,cidx] += 1

                        #self.contact_matrices["syoa"][group.spec+"_intra"]["unisex"][age_idx,cidx] += 1/2
                        #self.contact_matrices["syoa"][group.spec+"_intra"]["unisex"][cidx,age_idx] += 1/2
                        if person.sex == "m" and "male" in self.contact_sexes:
                            self.contact_matrices["syoa"][group.spec+"_intra"]["male"][age_idx,cidx] += 1

                            #self.contact_matrices["syoa"][group.spec+"_intra"]["male"][age_idx,cidx] += 1/2
                            #self.contact_matrices["syoa"][group.spec+"_intra"]["male"][cidx,age_idx] += 1/2
                        if person.sex == "f" and "female" in self.contact_sexes:
                            self.contact_matrices["syoa"][group.spec+"_intra"]["female"][age_idx,cidx] += 1

                            #self.contact_matrices["syoa"][group.spec+"_intra"]["female"][age_idx,cidx] += 1/2
                            #self.contact_matrices["syoa"][group.spec+"_intra"]["female"][cidx,age_idx] += 1/2

            self.contact_counts[person.id]["global"] += total_contacts
            self.contact_counts[person.id][group.spec] += total_contacts
            if group.spec == "shelter":
                self.contact_counts[person.id][group.spec+"_inter"] += total_contacts
                self.contact_counts[person.id][group.spec+"_intra"] += total_contacts



        for subgroup, sub_i in zip(group.subgroups, range(len(group.subgroups))):
            if group.spec == "school":
                if sub_i > 0:
                    sub_i = 1
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
            if "male" in self.contact_sexes:
                self.location_counters["loc"][super_group_name][counter]["male"].append(len(men))
            if "female" in self.contact_sexes:
                self.location_counters["loc"][super_group_name][counter]["female"].append(len(women)) 

            #By Date 
            if timer.date.hour == timer.initial_date.hour and timer.date.minute== 0 and timer.date.second == 0:
                self.location_counters_day_i["loc"][super_group_name][counter]["unisex"] = people
                self.location_counters_day["loc"][super_group_name][counter]["unisex"].append(len(self.location_counters_day_i["loc"][super_group_name][counter]["unisex"]))
                if "male" in self.contact_sexes:
                    self.location_counters_day_i["loc"][super_group_name][counter]["male"] = men
                    self.location_counters_day["loc"][super_group_name][counter]["male"].append(len(men))
                if "female" in self.contact_sexes:
                    self.location_counters_day_i["loc"][super_group_name][counter]["female"] = women
                    self.location_counters_day["loc"][super_group_name][counter]["female"].append(len(women))
            else:
                self.location_counters_day_i["loc"][super_group_name][counter]["unisex"] = self.union(self.location_counters_day_i["loc"][super_group_name][counter]["unisex"], people)
                self.location_counters_day["loc"][super_group_name][counter]["unisex"][-1] = len(self.location_counters_day_i["loc"][super_group_name][counter]["unisex"])

                if "male" in self.contact_sexes:
                    self.location_counters_day_i["loc"][super_group_name][counter]["male"] = self.union(self.location_counters_day_i["loc"][super_group_name][counter]["male"],men)
                    self.location_counters_day["loc"][super_group_name][counter]["male"][-1] = len(self.location_counters_day_i["loc"][super_group_name][counter]["male"] )
                if "female" in self.contact_sexes:
                    self.location_counters_day_i["loc"][super_group_name][counter]["female"] = self.union(self.location_counters_day_i["loc"][super_group_name][counter]["female"],women)
                    self.location_counters_day["loc"][super_group_name][counter]["female"][-1] = len(self.location_counters_day_i["loc"][super_group_name][counter]["female"] )


    def simulate_traveldistance(self, day):
        if day != "Monday":
            return 1

        self.travel_distance[day] = {}
        for loc in self.location_counters_day_i["loc"].keys():
            self.travel_distance[day][loc] = []
            grouptype = getattr(self.world, loc)
            if grouptype is not None:
                counter = 0                 
                for group in grouptype.members: #Loop over all locations.
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
                counter = 0                 
                for group in grouptype.members: #Loop over all locations.
                    if group.spec in self.group_type_names:
                        self.simulate_1d_contacts(group, Contact_All= False)
                        self.simulate_attendance(group, super_group_name, self.timer, counter)
                        counter += 1
        return 1

#####################################################################################################################################################################
                                ################################### Saving tracker results output ##################################
#####################################################################################################################################################################

    def tracker_tofile(self, tracker_path):
        """
        Save tracker log. Including;
            Input interaction matrices
            Outputs over each contact matrix type syoa, AC, etc etc

        Parameters
        ----------
            None
            
        Returns
        -------
            None

        """
        bintypes = list(self.contact_matrices.keys())
        def tracker_Params():
            jsonfile = {}
            jsonfile["total_days"] = self.timer.total_days
            jsonfile["Weekend_Names"] =  self.MatrixString(np.array(self.timer.day_types["weekend"]))
            jsonfile["Weekday_Names"] = self.MatrixString(np.array(self.timer.day_types["weekday"]))
            return jsonfile

        junk_dir = self.record_path / "Tracker" / "data_output" / "junk"
        junk_dir.mkdir(exist_ok=True, parents=True)


        jsonfile = tracker_Params()
        with open(junk_dir / "tracker_Params_dummy.yaml", "w") as f:
            yaml.dump(
                jsonfile,
                f,
                allow_unicode=True,
                default_flow_style=False,
                default_style=None,
                sort_keys=False,
            )
        with open(junk_dir / "tracker_Params_dummy.yaml", 'r') as f, open(tracker_path / "tracker_Params.yaml", 'w') as fo:
            for line in f:
                fo.write(line.replace('"', '').replace("'", ""))

        cm_dir = self.record_path / "Tracker" / "data_output" / "CM_yamls"
        cm_dir.mkdir(exist_ok=True, parents=True)
        # Save out the CM
        SkipLocs = []
        jsonfile = self.tracker_StartParams()
        with open(junk_dir / "tracker_Input_dummy.yaml", "w") as f:
            yaml.dump(
                jsonfile,
                f,
                allow_unicode=True,
                default_flow_style=False,
                default_style=None,
                sort_keys=False,
            )
        with open(junk_dir / "tracker_Input_dummy.yaml", 'r') as f, open(cm_dir / "tracker_Input.yaml", 'w') as fo:
            for line in f:
                fo.write(line.replace('"', '').replace("'", ""))

        jsonfile = {}
        for binType in bintypes:
            jsonfile[binType] = self.tracker_EndParams(binType=binType, SkipLocs=SkipLocs,Norm=True)  
        with open(junk_dir / "tracker_NormCM_dummy.yaml", "w") as f:
            yaml.dump(
                jsonfile,
                f,
                allow_unicode=True,
                default_flow_style=False,
                default_style=None,
                sort_keys=False,
            )
        with open(junk_dir / "tracker_NormCM_dummy.yaml", 'r') as f, open(cm_dir / "tracker_NormCM.yaml", 'w') as fo:
            for line in f:
                fo.write(line.replace('"', '').replace("'", ""))

        jsonfile = {}
        for binType in bintypes:
            jsonfile[binType] = self.tracker_EndParams(binType=binType, SkipLocs=SkipLocs,Norm=False)  
        with open(junk_dir / "tracker_CM_dummy.yaml", "w") as f:
            yaml.dump(
                jsonfile,
                f,
                allow_unicode=True,
                default_flow_style=False,
                default_style=None,
                sort_keys=False,
            )
        with open(junk_dir / "tracker_CM_dummy.yaml", 'r') as f, open(cm_dir / "tracker_CM.yaml", 'w') as fo:
            for line in f:
                fo.write(line.replace('"', '').replace("'", ""))


        VD_dir = self.record_path / "Tracker" / "data_output" / "Venue_Demographics"
        VD_dir.mkdir(exist_ok=True, parents=True)
        for bin_types in self.age_profiles.keys():
            dat = self.age_profiles[bin_types]
            bins = self.age_bins[bin_types]
            with pd.ExcelWriter(VD_dir / f'PersonCounts_{bin_types}.xlsx', mode="w") as writer:  
                for local in dat.keys(): 

                    df = pd.DataFrame(dat[local])
                    if bin_types == "syoa":
                        df["Ages"] = [f"{low}" for low,high in zip(bins[:-1], bins[1:])]
                    else:
                        df["Ages"] = [f"{low}-{high-1}" for low,high in zip(bins[:-1], bins[1:])]
                    df = df.set_index("Ages")
                    df.loc['Total']= df.sum()
                    df.to_excel(writer, sheet_name=f'{local}')

        VTD_dir = self.record_path / "Tracker" / "data_output" / "Venue_TotalDemographics"
        VTD_dir.mkdir(exist_ok=True, parents=True)
        for bin_types in self.location_cum_pop.keys(): 
            dat = self.location_cum_pop[bin_types]
            with pd.ExcelWriter(VTD_dir / f'CumPersonCounts_{bin_types}.xlsx', mode="w") as writer:  
                for local in dat.keys(): 

                    df = pd.DataFrame(dat[local])
                    df.to_excel(writer, sheet_name=f'{local}')

        Dist_dir = self.record_path / "Tracker" / "data_output" / "Venue_TravelDist"
        Dist_dir.mkdir(exist_ok=True, parents=True)
        days = list(self.travel_distance.keys())
        with pd.ExcelWriter(Dist_dir / f'Distance_traveled.xlsx', mode="w") as writer:  
            for local in self.travel_distance[days[0]].keys(): 
                df = pd.DataFrame()
                bins = np.arange( 0, 6, 0.2)
                df["bins"] = (bins[:-1]+bins[1:]) / 2
                for day in days:
                    df[day] = np.histogram( self.travel_distance[day][local], bins=bins, density=True)[0]
                df.to_excel(writer, sheet_name=f'{local}')
                    

        V_dir = self.record_path / "Tracker" / "data_output" / "Venue_UniquePops"
        V_dir.mkdir(exist_ok=True, parents=True)

        # Save out persons per location
        timestamps = self.location_counters["Timestamp"]
        delta_ts = self.location_counters["delta_t"]
        for sex in self.contact_sexes:
            with pd.ExcelWriter(V_dir / f'Venues_{sex}_Counts_BydT.xlsx', mode="w") as writer:  
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

                        if loc_j > 100:
                            break

                    df.to_excel(writer, sheet_name=f'{loc}')

        timestamps = self.location_counters_day["Timestamp"]
        for sex in self.contact_sexes:
            with pd.ExcelWriter(V_dir/ f'Venues_{sex}_Counts_ByDate.xlsx', mode="w") as writer:  
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

                        if loc_j > 100:
                            break
                    df.to_excel(writer, sheet_name=f'{loc}')

        # Save contacts per location
        Av_dir = self.record_path / "Tracker" / "data_output" / "Venue_AvContacts"
        Av_dir.mkdir(exist_ok=True, parents=True)
        with pd.ExcelWriter(Av_dir / f'Average_contacts.xlsx', mode="w") as writer:  
            for rbt in self.average_contacts.keys():
                df = self.average_contacts[rbt]
                df.to_excel(writer, sheet_name=f'{rbt}')

        return 1

    def tracker_StartParams(self):
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
        for local in self.interaction_matrices.keys():
            jsonfile[local] = {}
            for item in self.interaction_matrices[local].keys():
                if item in ["contacts", "contacts_err", "proportion_physical"]:
                    append = self.MatrixString(np.array(self.interaction_matrices[local][item]))
                elif item in ["bins"]:
                    append = self.MatrixString(np.array(self.interaction_matrices[local][item]), dtypeString="int")
                elif item in ["characteristic_time", "type"]:
                    append = self.interaction_matrices[local][item]
                jsonfile[local][item] = append
        return jsonfile
        
    def tracker_EndParams(self, binType="AC", SkipLocs=[], Norm=True):
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
       
        if binType == "Interaction":
            binType = "Interaction"
            jsonfile  = {}

            for local in self.normalised_contact_matrices[binType].keys():
                jsonfile[local] = {}

                c_time = self.interaction_matrices[local]["characteristic_time"]
                I_bintype = self.interaction_matrices[local]["type"]
                bins = self.interaction_matrices[local]["bins"]
                p_physical = np.array(self.interaction_matrices[local]["proportion_physical"])

                jsonfile[local]["proportion_physical"] = self.MatrixString(p_physical)
                jsonfile[local]["characteristic_time"] = c_time
                jsonfile[local]["type"] = I_bintype
                if I_bintype == "Age":
                    jsonfile[local]["bins"] = self.MatrixString(np.array(bins), dtypeString="int")
                elif I_bintype == "Discrete":
                    jsonfile[local]["bins"] = self.MatrixString(np.array(bins), dtypeString="float")

                if Norm:
                    cm = np.array(self.normalised_contact_matrices[binType][local])
                    cm_err = np.array(self.normalised_contact_matrices_err[binType][local])
                else:
                    cm = np.array(self.contact_matrices[binType][local])
                    cm_err = np.array(self.contact_matrices_err[binType][local])

                jsonfile[local]["contacts"] = self.MatrixString(cm)
                jsonfile[local]["contacts_err"] = self.MatrixString(cm_err)
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


            jsonfile = {}
            locallists = list(self.normalised_contact_matrices[binType].keys())
            locallists.sort()
            for local in locallists:
                local = str(local)

                #Skip some because mismatch between bin type of ages and other types
                if local in SkipLocs:
                    continue
                jsonfile[local] = {}

                if "shelter" in local:
                    local_c = "shelter"
                else:
                    local_c = local

                if local == "global":
                    c_time = 24
                    p_physical = np.array([[0.12]])
                else:
                    c_time = self.interaction_matrices[local_c]["characteristic_time"]
                    p_physical = expand_proportional(
                        self,
                        np.array(self.interaction_matrices[local_c]["proportion_physical"]),
                        self.interaction_matrices[local_c]["bins"],
                        self.interaction_matrices[local_c]["type"],
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
                    if Norm:
                        cm = np.array(self.normalised_contact_matrices[binType][local][sex])
                        cm_err = np.array(self.normalised_contact_matrices_err[binType][local][sex])
                    else:
                        cm = np.array(self.contact_matrices[binType][local][sex])
                        cm_err = np.array(self.contact_matrices_err[binType][local][sex])

                    jsonfile[local]["sex"][sex]["contacts"] = self.MatrixString(cm)
                    jsonfile[local]["sex"][sex]["contacts_err"] = self.MatrixString(cm_err)

            
        return jsonfile

    def MatrixString(self, matrix, dtypeString="float"):
        """
        Take square matrix array into a string for clarity of printing

        Parameters
        ----------
            matrix:
                np.array matrix
            
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
        if len(WhichLocals) == 0:
            WhichLocals = self.contact_matrices[binType].keys()

        for local in WhichLocals:            
            contact = self.normalised_contact_matrices[binType][local]
            contact_err = self.normalised_contact_matrices_err[binType][local]

            
            if local in self.interaction_matrices.keys():
                proportional_physical = np.array(self.interaction_matrices[local]["proportion_physical"])
                characteristic_time = self.interaction_matrices[local]["characteristic_time"]
            else:
                proportional_physical = np.array(0)
                characteristic_time = 0

            self.PolicyText(local, contact, contact_err, proportional_physical, characteristic_time)
            print("")
            interact = np.array(self.interaction_matrices[local]["contacts"]) 
            print("    Ratio of contacts and feed in values: %s" % self.MatrixString(contact/interact))
            print("")
        return 1