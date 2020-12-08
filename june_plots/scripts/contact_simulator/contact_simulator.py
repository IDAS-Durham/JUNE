import psutil
import os
import copy
import pickle
import time
import datetime as dt
import yaml
from collections import Counter, defaultdict, ChainMap
from pathlib import Path
import logging

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors
import pandas as pd
import tables
import networkx as nx

from june.hdf5_savers import generate_world_from_hdf5
from june.groups.leisure import generate_leisure_for_config

from june.groups.group.interactive import InteractiveGroup
from june.groups.school import _get_contacts_in_school
from june.groups import InteractiveSchool, InteractiveCompany, InteractiveHousehold
from june.groups import Group, Subgroup

#from june.infection import HealthIndexGenerator
#from june.infection_seed import InfectionSeed, Observed2Cases
#from june.infection import InfectionSelector, HealthIndexGenerator
from june.groups.travel import Travel
from june.policy import Policies
from june.records import Record, RecordReader
from june.records.event_records_writer import EventRecord
from june.demography import Person

from june.mpi_setup import mpi_rank, mpi_size, mpi_comm, MovablePeople

from june import paths
from june.simulator import Simulator
from june.utils import random_choice_numba

default_simulation_config_path = (
    paths.configs_path / "config_example.yaml"
)
default_interaction_path = (
    paths.configs_path / "defaults/interaction/interaction.yaml"
)
default_bbc_data_path = (
    paths.data_path / "plotting/contact_tracking/bbc_cm.xls"
)

logger = logging.getLogger(__name__)

