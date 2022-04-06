from cProfile import label
import numpy as np
import yaml
import pandas as pd

from pathlib import Path
from june import paths

from june.world import World

import matplotlib.pyplot as plt
import matplotlib.colors as colors
from mpl_toolkits.axes_grid.inset_locator import inset_axes
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates
from datetime import timedelta

from june.groups.group import make_subgroups

AgeAdult = make_subgroups.Subgroup_Params.AgeYoungAdult
ACArray = np.array([0,AgeAdult,100])

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
    simulation_days:
        duration of the simulation in days
    delta_t:
        duration of the timestep in hours
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
        track_contacts_count=False,
        simulation_days=0,
        delta_t=24,
        record_path=Path(""),
        load_interactions_path=default_interaction_path,

        contact_counts=None,
        location_counts=None,
        contact_matrices=None,

        location_cum_pop=None,
        location_cum_time=None,
    ):
        self.world = world
        self.age_bins = age_bins
        self.contact_sexes = contact_sexes
        self.group_types = group_types
        self.track_contacts_count = track_contacts_count
        self.location_counters = location_counts
        self.simulation_days = simulation_days
        self.delta_t = delta_t
        self.record_path = record_path
        self.load_interactions_path = load_interactions_path

        #If we want to track total persons at each location
        self.initialise_group_names()

        if self.track_contacts_count == True and location_counts == None:
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

    def Probabilistic_Contacts(self, mean, mean_err):
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
        if mean_err != 0: #Errored input
            C_i = max(0, np.random.normal(mean,mean_err))
            C_i = self._random_round(np.random.poisson(C_i))
        else: #Error on counts treated as zero
            C_i = self._random_round(np.random.poisson(mean)) 
        return C_i

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

    def Get_characteristic_time(self,contact_type):
        #Pull out relevent characteristic times. TODO Do we use this?
        if contact_type not in ["global", "shelter_intra", "shelter_inter"]:
            characteristic_time = self.interaction_matrices[contact_type]["characteristic_time"] / 24
            proportion_pysical = self.interaction_matrices[contact_type]["proportion_physical"]
        elif contact_type in [ "shelter_intra", "shelter_inter"]:
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
            spec = groups[0].spec
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
                pass
            else:
                locations.append(locs+"s")

        self.location_counters = {
            "Timestamp" : [],
            "loc" : {
                spec : {
                    N: [] for N in range(len(getattr(self.world, spec).members))
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
            Bins, Type = make_subgroups.Get_Defaults(loc)
            if "type" not in self.interaction_matrices[loc].keys():
                self.interaction_matrices[loc]["type"] = Type
            if "bins" not in self.interaction_matrices[loc].keys():
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
        self.contacts_df[colsWhich] /= self.simulation_days
        for bin_type in self.age_bins.keys():
            bins_idx = f"{bin_type}_idx"
            ExpN = len(self.age_bins[bin_type])
            AgesCount = self.contacts_df.groupby(self.contacts_df[bins_idx], dropna = False).mean()[colsWhich]
            AgesCount = AgesCount.reindex(range(ExpN-1), fill_value=0)

            self.average_contacts[bin_type] = (
                AgesCount
            )
        return 1

    def normalise_contact_matrices(self):          
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
                        cm = cm_spec
                        age_profile = self.location_cum_pop["Interaction"][contact_type]
                        age_profile_G = np.ones(age_profile.shape[0])
                        bins = np.arange(age_profile.shape[0]+1) #TODO Find appropirate renorm scale.
                    else:
                        cm = cm_spec[sex]
                        age_profile = self.location_cum_pop[bin_type][contact_type][sex]
                        age_profile_G = self.age_profiles[bin_type]["global"][sex]
                        bins = self.age_bins[bin_type]
 
                    norm_cm, norm_cm_err = self.CM_Norm(cm, np.array(bins), np.array(age_profile_G), np.array(age_profile), contact_type=contact_type)


                    if bin_type == "Interaction":
                        self.normalised_contact_matrices["Interaction"][contact_type] = norm_cm
                        self.normalised_contact_matrices_err["Interaction"][contact_type] = norm_cm_err

                        #Basically just counts of interations so assume a poisson error
                        #TODO Think about this error?
                        self.contact_matrices_err["Interaction"][contact_type] = np.sqrt(self.contact_matrices_err[bin_type][contact_type])

                    else:
                        self.normalised_contact_matrices[bin_type][contact_type][sex] = norm_cm
                        self.normalised_contact_matrices_err[bin_type][contact_type][sex] = norm_cm_err

                        #Basically just counts of interations so assume a poisson error
                        #TODO Think about this error?
                        self.contact_matrices_err[bin_type][contact_type][sex] = np.sqrt(self.contact_matrices_err[bin_type][contact_type][sex]) 
        return 1

    
    def CM_Norm(self, cm, bins, global_age_profile, pop_tots, contact_type="global"):
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
        factor = (self.Get_characteristic_time(contact_type=contact_type)[0]*np.sum(pop_tots))/self.location_cum_time[contact_type]
        #Create blanks to fill
        norm_cm = np.zeros( cm.shape )
        norm_cm_err = np.zeros( cm.shape )

        if isinstance(bins[0], str):
            Bindiffs = np.ones_like(global_age_profile)
        else:
            Bindiffs = np.abs(bins[1:]-bins[:-1])

        global_age_profile = global_age_profile / Bindiffs
        pop_tots = pop_tots

        #Loop over elements
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                
                F_i = 1
                F_j = 1
                #Population rescaling
                w = (global_age_profile[i] / global_age_profile[j])
                #w = (pop_tots[i] / pop_tots[j]) * (Bindiffs[i]/Bindiffs[j])
   
                norm_cm[i,j] = (
                    0.5*(F_i*cm[i,j]/pop_tots[j] + (F_j*cm[j,i]/pop_tots[i])*w)*factor
                )
                #TODO Think about this error? 
                norm_cm_err[i,j] = (
                    0.5*( 
                        np.sqrt(F_i*cm[i,j])/(pop_tots[j]) + 
                        (np.sqrt(F_j*cm[j,i])/(pop_tots[i])*w) 
                    )*factor
                )

        return norm_cm, norm_cm_err

    def post_process_simulation(self):
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
        self.convert_dict_to_df()
        self.calc_age_profiles()
        self.calc_average_contacts()
        self.normalise_contact_matrices()

        self.tracker_results_to_yaml()
        return 1

#####################################################################################################################################################################
                                ################################### Plotting functions ##################################
#####################################################################################################################################################################

    def AnnotateCM(self, cm, cm_err, ax, thresh=1e10):
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
            
        Returns
        -------
            ax
        """
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                fmt = ".2f"
                if cm[i,j] == 1e-16:
                    cm[i,j] = 0
                if cm[i,j] > 1e8:
                    cm[i,j] = np.inf


                # if cm[i,j] >= 1:
                #     fmt = ".1f"
                # else:
                #     fmt = ".1f"
                    
                # if cm[i,j] == 0:
                #     fmt = ".1f"

                if cm_err is not None:
                    text =  r"$ %s \pm %s$" % (format(cm[i, j], fmt), format(cm_err[i, j], fmt))
                else: 
                    text =  r"$ %s $" % (format(cm[i, j], fmt))
                ax.text(j, i,text,
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black",size=15)
        return ax

    def PlotCM(self, cm, cm_err, labels, ax, **plt_kwargs):
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
            **plt_kwargs:
                plot keyword arguements
    
        Returns
        -------
            im:
                referance to plot object
        """
        im = ax.imshow(cm, **plt_kwargs)
        if labels is not None:
            if len(labels) < 25:
                ax.set_xticks(np.arange(len(cm)))
                ax.set_xticklabels(labels,rotation=45)
                ax.set_yticks(np.arange(len(cm)))
                ax.set_yticklabels(labels)
            else:
                pass
        # Loop over data dimensions and create text annotations.
        if cm.shape[0]*cm.shape[1] < 26:
            self.AnnotateCM(cm, cm_err, ax)
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
            return [
                f"{low}-{high-1}" for low,high in zip(bins[:-1], bins[1:])
            ]
        else:
            return None
        
    def CMPlots_GetCM(self, bin_type, contact_type, sex="unisex", normalized=True):
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
            normalized:
                bool, if we use the normalised matrix or the total counts per day
            
        Returns
        -------
            cm:
                np.array contact matrix
            cm_err:
                np.array contact matrix errors
        """
        if bin_type != "Interaction":
            if normalized == True:
                cm =  self.normalised_contact_matrices[bin_type][contact_type][sex]
                cm_err = self.normalised_contact_matrices_err[bin_type][contact_type][sex]
            else:
                cm = self.contact_matrices[bin_type][contact_type][sex]/self.simulation_days 
                cm_err = self.contact_matrices_err[bin_type][contact_type][sex]/self.simulation_days 
        else:
            if normalized == True:
                cm =  self.normalised_contact_matrices[bin_type][contact_type]
                cm_err = self.normalised_contact_matrices_err[bin_type][contact_type]
            else:
                cm = self.contact_matrices[bin_type][contact_type]/self.simulation_days 
                cm_err = self.contact_matrices_err[bin_type][contact_type]/self.simulation_days 
        return cm, cm_err

    def MaxAgeBinIndex(self, bins, MaxAgeBin=60):
        Array = [index for index in range(len(bins)) if bins[index] >= MaxAgeBin]
        if len(Array) != 0:
            return min(Array)
        else:
            return None

    def CMPlots_UsefulCM(self, bin_type, cm, cm_err=None, labels=None):
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
        MaxAgeBin = 60
        if bin_type == "Paper":
            MaxAgeBin = np.inf

        index = self.MaxAgeBinIndex(self.age_bins[bin_type], MaxAgeBin=MaxAgeBin)
        cm = cm[:index, :index]
        if cm_err is not None:
            cm_err=cm_err[:index,:index]
        if labels is not None:
            labels=labels[:index]
        return cm, cm_err, labels

    def IMPlots_GetLabels(self, contact_type, cm):
        """
        Create list of labels for the bins in the input IM plots. More nuisanced as subgroups not always age bins.

        Parameters
        ----------
            contact_type:
                Location of contacts
            cm:
                np.array contact matrix

        Returns
        -------
            labels:
                list of strings for bin labels or none type
        """

        bintype = self.interaction_matrices[contact_type]["type"]
        bins = np.array(self.interaction_matrices[contact_type]["bins"])

        if len(bins) < 25 and bintype == "Age":
            labels = [
                f"{int(low)}-{int(high-1)}" for low,high in zip(bins[:-1], bins[1:])
            ]
        elif len(bins) < 25 and bintype == "Discrete":
            labels = bins
        else:
            labels = None
        return labels

    def IMPlots_GetCM(self, contact_type):
        """
        Get IM out of dictionary. 

        Parameters
        ----------
            contact_type:
                Location of contacts

        Returns
        -------
            cm:
                np.array interactiojn matrix
            cm_err:
                np.array interaction matrix errors (could be none)
        """
        cm = np.array(self.interaction_matrices[contact_type]["contacts"], dtype=float)
        if "contacts_err" not in self.interaction_matrices[contact_type].keys():
            cm_err = None
        else:
            cm_err = np.array(self.interaction_matrices[contact_type]["contacts_err"], dtype=float)
        return cm, cm_err

    def IMPlots_UsefulCM(self, contact_type, cm, cm_err=None, labels=None):
        """
        Truncate the CM for the plots to drop age bins of the data with no people.

        Parameters
        ----------
            binType:
                Name of bin type syoa, AC etc
            bin_ageDiscrete:
                Name type, Age or Discrete
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
        bintype = self.interaction_matrices[contact_type]["type"]
        bins = np.array(self.interaction_matrices[contact_type]["bins"])

        if bintype == "Discrete":
            return cm, cm_err, labels
        
        index = self.MaxAgeBinIndex(np.array(bins))
        cm = cm[:index, :index]
        if cm_err is not None:
            cm_err=cm_err[:index,:index]
        if labels is not None:
            labels=labels[:index]
        return cm, cm_err, labels

#####################################################################################################################################################################
                                ################################### Plotting ##################################
#####################################################################################################################################################################
    
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
        IM, IM_err = self.IMPlots_GetCM(contact_type)
        labels_IM = self.IMPlots_GetLabels(contact_type, IM)
        IM, IM_err, labels_IM = self.IMPlots_UsefulCM(contact_type, IM, cm_err=IM_err, labels=labels_IM)

        #IM_Min = IM[np.isfinite(IM)].min()
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
        cm, cm_err = self.CMPlots_GetCM("Interaction", contact_type, normalized=True)
        cm, cm_err, _ = self.IMPlots_UsefulCM(contact_type, cm, cm_err=cm_err, labels=labels_CM)

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
        norm=colors.Normalize(vmin=vMin, vmax=vMax)
        plt.rcParams["figure.figsize"] = (15,5)
        f, (ax1,ax2, ax3) = plt.subplots(1,3)
        f.patch.set_facecolor('white')

        im1 = self.PlotCM(IM, IM_err, labels_IM, ax1, origin='lower',cmap='RdYlBu_r', norm=norm)
        im2 = self.PlotCM(cm, cm_err, labels_CM, ax2, origin='lower',cmap='RdYlBu_r',norm=norm)

        ratio = cm/IM
        ratio = np.nan_to_num(ratio)
        ratio_values = ratio[np.nonzero(ratio) and ratio<1e3]
        if len(ratio_values) != 0:
            ratio_max = np.nanmax(ratio_values)
            ratio_min = np.nanmin(ratio_values)
            diff_max = np.max([abs(ratio_max-1),abs(ratio_min-1)])
            if diff_max < 0.5:
                diff_max = 0.5
        else:
            diff_max = 0.5

        im3 = self.PlotCM(ratio, None, labels_CM, ax3, origin='lower',cmap='seismic',vmin=1-diff_max,vmax=1+diff_max)
        f.colorbar(im1, ax=ax1)
        f.colorbar(im2, ax=ax2)
        f.colorbar(im3, ax=ax3)
        ax1.set_title("Input Interaction Matrix")
        ax2.set_title("Output Contact Matrix")
        ax3.set_title("Output/Input")

        f.suptitle(f"Survey interaction binned contacts in {contact_type}")
        plt.tight_layout()
        return ax1
        
    def plot_contact_matrix(self, bin_type, contact_type, sex="unisex", normalized=True):
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
            normalized:
                bool, if we use the normalised matrix or the total counts per day
            
        Returns
        -------
            (ax1,ax2):
                matplotlib axes objects (Linear and Log)
        """
        labels = self.CMPlots_GetLabels(self.age_bins[bin_type])
        cm, cm_err = self.CMPlots_GetCM(bin_type, contact_type, sex=sex, normalized=normalized)
        cm, cm_err, labels = self.CMPlots_UsefulCM(bin_type, cm, cm_err, labels)

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

        plt.rcParams["figure.figsize"] = (10,5)
        f, (ax1,ax2) = plt.subplots(1,2)
        f.patch.set_facecolor('white')

        im1 = self.PlotCM(cm, cm_err, labels, ax1, origin='lower',cmap='RdYlBu_r',vmin=0,vmax=cm_Max)
        im2 = self.PlotCM(cm+1e-16, cm_err, labels, ax2, origin='lower',cmap='RdYlBu_r', norm=colors.LogNorm(vmin=cm_Min, vmax=cm_Max))

        f.colorbar(im1, ax=ax1)
        f.colorbar(im2, ax=ax2, extend="min")

        f.suptitle(f"{bin_type} binned contacts in {contact_type} for {sex}")
        plt.tight_layout()
        return (ax1,ax2)

    def plot_comparesexes_contact_matrix(self, bin_type, contact_type, normalized=True):
        """
        Function to plot difference in contact matrices between men and women for bin_type, contact_type.

        Parameters
        ----------
            binType:
                Name of bin type syoa, AC etc
            contact_type:
                Location of contacts
            normalized:
                bool, if we use the normalised matrix or the total counts per day
            
        Returns
        -------
            (ax1,ax2):
                matplotlib axes objects (Linear and Log)
        """
        plt.rcParams["figure.figsize"] = (10,5)
        f, (ax1,ax2) = plt.subplots(1,2)
        f.patch.set_facecolor('white')

        labels = self.CMPlots_GetLabels(self.age_bins[bin_type])

        cm_M, _ = self.CMPlots_GetCM(bin_type, contact_type, "male", normalized)
        cm_F, _ = self.CMPlots_GetCM(bin_type, contact_type, "female", normalized)
        cm = cm_M - cm_F    

        cm, cm_err, labels = self.CMPlots_UsefulCM(bin_type, cm, None, labels)

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
        im1 = self.PlotCM(cm, cm_err, labels, ax1, origin='lower',cmap='RdYlBu_r',vmin=cm_Min,vmax=cm_Max)
        im2 = self.PlotCM(cm+1e-16, cm_err, labels, ax2, origin='lower',cmap='RdYlBu_r', norm=colors.SymLogNorm(linthresh = 1, vmin=cm_Min, vmax=cm_Max))

        f.colorbar(im1, ax=ax1)
        f.colorbar(im2, ax=ax2, extend="min")
        f.suptitle(f"cm_M - cm_F {bin_type} binned contacts in {contact_type}")
        plt.tight_layout()
        return (ax1,ax2)

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
        f, ax = plt.subplots()
        f.patch.set_facecolor('white')

        average_contacts = self.average_contacts[bin_type]
        bins = self.age_bins[bin_type]
        lower = np.zeros(len(bins)-1)

        mids = 0.5*(bins[:-1]+bins[1:])
        widths = (bins[1:]-bins[:-1])
        plotted = 0

        if contact_types is None:
            contact_types = self.contact_types

        for ii, contact_type in enumerate(contact_types):
            if contact_type in ["shelter_intra", "shelter_inter"]:
                continue
            if contact_type not in average_contacts.columns:
                print(f"No contact_type {contact_type}")
                continue
            if contact_type == "global":
                continue

            if plotted > 9:
                hatch="/"
            else:
                hatch=None

            heights = average_contacts[contact_type]
            ax.bar(
                mids, heights, widths, bottom=lower,
                hatch=hatch, label=contact_type,
            )
            plotted += 1

            lower = lower + heights

        ax.set_xlim(bins[0], bins[-1])

        ax.legend(bbox_to_anchor = (0.5,1.02),loc='lower center',ncol=3)
        ax.set_xlabel('Age')
        ax.set_ylabel('average contacts per day')
        f.subplots_adjust(top=0.70)
        plt.tight_layout()
        return ax 


    def plot_demographics_at_locs(self, bin_type, sex="unisex"):
        """
        Plot fraction of each demographic going to each location per day.

        Parameters
        ----------
            binType:
                Name of bin type syoa, AC etc

        Returns
        -------
            ax:
                matplotlib axes object
        """
        distribution_global = self.location_cum_pop[bin_type]["global"][sex]
        distribution_global = self.age_profiles[bin_type]["global"][sex]

        f, ax = plt.subplots()
        f.patch.set_facecolor('white')

        bins = self.age_bins[bin_type]
        mids = 0.5*(bins[:-1]+bins[1:])
        for contact_type in  self.location_cum_pop[bin_type].keys():
            if bin_type in ["global", "shelter_inter", "shelter_intra"]:
                continue
            distribution_loc = self.age_profiles[bin_type][contact_type][sex]
            heights = distribution_loc/distribution_global
            plt.plot(mids, heights, label=contact_type)
 
        ax.set_xlim(bins[0], bins[-1])
        ax.legend(bbox_to_anchor = (0.5,1.02),loc='lower center',ncol=3)
        ax.set_xlabel('Age')
        ax.set_ylabel('faction of demographic going to local')
        f.subplots_adjust(top=0.70)
        plt.tight_layout()
        return ax

    def plot_population_at_locs(self, locations, max_days=7):
        """
        Plot total population of each location for each timestep.

        Parameters
        ----------
            locations:
                list of locations to plot for
            max_days:
                The maximum number of days to plot over

        Returns
        -------
            ax:
                matplotlib axes object

        """
        Interval = timedelta(days=max_days)

        xs = np.array(self.location_counters["Timestamp"])

        max_index = None
        if xs[-1] - xs[0] > Interval:
            max_index = np.sum(xs < xs[0]+Interval)
        xs = xs[:max_index]

        f, ax = plt.subplots()
        f.patch.set_facecolor('white')
        ax.set_title(locations)
        for i in self.location_counters["loc"][locations].keys():
            ys = self.location_counters["loc"][locations][i][:max_index]

            ax.plot(xs, ys)
                    
            if i == 0:
                Total = np.array(ys)
            else:
                Total += np.array(ys)
        # Define the date format
        ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[0]))
        ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=None, interval=1))
        ax.xaxis.set_major_formatter(DateFormatter("%d/%m"))

        #ax.set_xlabel("Timestep")
        ax.set_ylabel("N people at location")
        plt.tight_layout()
        return ax

    def plot_AgeProfileRatios(self, contact_type="global", bin_type="syoa", sex="unisex"):
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
        pop_tots = self.location_cum_pop[bin_type][contact_type][sex]
        global_age_profile = self.age_profiles[bin_type]["global"][sex]

        Bins = np.array(self.age_bins[bin_type])
        Labels = self.CMPlots_GetLabels(Bins)
        Bincenters = 0.5*(Bins[1:]+Bins[:-1])
        Bindiffs = np.abs(Bins[1:]-Bins[:-1])

        Height_G = global_age_profile/Bindiffs
        Height_P = pop_tots/Bindiffs

        ws_G = np.zeros((Bins.shape[0]-1,Bins.shape[0]-1))
        ws_P = np.zeros((Bins.shape[0]-1,Bins.shape[0]-1))
        #Loop over elements
        for i in range(ws_G.shape[0]):
            for j in range(ws_G.shape[1]):
                #Population rescaling
                ws_G[i,j] = Height_G[j] / Height_G[i]
                ws_P[i,j] = Height_P[j] / Height_P[i]

        plt.rcParams["figure.figsize"] = (15,5)
        f, (ax1,ax2) = plt.subplots(1,2)
        
        f.patch.set_facecolor('white')

        vmax_G = np.nan
        vmax_P = np.nan
        if np.isfinite(ws_G).sum() != 0:
            vmax_G = ws_G[np.isfinite(ws_G)].max()*2
        if np.isfinite(ws_P).sum() != 0:
            vmax_P = ws_P[np.isfinite(ws_P)].max()*2

        vmax = np.nanmax([vmax_G, vmax_P])
        if np.isnan(vmax) or vmax == None:
            vmax= 1e-1

        vmin = 10**(-1*np.log10(vmax))

        ax1_ins = ax1.inset_axes([0.8,1.0,0.2,0.2])
        im_P = self.PlotCM(ws_P, None, Labels, ax1, origin='lower',cmap='seismic',norm=colors.LogNorm(vmin=vmin, vmax=vmax))
        im_G = self.PlotCM(ws_G, None, Labels, ax1_ins, origin='lower',cmap='seismic',norm=colors.LogNorm(vmin=vmin, vmax=vmax))
            
        f.colorbar(im_P, ax=ax1, label=r"$\dfrac{Age_{y}}{Age_{x}}$")
        plt.bar(x=Bincenters, height=Height_G/sum(Height_G), width=Bindiffs, tick_label=Labels, alpha=0.5, color="blue", label="Ground truth")
        plt.bar(x=Bincenters, height=Height_P/sum(Height_P), width=Bindiffs, tick_label=Labels, alpha=0.5, color="red", label=contact_type+" tracker")
        ax2.set_ylabel("Normed Population size")
        ax2.set_xlim([Bins[0], Bins[-1]])
        plt.xticks(rotation=90)
        f.suptitle(f"Age profile of {contact_type}")
        plt.legend()
        return (ax1,ax2)


    def make_plots(self, 
        plot_AvContactsLocation=True, 
        plot_FractionalDemographicsLocation=True, 
        plot_dTLocationPopulation=True, 
        plot_InteractionMatrices=True,
        plot_ContactMatrices=True, 
        plot_CompareSexMatrices=True,
        plot_AgeBinning=True):
        """
        Make plots.

        Parameters
        ----------
            plot_AvContactsLocation:
                bool, To plot average contacts per location plots
            plot_FractionalDemographicsLocation:
                bool, To plot fraction of subgroup at locations
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
            
        Returns
        -------
            None
        """

        relevant_bin_types = self.contact_matrices.keys()
        relevant_bin_types_short = ["syoa"]
        relevant_contact_types = self.contact_matrices["syoa"].keys()

        if plot_AvContactsLocation:
            plot_dir = self.record_path / "Average_Contacts" 
            plot_dir.mkdir(exist_ok=True, parents=True)
            for rbt in relevant_bin_types_short:  
                stacked_contacts_plot = self.plot_stacked_contacts(
                    bin_type=rbt, contact_types=relevant_contact_types
                )
                stacked_contacts_plot.plot()
                plt.savefig(plot_dir / f"{rbt}_contacts.png", dpi=150, bbox_inches='tight')
                plt.close()
            
        if plot_FractionalDemographicsLocation:
            for rbt in relevant_bin_types_short: 
                self.plot_demographics_at_locs(rbt)
                plt.savefig(plot_dir / f"{rbt}_dem_contacts.png", dpi=150, bbox_inches='tight')
                plt.close()
            
        if plot_dTLocationPopulation:
            plot_dir = self.record_path / "Location_Pops" 
            plot_dir.mkdir(exist_ok=True, parents=True)
            for locations in self.location_counters["loc"].keys():
                self.plot_population_at_locs(locations)
                plt.savefig(plot_dir / f"{locations}.png", dpi=150, bbox_inches='tight')
                plt.close()

        if plot_InteractionMatrices:
            plot_dir = self.record_path / "Interaction_Matrices" 
            plot_dir.mkdir(exist_ok=True, parents=True)
            for rct in self.interaction_matrices.keys():
                self.plot_interaction_matrix(
                    contact_type=rct
                )
                plt.savefig(plot_dir / f"{rct}.png", dpi=150, bbox_inches='tight')
                plt.close()

        plot_totals = True
        if plot_ContactMatrices:
            plot_dir_1 = self.record_path / "Contact_Matrices"
            plot_dir_1.mkdir(exist_ok=True, parents=True)

            for rbt in relevant_bin_types:
                if rbt == "Interaction":
                    continue

                plot_dir_2 = plot_dir_1 / f"{rbt}"
                plot_dir_2.mkdir(exist_ok=True, parents=True)

                for sex in self.contact_sexes:
                    if sex in ["male", "female"]:
                        continue

                    plot_dir_3 = plot_dir_2 / f"{sex}"
                    plot_dir_3.mkdir(exist_ok=True, parents=True)

                    plot_dir_tot = plot_dir_3 / "Total"
                    plot_dir_tot.mkdir(exist_ok=True, parents=True)

                    for rct in relevant_contact_types:
                        self.plot_contact_matrix(
                            bin_type=rbt, contact_type=rct, sex=sex,
                        )
                        plt.savefig(plot_dir_3 / f"{rct}.png", dpi=150, bbox_inches='tight')
                        plt.close()

                        if plot_totals:
                            self.plot_contact_matrix(
                                bin_type=rbt, contact_type=rct, sex=sex, normalized=False
                            )
                            plt.savefig(plot_dir_tot / f"{rct}.png", dpi=150, bbox_inches='tight')
                            plt.close()

        if plot_CompareSexMatrices:
            plot_dir_1 = self.record_path / "Contact_Matrices"
            plot_dir_1.mkdir(exist_ok=True, parents=True)

            for rbt in relevant_bin_types:
                if rbt == "Interaction":
                    continue

                plot_dir_2 = plot_dir_1 / f"{rbt}"
                plot_dir_2.mkdir(exist_ok=True, parents=True)

                for rct in relevant_contact_types:
                    if "male" in self.contact_sexes and "female" in self.contact_sexes:
                        plot_dir_3 = plot_dir_2 / "CompareSexes"
                        plot_dir_3.mkdir(exist_ok=True, parents=True)

                        self.plot_comparesexes_contact_matrix(
                            bin_type=rbt, contact_type=rct, normalized=True
                            )
                        plt.savefig(plot_dir_3 / f"{rct}.png", dpi=150, bbox_inches='tight')
                        plt.close() 

        if plot_AgeBinning:
            plot_dir = self.record_path / "Age_Binning"
            plot_dir.mkdir(exist_ok=True, parents=True)
            for rbt in ["syoa", "Paper"]:
                if rbt not in self.age_bins.keys():
                    continue
                for rct in relevant_contact_types:
                    self.plot_AgeProfileRatios(
                        contact_type = rct, bin_type=rbt, sex="unisex"
                    )
                    plt.savefig(plot_dir / f"{rbt}_{rct}.png", dpi=150, bbox_inches='tight')
                    plt.close() 
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

        delta_t = self.delta_t / (3600*24) #In Days
        characteristic_time = self.Get_characteristic_time(spec)[0] #In Days

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
        #Loop over people
        if len(group.people) < 2:
            return 1

        for person in group.people:
            #Shelter we want family groups
            if group.spec == "shelter":
                groups_inter = group.families
            else: #Want subgroups as defined in groups
                groups_inter = group.subgroups

            
            

            #Work out which subgroup they are in...
            person_subgroup_idx = -1
            for sub_i in range(len(groups_inter)):
                if person in groups_inter[sub_i].people:
                    person_subgroup_idx = sub_i
                    break
            if person_subgroup_idx == -1:
                continue
   
            #Get contacts person expects

            contacts_per_subgroup, contacts_per_subgroup_error = self.get_contacts_per_subgroup(person_subgroup_idx, group)
            total_contacts = 0
            contact_subgroup_idx = 0
            for subgroup_contacts, subgroup_contacts_error, subgroup in zip(contacts_per_subgroup, contacts_per_subgroup_error, groups_inter):
                # potential contacts is one less if you're in that subgroup - can't contact yourself!
                subgroup_people = list(subgroup.people)
                #Person in this subgroup
                if person in subgroup.people:
                    inside = True
                    subgroup_people_without = list(subgroup.people)
                    subgroup_people_without.remove(person)
                else:
                    inside = False

                #is_same_subgroup = subgroup.subgroup_type == subgroup_idx
                potential_contacts = len(subgroup_people) - inside
                if potential_contacts == 0:
                    continue

                int_contacts = self.Probabilistic_Contacts(subgroup_contacts, subgroup_contacts_error)


                if int_contacts == 0:
                    continue

                contact_ids_inter = []
                contact_ids_intra = []
                contact_ids = []

                if inside:
                    contacts_index = np.random.choice(len(subgroup_people_without), int_contacts, replace=True)
                else:
                    contacts_index = np.random.choice(len(subgroup_people), int_contacts, replace=True)

                #Interaction Matrix
                if group.spec == "school":
                    if person_subgroup_idx > 0:
                        person_subgroup_idx = 1
                    if contact_subgroup_idx > 0:
                        contact_subgroup_idx = 1
                self.contact_matrices["Interaction"][group.spec][person_subgroup_idx, contact_subgroup_idx] += int_contacts
                


                #Get the ids
                for contacts_index_i in contacts_index:  
                    if inside:
                        contact = subgroup_people_without[contacts_index_i]
                    else: 
                        contact = subgroup_people[contacts_index_i]

                    if subgroup.spec == "shelter":
                        if inside:
                            contact_ids_intra.append(contact.id)
                        else: 
                            contact_ids_inter.append(contact.id)
                    contact_ids.append(contact.id)

                age_idx = self.age_idxs["syoa"][person.id]
                contact_age_idxs = [
                    self.age_idxs["syoa"][contact_id] for contact_id in contact_ids
                ]
                for cidx in contact_age_idxs:
                    self.contact_matrices["syoa"]["global"]["unisex"][age_idx,cidx] += 1
                    self.contact_matrices["syoa"][group.spec]["unisex"][age_idx,cidx] += 1
                    if person.sex == "m" and "male" in self.contact_sexes:
                        self.contact_matrices["syoa"]["global"]["male"][age_idx,cidx] += 1
                        self.contact_matrices["syoa"][group.spec]["male"][age_idx,cidx] += 1
                    if person.sex == "f" and "female" in self.contact_sexes:
                        self.contact_matrices["syoa"]["global"]["female"][age_idx,cidx] += 1
                        self.contact_matrices["syoa"][group.spec]["female"][age_idx,cidx] += 1

                    total_contacts += 1

                #For shelter only. We check over inter and intra groups
                if subgroup.spec == "shelter":
                    #Inter
                    contact_age_idxs = [
                        self.age_idxs["syoa"][contact_id] for contact_id in contact_ids_inter
                    ]
                    for cidx in contact_age_idxs:
                        self.contact_matrices["syoa"][group.spec+"_inter"]["unisex"][age_idx,cidx] += 1
                        if person.sex == "m" and "male" in self.contact_sexes:
                            self.contact_matrices["syoa"][group.spec+"_inter"]["male"][age_idx,cidx] += 1
                        if person.sex == "f" and "female" in self.contact_sexes:
                            self.contact_matrices["syoa"][group.spec+"_inter"]["female"][age_idx,cidx] += 1


                    #Intra
                    contact_age_idxs = [
                        self.age_idxs["syoa"][contact_id] for contact_id in contact_ids_intra
                    ]
                    for cidx in contact_age_idxs:
                        self.contact_matrices["syoa"][group.spec+"_intra"]["unisex"][age_idx,cidx] += 1
                        if person.sex == "m" and "male" in self.contact_sexes:
                            self.contact_matrices["syoa"][group.spec+"_intra"]["male"][age_idx,cidx] += 1
                        if person.sex == "f" and "female" in self.contact_sexes:
                            self.contact_matrices["syoa"][group.spec+"_intra"]["female"][age_idx,cidx] += 1

                #Interact contact_idx for interation matrix
                contact_subgroup_idx += 1

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

        self.location_cum_time["global"] += (self.delta_t) / (3600*24) #In Days
        self.location_cum_time[group.spec] += (len(group.people)*self.delta_t) / (3600*24) #In Days
        if group.spec == "shelter":
            self.location_cum_time[group.spec+"_inter"] += (len(group.people)*self.delta_t) / (3600*24) #In Days
            self.location_cum_time[group.spec+"_intra"] += (len(group.people)*self.delta_t) / (3600*24) #In Days
        return 1

#####################################################################################################################################################################
                                ################################### Tracker running ##################################
#####################################################################################################################################################################

    def trackertimestep(self, all_super_groups, date):
        """
        Loop over all locations at each timestamp to get contact matrices and location population counts.

        Sets;
            self.location_counters

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
        self.location_counters["Timestamp"].append(date)
 
        for super_group_name in all_super_groups:
            if "visits" in super_group_name:
                continue
            grouptype = getattr(self.world, super_group_name)

            if grouptype is not None:
                counter = 0              
                for group in grouptype.members: #Loop over all locations.
                    if group.spec in self.group_type_names:
                        self.simulate_1d_contacts(group)


                        if self.track_contacts_count == True and super_group_name in self.location_counters["loc"].keys():
                            self.location_counters["loc"][super_group_name][counter].append(len(group.people))
                            
                        counter += 1
        return 1

#####################################################################################################################################################################
                                ################################### Saving tracker results output ##################################
#####################################################################################################################################################################

    def tracker_results_to_yaml(self):
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
        SkipLocs = ["shelter", "hospital"]
        jsonfile = self.tracker_StartParams()
        for binType in self.normalised_contact_matrices.keys():
            if binType in ["syoa", "Interaction"]:
                continue
            jsonfile[binType] = self.tracker_EndParams(binType=binType, SkipLocs=SkipLocs)  
        with open(self.record_path / "tracker_log.yaml", "w") as f:
            yaml.dump(
                jsonfile,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )

        #Will need to get module openpyxl TODO 
        for bin_types in ["syoa", "AC"]:
            if bin_types not in self.age_profiles.keys():
                continue
            dat = self.age_profiles[bin_types]["global"]
            bins = self.age_bins[bin_types]
            with pd.ExcelWriter(self.record_path / f'PersonCounts_{bin_types}.xlsx', mode="w") as writer:  
                for local in dat.keys(): 
                    df = pd.DataFrame(dat[local])
                    if bin_types == "syoa":
                        df["Ages"] = [f"{low}" for low,high in zip(bins[:-1], bins[1:])]
                    else:
                        df["Ages"] = [f"{low}-{high-1}" for low,high in zip(bins[:-1], bins[1:])]
                    df = df.set_index("Ages")
                    df.loc['Total']= df.sum()
                    df.to_excel(writer, sheet_name=f'{local}')
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
        jsonfile = {
            "Discription": "Initalized with the following parameters"
        }
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
        
    def tracker_EndParams(self, binType="AC", sex="unisex", SkipLocs=[]):
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


        jsonfile = {
            "Description" : f"Results for bintype {binType}",
        }
        locallists = self.intersection(list(self.interaction_matrices.keys()), list(self.normalised_contact_matrices[binType].keys()), permute=False)
        locallists.sort()
        for local in locallists:
            local = str(local)

            #Skip some because mismatch between bin type of ages and other types
            if local in SkipLocs:
                continue
            jsonfile[local] = {}
            cm = self.MatrixString(np.array(self.normalised_contact_matrices[binType][local][sex]))
            cm_err = self.MatrixString(np.array(self.normalised_contact_matrices_err[binType][local][sex]))
            c_time = self.interaction_matrices[local]["characteristic_time"]
            I_bintype = self.interaction_matrices[local]["type"]
            bins = self.MatrixString(np.array(self.age_bins[binType]),dtypeString="int")

            p_physical = expand_proportional(
                self,
                np.array(self.interaction_matrices[local]["proportion_physical"]),
                self.interaction_matrices[local]["bins"],
                I_bintype,
                self.age_bins[binType],
            )
            p_physical = self.MatrixString(p_physical)

            jsonfile[local]["contacts"] = cm
            jsonfile[local]["contacts_err"] = cm_err
            jsonfile[local]["proportion_physical"] = p_physical
            jsonfile[local]["characteristic_time"] = c_time
            jsonfile[local]["type"] = I_bintype
            jsonfile[local]["bins"] = bins
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
        string = "["
        if len(matrix.shape) == 1:
            for i in range(matrix.shape[0]):
                if isinstance(matrix[i], str):
                    string += matrix[i]
                else:
                    if np.isnan(matrix[i]) or np.isinf(matrix[i]):
                        matrix[i] = 0
                    
                    if dtypeString == "float":
                        string += "%.2f" % matrix[i]
                    if dtypeString == "int":
                        string += "%.0f" % matrix[i]

                if i < matrix.shape[0]-1:
                    string+=","

        if len(matrix.shape) == 2:
            for i in range(matrix.shape[0]):
                string += "["
                for j in range(matrix.shape[1]):
                    if np.isnan(matrix[i,j]) or np.isinf(matrix[i,j]):
                        matrix[i,j] = 0

                    if dtypeString == "float":
                        string += "%.2f" % matrix[i,j]
                    if dtypeString == "int":
                        string += "%.0f" % matrix[i,j]

                    if j < matrix.shape[1]-1:
                        string+=","
                string+="]"
                if i < matrix.shape[0]-1:
                        string+=","
        string+="]"
        return f"{string}"

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