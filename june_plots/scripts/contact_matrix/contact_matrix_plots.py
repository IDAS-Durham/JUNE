import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
from bisect import bisect_right
import yaml
import numpy as np
from collections import defaultdict

from june.policy import Policies
from june import paths

default_policy_filename = (
    paths.configs_path / "defaults/policy/policy.yaml"
)

plt.style.use(['science'])
plt.style.reload_library()

# Household contact matrix
default_household_contact_matrix = np.array([[1.20, 1.20, 1.20, 1.20, 1.20, 1.20, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69],
                                             [1.20, 1.20, 1.20, 1.20, 1.20, 1.20, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69],
                                             [1.20, 1.20, 1.20, 1.20, 1.20, 1.20, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69],
                                             [1.20, 1.20, 1.20, 1.20, 1.20, 1.20, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69],
                                             [1.20, 1.20, 1.20, 1.20, 1.20, 1.20, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69],
                                             [1.20, 1.20, 1.20, 1.20, 1.20, 1.20, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69, 1.69],
                                             [1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.34, 1.34, 1.47, 1.47, 1.47, 1.47, 1.47, 1.47, 1.47, 1.47, 1.50, 1.50, 1.50],
                                             [1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.34, 1.34, 1.47, 1.47, 1.47, 1.47, 1.47, 1.47, 1.47, 1.47, 1.50, 1.50, 1.50],
                                             [1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.30, 1.30, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34],
                                             [1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.30, 1.30, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34],
                                             [1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.30, 1.30, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34],
                                             [1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.30, 1.30, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34],
                                             [1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.30, 1.30, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34],
                                             [1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.30, 1.30, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34],
                                             [1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.30, 1.30, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34],
                                             [1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.30, 1.30, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34],
                                             [1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.50, 1.50, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.40, 1.40, 1.40],
                                             [1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.50, 1.50, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.40, 1.40, 1.40],
                                             [1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.50, 1.50, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.34, 1.40, 1.40, 1.40]])

# School contact matrix
default_school_contact_matrix = np.array([[2.50, 0.75, 0.25, 0.25, 0.25, 0.25, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0],
                                          [0.75, 2.50, 0.75, 0.25, 0.25, 0.25, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0],
                                          [0.25, 0.75, 2.50, 0.75, 0.25, 0.25, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0],
                                          [0.25, 0.25, 0.75, 2.05, 0.75, 0.25, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0],
                                          [0.25, 0.25, 0.25, 0.75, 2.50, 0.75, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0],
                                          [0.25, 0.25, 0.25, 0.25, 0.75, 2.50, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0],
                                          [0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80],
                                          [0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80],
                                          [0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80],
                                          [0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80],
                                          [0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80],
                                          [0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80],
                                          [0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80],
                                          [0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80],
                                          [0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80],
                                          [0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80],
                                          [0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80],
                                          [0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80],
                                          [0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80, 4.80]])
                                        