class ContactSimulator:

    def __init__(
        self, 
        simulator=None, 
        simulation_outputs_path=None,
        simulation_record=None,
        age_bins = {"5yr": np.arange(0,105,5)},
        contact_matrices=None,
        contact_tracker=False,
        simulation_days=7,
        interaction_type="1d",
        world_name=None,
    ):
        self.simulator = simulator

        self.simulation_record = simulation_record
        self.simulation_outputs_path = simulation_outputs_path
        self.simulation_outputs_path.mkdir(exist_ok=True, parents=True)
        self.age_bins = {"syoa": np.arange(0,101,1), **age_bins}
        self.contact_tracker = contact_tracker
        self.simulation_days = simulation_days
        self.world_name = world_name

        # Why not just use the simulator.interaction.contact_matrices?
        # Want to be absolutely sure that the alpha = 1.0, proportion_physical = [[0.]]...
        self.load_interactions() 
        if self.simulator is not None:
            self.world = self.simulator.world
            self.timer = self.simulator.timer

            self.supergroups = [
                self.world.care_homes,
                self.world.cinemas, 
                self.world.city_transports, 
                self.world.inter_city_transports, 
                self.world.companies, 
                self.world.groceries, 
                self.world.hospitals, 
                self.world.households, 
                self.world.pubs, 
                self.world.schools, 
                self.world.universities
            ]
            self.contact_types = (
                [supergroup[0].spec for supergroup in self.supergroups if len(supergroup) > 0]
                + ["care_home_visits", "household_visits"]
            )
            if interaction_type in ["1d", "network"]:
                self.interaction_type = interaction_type
            else:
                raise IOError(f"No interaction type {interaction_type}. Choose from",["1d", "network"])
            self.initalise_counter()        
            self.initalise_tracker()
            self.initialise_contact_matrices()
            self.hash_ages() # store all ages/ index to age bins in python dict for quick lookup.
                        
    def load_interactions(self, interaction_path=default_interaction_path):
        with open(interaction_path) as f:
            interaction_config = yaml.load(f, Loader=yaml.FullLoader)
            self.interaction_matrices = interaction_config["contact_matrices"]

            for spec in self.interaction_matrices.keys():
                contact_data = self.interaction_matrices.get(spec, {})
                matrix = np.array( contact_data.get("contacts", [[1]]) )
                characteristic_time = contact_data.get("characteristic_time", 8)
                proportion_physical = np.zeros(matrix.shape)
                alpha_physical = 1.0

                if spec == "school":
                    self.interaction_matrices["school"]["contacts"] = (
                        InteractiveSchool.get_processed_contact_matrix(
                            contact_matrix=matrix, 
                            alpha_physical=alpha_physical, 
                            proportion_physical=proportion_physical, 
                            characteristic_time=characteristic_time
                        )
                    )
                else:
                    self.interaction_matrices[spec]["contacts"] = (
                        InteractiveGroup.get_processed_contact_matrix(
                            contact_matrix=matrix, 
                            alpha_physical=alpha_physical, 
                            proportion_physical=proportion_physical, 
                            characteristic_time=characteristic_time
                        )
                    )

    def initialise_contact_matrices(self, include_global=False, matrix_types=None):
        self.contact_matrices = {}
        if matrix_types is None:
            matrix_types = [x for x in self.contact_types] # A horrible cheat for copy.
        if include_global:
            matrix_types.append("global")
        # For each type of contact matrix binning, eg BBC, polymod, SYOA...
        for bin_type, bins in self.age_bins.items():
            self.contact_matrices[bin_type] = {
                contact_type: np.zeros( (len(bins)-1,len(bins)-1) )
                for contact_type in matrix_types
            }

    def initalise_counter(self):
        self.counter = {spec: defaultdict(int) for spec in self.contact_types}

    def initalise_tracker(self):
        self.tracker = {spec: Counter() for spec in self.contact_types}

    def hash_ages(self):
        """store all ages and age_bin indexes in python dict for quick lookup"""
        self.age_data = {}
        for person in self.world.people:
            self.age_data[person.id] = {
                bin_type: np.digitize(person.age, bins)-1 
                for bin_type, bins in self.age_bins.items()
            }
            self.age_data[person.id]["age"] = person.age

    def export_import_traveller_age_data(self, travellers: MovablePeople):
        """The new parallel bit"""
        traveller_age_data = {rank: {} for rank in range(mpi_size)}
        for domain_id, domain_data in travellers.skinny_out.items():
            for group_spec, group_spec_data in domain_data.items():
                for group_id, group_data in group_spec_data.items():
                    for subgroup_id, subgroup_data in group_data.items():
                        for person_id in subgroup_data.keys():
                            traveller_age_data[domain_id][person_id] = (
                                self.age_data[person_id]
                            )

        reqs = []
        for rank in range(mpi_size):
            data = traveller_age_data[rank]
            if rank == mpi_rank:
                assert len(data) == 0
                continue
            reqs.append(mpi_comm.isend(data, dest=rank, tag=400))        

        traveller_dicts = []
        for rank in range(mpi_size):
            if rank == mpi_rank:
                continue
            traveller_dicts.append(mpi_comm.recv(source=rank, tag=400))
        
        for r in reqs:
            r.wait()

        collated_traveller_age_data = {
            k:v for d in traveller_dicts for k,v in d.items()
        }
        print(f"{mpi_rank} has imported {len(collated_traveller_age_data)} travellers")
        self.traveller_age_data = collated_traveller_age_data        

    def global_operations(self, people_from_abroad):
        pass

    def operations(
        self, people_from_abroad_dict, to_send_abroad, record_time_step=False
    ):  
        tick = time.time()               
        self.contact_pairs = []

        self.export_import_traveller_age_data(to_send_abroad)

        for supergroup in self.supergroups:
            if len(supergroup) == 0:
                continue
            spec = supergroup[0].spec
            for group in supergroup:
                if group.external:
                    continue
                people_from_abroad = people_from_abroad_dict.get(
                    group.spec, {}
                ).get(group.id, None)                    
                interactive_group = group.get_interactive_group(people_from_abroad)
                if interactive_group.size == 0:
                    continue
                self.modify_interactive_group(interactive_group, people_from_abroad)
                if self.interaction_type == "1d":
                    self.simulate_1d_contacts(interactive_group)
                elif self.interaction_type == "network":
                    raise NotImplementedError
                    #self.simulate_network_contacts(int_group)
            self.tracker[spec] = self.tracker[spec] + Counter(self.contact_pairs)
        tock = time.time()
        print(f"{mpi_rank} {self.timer.date} done in {(tock-tick)/60.} min")

        if record_time_step:
            self.record_output()

    def modify_interactive_group(self, interactive_group, people_from_abroad):
        """"""
        people_from_abroad = people_from_abroad or {}

        interactive_group.subgroup_member_ids = []
        for subgroup_index, subgroup in enumerate(interactive_group.group.subgroups):
            subgroup_size = len(subgroup.people)
            if subgroup.subgroup_type in people_from_abroad:
                people_abroad_data = people_from_abroad[subgroup.subgroup_type]
                people_abroad_ids = people_abroad_data.keys()
                subgroup_size += len(people_abroad_ids)
            else:
                people_abroad_data = None
                people_abroad_ids = []
             
            this_subgroup_ids = [p.id for p in subgroup.people] + list(people_abroad_ids)
            interactive_group.subgroup_member_ids.append(this_subgroup_ids)

        if interactive_group.group.spec == "school":
            if (len(interactive_group.subgroup_member_ids) == 
                len(interactive_group.school_years) + 2):
                assert len(interactive_group.subgroup_member_ids[-1]) == 0
                del interactive_group.subgroup_member_ids[-1]
            else:
                print("you can probably remove this 'if school' statement in modify_interactive_group")

    def simulate_1d_contacts(self, interactive_group: InteractiveGroup):
        """get the total number of contacts each person has in a simulation.
            Estimate contact matrices by choosing the the allotted number of people
            per subgroup.
        """                      

        all_members = [ 
            np.array(subgroup) for subgroup in interactive_group.subgroup_member_ids
        ] # it's better to use arrays for np choice later on.

        spec = interactive_group.spec

        for subgroup_type, subgroup_ids in enumerate(interactive_group.subgroup_member_ids):
            #------some set up that it's faster to do only once.
            if len(subgroup_ids) == 0:
                continue
            # lists of probablilites to do the fast random choice later on,
            # account for fact that there's 1 less contact in your own subgroup. ie, you!
            prob_lists = []
            for ii, m in enumerate(interactive_group.subgroup_member_ids):
                len_subgroup = len(m)
                if subgroup_type == ii:
                    len_subgroup -= 1                     
                if len_subgroup > 0:
                    prob_lists.append(np.full(len_subgroup, 1./len_subgroup))
                else:
                    prob_lists.append(np.array([]))
            # how many contacts will a person in this subgroup have with each other subgroup?
            contacts_per_subgroup = self.get_contacts_per_subgroup(
                subgroup_type, interactive_group
            )
            # sum the number of contacts, no contacts if you're the only one in your subgroup.
            total_contacts = 0
            for ii, (m, c) in enumerate(
                zip(interactive_group.subgroup_member_ids, contacts_per_subgroup)
            ):
                len_subgroup = len(m)
                if ii == subgroup_type:
                    len_subgroup -= 1
                total_contacts += c*(len_subgroup > 0)

            for pid in subgroup_ids:
                subgroup_members = [x for x in all_members] 
                subgroup_members[subgroup_type] = np.setdiff1d(
                    all_members[subgroup_type], np.array([pid]), assume_unique=True
                ) # make a copy of subgroup_members, but remove yourself. # this is faster than "x for x in subgroup if x != pid" ??
                assert len(subgroup_members[subgroup_type]) == len(all_members[subgroup_type])-1
                self.counter[spec][pid] += total_contacts
                potential_contacts = [ # do this inside the loop as it should be different for every person.
                    self._random_round(c)*( len(m) > 0 ) 
                    for c,m in zip(contacts_per_subgroup, subgroup_members)
                ]
                #contact_ids = [ # I think this version is much slower?
                #    cid for members, x in zip(subgroup_members, potential_contacts) for cid in np.random.choice(members, x)
                #]
                contact_ids = [
                    random_choice_numba(members, probs)
                    for members, probs, c in zip(subgroup_members, prob_lists, potential_contacts)
                    for _ in range(c)
                ]
                self.increment_contact_matrices(pid, contact_ids, spec=spec)
                if self.contact_tracker:
                    self.contact_pairs.extend([
                        (pid, cid) for cid in contact_ids
                    ])

    @staticmethod
    def _random_round(x):
        """round float to integer randomly with probability x%1.
            eg. round 3.7 to 4 with probability 70%, else round to 3.
        """
        return int(np.floor(x+np.random.random()))

    def get_active_subgroup(self, person: Person):
        """maybe not so useful here, but could be for others"""
        active_subgroups = []
        subgroup_ids = []
        for subgroup in person.subgroups.iter():
            if subgroup is None or subgroup.group.spec == "commute_hub":
                continue
            if subgroup.external:
                continue
            if person in subgroup.people:
                subgroup_id = f"{subgroup.group.spec}_{subgroup.group.id}"
                if subgroup_id in subgroup_ids:
                    # gotcha: if you're receiving household visits, then you're active in residence
                    # and leisure -- but they are actually the same location...
                    continue
                active_subgroups.append( subgroup )
                subgroup_ids.append( subgroup_id )

        if len(active_subgroups) == 0:
            print(f"CHECK: person {person.id} active in NO subgroups!?")
            return None
        elif len(active_subgroups) > 1:
            print(f"CHECK: person {person.id} is in more than one subgroup!?")
            return None
        else:
            active_subgroup = active_subgroups[0]
        return active_subgroup

    def get_contacts_per_subgroup(self, subgroup_type, interactive_group: InteractiveGroup):
        """"""
        spec = interactive_group.group.spec
        matrix = self.interaction_matrices[spec]["contacts"]
        delta_t = self.timer.delta_time.seconds / 3600.
        factor = delta_t / 24.

        contacts_per_subgroup = [
            interactive_group.get_contacts_between_subgroups(
                matrix, subgroup_type, other_subgroup
            ) * factor for other_subgroup, _ in enumerate(interactive_group.subgroup_member_ids)
        ]
        return contacts_per_subgroup

    def increment_contact_matrices(self, pid, contact_ids, spec):
        for bin_type in self.age_bins.keys():
            if pid in self.age_data:
                age_idx = self.age_data[pid][bin_type]
            elif pid in self.traveller_age_data:
                age_idx = self.traveller_age_data[pid][bin_type]
            contact_age_idxes = []
            for cid in contact_ids:
                if cid in self.age_data:
                    contact_age_idxes.append(self.age_data[cid][bin_type])
                elif cid in self.traveller_age_data:
                    contact_age_idxes.append(self.traveller_age_data[cid][bin_type])
                else:
                    print(mpi_rank, group.spec, pid, cid, subgroup_members, contact_ids)
                    raise ValueError(f"{mpi_rank}: No key {cid}")

            bincount = np.bincount(
                contact_age_idxes, minlength=len(self.age_bins[bin_type])-1
            )
            self.contact_matrices[bin_type][spec][age_idx,:] += bincount         

    def record_output(self):
        if mpi_rank == 0:
            logger.info(f"record output at {self.timer.date}")
        for contact_type in self.contact_types:
            if len(self.counter[contact_type]) > 0: # ie. no one in pub in sleep timestep.
                counter_person_ids = list(self.counter[contact_type].keys())
                contact_counts = list(self.counter[contact_type].values())
                self.simulation_record.accumulate(
                    table_name="counter",
                    contact_type=contact_type,
                    person_ids=counter_person_ids,
                    num_contacts=contact_counts
                )
            if len(self.tracker[contact_type]) > 0:
                arr = np.array(list(self.tracker[contact_type].keys()))
                tracker_person_ids = arr[:,0]
                tracker_contact_ids = arr[:,1]
                tracker_count = list(self.tracker[contact_type].values())
                self.simulation_record.accumulate(
                    table_name="tracker",
                    contact_type=contact_type,
                    person_ids=tracker_person_ids,
                    contact_ids=tracker_contact_ids,
                    tracker_count=tracker_count
                )
        self.simulation_record.time_step(self.timer.date, ["counter", "tracker"])

        # Reset the counters for the next interval...
        self.initalise_counter()
        self.initalise_tracker()

    def save_auxilliary_data(self, overwrite=False):
        """Dump the raw contact_matrices, 
            age_bins, simulation_days into pkl file, path defined on initialisation.
            if overwrite is False, and self.pickle_path exists,
            try pickle_1.pkl, pickle_2.pkl, etc.
        """
        output = {
            #"age_data": self.age_data,
            "age_bins": self.age_bins,
            "simulation_days": self.simulation_days,
            "contact_matrices": self.contact_matrices,
        }
        aux_out_path = self.simulation_outputs_path / f"output.{mpi_rank:03d}.pkl"
        with open(aux_out_path,"wb+") as pkl:
            pickle.dump(output, pkl)

    ### some functions for processing.

    def collate_results(self):
        """ This should be called for mpi_rank==0 only...  """
        matrix_types = [
            "care_home", "cinema", "city_transport", "inter_city_transport", "company", 
            "grocery", "hospital", "household", "pub", "school", "university", 
            "care_home_visits", "household_visits"
        ]
        self.initialise_contact_matrices(
            include_global=True, matrix_types=matrix_types
        )
        output_files = sorted(self.simulation_outputs_path.glob("output.*.pkl"))
        for ii, pkl_path in enumerate(output_files):
            with open(pkl_path, "rb") as pkl:
                f = pickle.load(pkl)
                for bin_type in self.age_bins.keys():
                    for contact_type in matrix_types:
                        if contact_type not in f["contact_matrices"][bin_type].keys():
                            continue               
                        self.contact_matrices[bin_type][contact_type] = (
                            self.contact_matrices[bin_type][contact_type] + 
                            f["contact_matrices"][bin_type][contact_type]
                        )
                        self.contact_matrices[bin_type]["global"] = (
                            self.contact_matrices[bin_type]["global"] + 
                            f["contact_matrices"][bin_type][contact_type]
                        )
        combined_cm_path = self.simulation_outputs_path / "contact_matrices.pkl"
        #with open(combined_cm_path, "wb+") as pkl:
        #    pickle.dump(self.contact_matrices, pkl)

        self.read = RecordReader(
            self.simulation_outputs_path, 
            record_name="simulation_record.h5"
        )
        self.population = self.read.table_to_df("population")
        drop_cols = [
            'primary_activity_id', 
            'residence_id', 
            'area_id', 
            #'primary_activity_type'
        ]

        print("LEN POP IDs", len(self.population.index.unique()))
        self.population.drop(drop_cols, axis=1, inplace=True)
        self.contacts = self.read.table_to_df("counter", index="id")
        print("LEN CONTACTs IDs", len(self.contacts.index))
        self.contacts.set_index(
            ["contact_type", "timestamp"], append=True, inplace=True
        )
        print(self.contacts)

    def get_age_profiles(self, age_data):
        self.age_profiles = {}
        for bin_type,bins in self.age_bins.items():
            hist, edges = np.histogram(age_data, bins=bins)
            self.age_profiles[bin_type] = hist
        combined_age_profiles_path = self.simulation_outputs_path / "age_profiles.pkl"
        #with open(combined_age_profiles_path, "wb+") as pkl:
        #    pickle.dump(self.age_profiles, pkl)

    def convert_contacts(self):
        #for idx, df in self.contacts.groupby(["id", "contact_type"]):
        #    print(idx, df)

        all_contacts = self.contacts.groupby(["id", "contact_type"]).sum()
        df = all_contacts["num_contacts"].unstack(
            level="contact_type", fill_value=0.
        )

        pd.set_option('max_rows', 100)
        pd.set_option('max_columns', 30)
        df = df.join(
            self.population, on="id"
        )
        for bin_type, bins in self.age_bins.items():
            bins_idx = f"{bin_type}_idx"
            df[bins_idx] = np.digitize(df["age"], bins) - 1
        
        self.contacts_df = df
        #print("contacts len", len(self.contacts_df[self.contacts_df["company"] > 0]))
        #print(self.contacts_df[self.contacts_df["company"] > 0].head(n=10))

    def calc_average_contacts(self):
        """ average contacts over age bins. Returns a dict of {bin_type: df} -- where df is
            has rows of age bins, columns of supergroup -- for each set of bins in age_bins"""
        self.average_contacts = {}
        for bin_type in self.age_bins.keys():
            bins_idx = f"{bin_type}_idx"
            self.average_contacts[bin_type] = (
                self.contacts_df.groupby(self.contacts_df[bins_idx]).mean() / self.simulation_days
            )
            #print(self.average_contacts[bin_type])
        combined_ave_contacts_path = self.simulation_outputs_path / "average_contacts.pkl"
        #with open(combined_ave_contacts_path, "wb+") as pkl:
        #    pickle.dump(self.average_contacts, pkl)

    def normalise_contact_matrices(self, set_on_copy=True):
        if set_on_copy:
            self.normalised_contact_matrices = copy.deepcopy(self.contact_matrices)        
        for bin_type in self.age_bins.keys():
            matrices = self.contact_matrices[bin_type]
            age_profile = self.age_profiles[bin_type]
            
            for contact_type, mat in matrices.items():
                if contact_type == "age_bins":
                    continue
                mat = mat / (self.simulation_days*age_profile[np.newaxis, :])
                norm_mat = np.zeros( mat.shape )
                for i,row in enumerate(norm_mat):
                    for j,col in enumerate(norm_mat.T):
                        norm_factor = age_profile[i]/age_profile[j]
                        norm_mat[i,j] = (
                            0.5*(mat[i,j] + mat[j,i]*norm_factor)
                        )
                norm_mat[ norm_mat == 0. ] = np.nan
                if set_on_copy:
                    self.normalised_contact_matrices[bin_type][contact_type] = norm_mat
                else:
                    self.contact_matrices[bin_type][contact_type] = norm_mat

    def save_collated_results(self, collated_results_name="collated_results.pkl"):
        collated_results = {
            "raw_contact_matrices": self.contact_matrices,
            "normalised_contact_matrices": self.normalised_contact_matrices,
            "age_profiles": self.age_profiles,
            "average_contacts": self.average_contacts,
            "age_bins": self.age_bins,
            "simulation_days": self.simulation_days,
        }
        collated_results_path = self.simulation_outputs_path / collated_results_name
        with open(collated_results_path, "wb+") as pkl:
            pickle.dump(collated_results, pkl)

    def process_results(self):
        """convenience method. calls convert_dict_to_df(), calc_age_profiles(), 
        calc_average_contacts(), normalise_contact_matrices()"""
        self.collate_results()
        self.get_age_profiles(self.population["age"])
        self.convert_contacts()
        self.calc_average_contacts()
        self.normalise_contact_matrices(set_on_copy=True)
        self.save_collated_results()

    def load_results(self, collated_results_name="collated_results.pkl"):
        collated_results_path = self.simulation_outputs_path / collated_results_name
        with open(collated_results_path, "rb") as pkl:
            dat = pickle.load(pkl)            
            self.age_profiles = dat["age_profiles"]
            self.age_bins = dat["age_bins"]
            self.contact_matrices = dat["raw_contact_matrices"]
            self.average_contacts = dat["average_contacts"]
        self.normalise_contact_matrices()
            

    def load_real_contact_data(
        self, **kwargs
    ):
        self.real_contact_matrices = {}
        self.real_contact_data = {}
        self.load_bbc_data(**kwargs)

    def load_bbc_data(
        self,
        bbc_data_path=default_bbc_data_path,
        bbc_mapping={
            "home": "household", "work": "company", "school": "school", "other": "other"
        },
        **kwargs
    ):
        bbc_contact_matrices = {}
        bbc_contact_data = {}

        for location, value in bbc_mapping.items():
            sheet_name = f"all_{location}"
            mat = pd.read_excel(
                bbc_data_path, sheet_name=sheet_name, index_col = 0
            )
            rename_cols = {"75+": "75-100"}
            for col in mat.columns:
                try:
                    d = pd.to_datetime(col)
                    rename_cols[col] = f"{d.day}-{d.month}"
                except:
                    pass
            mat.rename(rename_cols, axis=0, inplace=True)
            mat.rename(rename_cols, axis=1, inplace=True)
            # Don't think we want the .T ...
            bbc_contact_matrices[value] = mat.values
            bbc_contact_data[value] = np.sum(mat.values, axis=0)
        bbc_contact_data["global"] = sum([arr for arr in bbc_contact_data.values()])
        # just use the last matrix
        bbc_contact_data["age_min"] = [int(col.split("-")[0]) for col in mat.columns]
        bbc_contact_data["age_max"] = [int(col.split("-")[1]) for col in mat.columns]
        self.real_contact_matrices["bbc"] = bbc_contact_matrices
        self.real_contact_data["bbc"] = bbc_contact_data

    def _plot_real_data(self, ax, data, contact_type="global", errorbar=True, **kwargs):
        endpoints = np.array(
            [x for x in data["age_min"]] + [data["age_max"][-1]]
        )
        mids = 0.5*(endpoints[:-1] + endpoints[1:])
        widths = 0.5*(endpoints[1:] - endpoints[:-1])
        ydat = data[contact_type]
        if errorbar:
            ax.errorbar(mids, ydat, xerr=widths, **kwargs)
        else:
            ax.plot(mids, ydat, **kwargs)

    def plot_group_contacts(
        self, bin_type="bbc", contact_types=None, plot_real_data=True
    ):
        f, ax = plt.subplots()
        average_contacts = self.average_contacts[bin_type]
        bins = self.age_bins[bin_type]
        mids = 0.5*(bins[:-1]+bins[1:])
        widths = (bins[1:]-bins[:-1])
        real_plotted=False
        real_kwargs = {"marker":"x", "ms":5, "lw":1, "ls":"--",}
        for ii, contact_type in enumerate(contact_types):
            if contact_type not in average_contacts.columns:
                print(f"No contact_type {contact_type}")
                continue
            ax.plot(
                mids, average_contacts[contact_type], 
                label=contact_type, color=f"C{ii%6}"
            )

            if plot_real_data:
                if "real_contact_data" in self.__dict__:                    
                    for jj, (key, data) in enumerate(self.real_contact_data.items()):
                        self._plot_real_data(
                            ax, data, contact_type=contact_type, errorbar=False,
                            color=f"C{ii%6}", **real_kwargs, 
                        )
                    real_plotted=True
            else:
                print("\"Real\" data not loaded - do contact_tracker.load_contact_data() before plotting.")
        
        ax2 = ax.twinx()
        ax2.plot((0,0),(0,0),color="grey", label="JUNE")
        ax2.plot((0,0),(0,0), color="grey", **real_kwargs, label=bin_type)
        ax2.legend(bbox_to_anchor=(0.6,1.0))
        ax.legend()
        ax.set_xlim(bins[0], bins[-1])
        ax.set_xlabel('Age')
        ax.set_ylabel('average contacts per day in group')
        #f.subplots_adjust(top=0.9)
        return ax 

    def plot_stacked_contacts(
        self, bin_type="syoa", contact_types=None, plot_real_data=True
    ):
        f, ax = plt.subplots()
        average_contacts = self.average_contacts[bin_type]
        bins = self.age_bins[bin_type]
        lower = np.zeros(len(bins)-1)
        mids = 0.5*(bins[:-1]+bins[1:])
        widths = (bins[1:]-bins[:-1])
        plotted = 0

        if contact_types is None:
            contact_types = self.contact_types
        for ii, contact_type in enumerate(contact_types):
            if contact_type not in average_contacts.columns:
                print(f"No contact_type {contact_type}")
                continue
            if contact_type == "global":
                continue
            hatch = "/" if plotted > 6 else None
            heights = average_contacts[contact_type]            
            label = " ".join(x for x in contact_type.split("_")) # Avoids idiotic latex error.
            ax.bar(
                mids, heights, widths, bottom=lower,
                hatch=hatch, label=label
            )
            plotted += 1
            lower = lower + heights

        if plot_real_data:
            if "real_contact_data" in self.__dict__:
                real_kwargs = {"marker":"x", "ms":5, "lw":1, "color":"k"}
                line_styles=["-","--",":"]
                #if type(self.contact_data) is dict:
                for ii, (key, data) in enumerate(self.real_contact_data.items()):
                    self._plot_real_data(
                        ax, data, contact_type="global", label=key, **real_kwargs, ls=line_styles[ii]
                    )
            else:
                print("\"Real\" data not loaded - do contact_tracker.load_contact_data() before plotting.")

        ax.set_xlim(bins[0], bins[-1])
        ax.legend(bbox_to_anchor = (0.5,1.02), loc='lower center', ncol=3)
        ax.set_xlabel('Age')
        ax.set_ylabel('average contacts per day')
        #f.subplots_adjust(top=0.9)
        return ax 

    def plot_contact_matrix(
        self, bin_type="bbc", contact_type="school", real=False, ratio_with_real=False, **kwargs
    ):
        bins = self.age_bins[bin_type]
        if len(bins) < 25:
            labels = [
                f"{low}-{high-1}" for low,high in zip(bins[:-1], bins[1:])
            ]
        else:
            labels = None

        plot_kwargs = {}
        if ratio_with_real:
            matrix_type=f"ratio JUNE/{bin_type.upper()}"
            model_mat = self.normalised_contact_matrices[bin_type][contact_type]
            real_mat = self.real_contact_matrices[bin_type][contact_type]
            mat = model_mat / real_mat
            vmin, vmax= 0.2, 3.0
            plot_kwargs["norm"]=colors.LogNorm(vmin=vmin, vmax=vmax)
            
        else:
            if real:
                matrix_type = bin_type.upper()
                mat = self.real_contact_matrices[bin_type][contact_type]
            else:
                matrix_type = "JUNE"
                mat = self.normalised_contact_matrices[bin_type][contact_type]
            plot_kwargs["vmin"]=0.0
            plot_kwargs["vmax"]=1.0

        plot_kwargs.update(kwargs)

        cmap = copy.copy(cm.get_cmap('RdYlBu_r'))
        cmap.set_bad(color="lightgrey")
        plot_kwargs["cmap"] = cmap

        f, ax = plt.subplots()
        im = ax.imshow(mat, origin='lower', **plot_kwargs)
        if labels is not None:
            ax.set_xticks(np.arange(len(mat)))
            ax.set_xticklabels(labels,rotation=90)
            ax.set_yticks(np.arange(len(mat)))
            ax.set_yticklabels(labels)
        f.colorbar(im)

        if self.world_name is not None:
            world_name = self.world_name.split("_")[0].capitalize()
            title = f"{contact_type} ({world_name}, {matrix_type})"
        else:
            title = f"{contact_type} ({matrix_type})"
        ax.set_title(title)
        ax.set_xlabel("Participant age group")
        ax.set_ylabel("Contact age group")
        return ax

    def make_plots(
        self, 
        save_dir,
        relevant_contact_types=["household", "school", "company"],
        relevant_bin_types=["bbc", "syoa"],
        ratio_bin_types = ["bbc"],
        color_palette=None
    ):
        contact_types = [
            "household", "school", "grocery", "household_visits", "pub", "university", 
            "company", "city_transport", "inter_city_transport", "care_home", 
            "care_home_visits", "cinema", "hospital",
        ]

        self.load_real_contact_data()
        save_dir.mkdir(exist_ok=True, parents=True)

        limits = {
            "household": {"vmin": 0., "vmax": 1.},
            "school": {"vmin": 0., "vmax": 3.5},
            "company": {"vmin": 0., "vmax": 1.0}
        }
            

        groups_plot = self.plot_group_contacts(
            contact_types=relevant_contact_types+["global"]
        )
        groups_plot.plot()
        plt.savefig(save_dir / f"bbc_group_contacts.png", dpi=150, bbox_inches='tight')
        for rbt in relevant_bin_types:
            stacked_contacts_plot = self.plot_stacked_contacts(
                bin_type=rbt, contact_types=contact_types
            )
            stacked_contacts_plot.plot()
            plt.savefig(save_dir / f"{rbt}_stacked_contacts.png", dpi=150, bbox_inches='tight')
            mat_dir = save_dir / f"{rbt}_matrices"
            mat_dir.mkdir(exist_ok=True, parents=True)
            
            for rct in relevant_contact_types:
                mat_plot = self.plot_contact_matrix(
                    bin_type=rbt, contact_type=rct, **limits.get(rbt, {})
                )
                mat_plot.plot()
                plt.savefig(mat_dir / f"{rct}.png", dpi=150, bbox_inches='tight')     
                if rbt not in ratio_bin_types:
                    continue
                real_plot = self.plot_contact_matrix(
                    bin_type=rbt, contact_type=rct, real=True, **limits.get(rbt, {})
                )
                real_plot.plot()
                plt.savefig(mat_dir / f"{rct}_real.png", dpi=150, bbox_inches='tight')   
                ratio_plot = self.plot_contact_matrix(
                    bin_type=rbt, contact_type=rct, ratio_with_real=True
                )
                ratio_plot.plot()
                plt.savefig(mat_dir / f"{rct}_ratio.png", dpi=150, bbox_inches='tight')
            
if __name__ == "__main__":
    print("Use simulation_plotter.")