class ContactMatrixPlots():
    """
    Class for plotting contact matrices derived from JUNE

    Parameters
    ----------
    world
    """

    def __init__(
            self,
            world,
            colors,
            policy_filename = default_policy_filename,
            household_contact_matrix = default_household_contact_matrix,
            school_contact_matrix = default_school_contact_matrix,
    ):
        self.world = world
        self.colors = colors
        self.policies = Policies.from_file(policy_filename)
        self.policies.init_policies(self.world)
        self.household_contact_matrix = household_contact_matrix
        self.school_contact_matrix = school_contact_matrix


    def load_world_data(self):
        "Load data and arrays."
        # BBC age bins
        self.bins = [0,5,10,13,15,18,20,22,25,30,35,40,45,50,55,60,65,70,75,200]
        # 2018 mid-year population estimate of UK
        self.all_age_population = np.array([3914028, 4138524, 2381486, 1477408, 2140139, 1529111, 
                                    1628812, 2555763, 4527175, 4433357, 4372234, 3993392,
                                    4507391, 4674235, 4293820, 3673109, 3396435, 3251596, 5517526])
        # Bin all people in world in age bins
        world_ages = [person.age for person in self.world.people]
        _, self.age_array = np.unique(np.searchsorted(self.bins, world_ages, side='right'),return_counts=True)
    

    def calculate_all_contact_matrices(self, date):
        "Calculate contact matrices for all locations."
        # set up age binning arrays for each location
        self.location_arrays = {}
        self.location_arrays['household'] = np.zeros((len(self.world.households), 19), dtype=np.int)
        self.location_arrays['school'] = np.zeros((len(self.world.schools), 19), dtype=np.int)
        self.location_arrays['company'] = np.zeros((len(self.world.companies), 19), dtype=np.int)

        # set up interaction arrays for each location
        self.interaction_arrays = {}
        self.interaction_arrays['household'] = np.zeros((19, 19))
        self.interaction_arrays['school'] = np.zeros((19, 19))
        self.interaction_arrays['company'] = np.zeros((19, 19))

        beta_reductions = self.get_beta_reductions(date)

        self.bin_locations(date)
        self.calculate_interactions()

        self.contact_matrices = {}
        for location in self.interaction_arrays.keys():
            self.contact_matrices[location] = self.calculate_contact_matrix(
                self.interaction_arrays[location]
            ) * beta_reductions[location]
        return None


    def bin_locations(self, date):
        "Bin all locations by age."
        activities = ["primary_activity", "residence"]
        active_individual_policies = self.policies.individual_policies.get_active(date=date)
        for location in self.location_arrays.keys():
            if location == 'household':
                for i in range(len(self.world.households)):    
                    for person in self.world.households[i].people:
                        age_bin = bisect_right(self.bins, person.age)
                        self.location_arrays['household'][i, age_bin-1] += 1
            elif location == 'school':
                for i in range(len(self.world.schools)):
                    for person in self.world.schools[i].people:
                        activities_left = self.policies.individual_policies.apply(
                            active_individual_policies,
                            person=person,
                            activities=activities,
                            days_from_start=0
                        )
                        if "primary_activity" in activities_left:
                            age_bin = bisect_right(self.bins, person.age)
                            self.location_arrays['school'][i, age_bin-1] += 1
            elif location == 'company':
                for i in range(len(self.world.companies)):   
                    for person in self.world.companies[i].people:
                        activities_left = self.policies.individual_policies.apply(
                            active_individual_policies,
                            person=person,
                            activities=activities,
                            days_from_start=0
                        )
                        if "primary_activity" in activities_left:
                            age_bin = bisect_right(self.bins, person.age)
                            self.location_arrays['company'][i, age_bin-1] += 1
        return None


    def calculate_interactions(self):
        "Create raw interaction matrix for all locations."
        for location in self.location_arrays.keys():
            for i in range(len(self.location_arrays[location])):
                self.interactions(
                    self.location_arrays[location][i],
                    self.interaction_arrays[location]
                )
        # Aiofe calls these interation_array_c
        self.interaction_arrays['household'] *= self.household_contact_matrix
        self.interaction_arrays['school'] *= self.school_contact_matrix
        self.interaction_arrays['company'] *= 4.8
        return None


    def interactions(self, location_row, interaction_array):
        "Creates raw age interaction matrix"
        # if only one person, no interaction
        if location_row.sum() <= 1:
            return
        else:
            nonzeros = np.nonzero(location_row)
            for idx, i in enumerate(nonzeros[0]):
                for j in nonzeros[0][idx+1:]:
                    interaction_array[j][i] += location_row[i]
                    interaction_array[i][j] += location_row[j]
                interaction_array[i][i] += location_row[i]-1 # Remove self-interactions


    def calculate_contact_matrix(self, interaction_array):
        "From BBC paper: c_ij = 0.5*(m_ij + m_ji * (w_i/w_j))"
        contact_matrix = np.zeros((19, 19), dtype=np.float)
        for i in range(0, 19):
            for j in range(0, 19):
                ni = self.age_array[i]
                nj = self.age_array[j]
                w = self.all_age_population[i] / self.all_age_population[j]
                tij = interaction_array[i][j]
                tji = interaction_array[j][i]
                contact_matrix[i][j] = 0.5*((tij/nj) + (tji/ni)*w)
        return contact_matrix


    def get_beta_reductions(self, date):
        beta_reductions = defaultdict(lambda: 1.0)
        for policy in self.policies.interaction_policies.get_active(
                date=date
            ):
            if policy.spec == 'social_distancing':
                beta_reductions_dict = policy.apply()
                for group in beta_reductions_dict:
                    beta_reductions[group] *= beta_reductions_dict[group]
        return beta_reductions


    def plot_contact_matrix(self, contact_matrix, location):
        fig, ax = plt.subplots()

        if location == 'household':
            vmax = 0.6
            ticks = np.linspace(0, vmax, 4+1, endpoint=True)
        else:
            vmax = 4
            ticks = range(0, vmax+1, 1)

        im = plt.imshow(contact_matrix,
                        cmap='coolwarm',
                        interpolation='nearest',
                        origin='lower',
                        vmin=0,
                        vmax=vmax
                        )

        ages = ['0-4', '5-9', '10-12', '13-14', '15-17', '18-19', '20-21', '22-24', '25-29', '30-34',
                '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74', '75+']

        ax.set_xticks(range(len(ages)))
        ax.set_yticks(range(len(ages)))
        ax.minorticks_off()
        ax.set_xticklabels(ages, fontsize='small', rotation='vertical')
        ax.set_yticklabels(ages, fontsize='small')
        cbar = plt.colorbar(im,
                     ax=ax, 
                     boundaries=np.linspace(0, vmax, 100),
                     ticks=ticks
                     )
        ax.set_xlabel("Participant age group")
        ax.set_ylabel("Contact age group")
        return fig
