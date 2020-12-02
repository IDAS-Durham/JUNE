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
#import seaborn as sns

#from june_runs import Runner

#default_run_config_path = (
#    "/home/aidan/covid/june_runs/example_run/runs/run_000/parameters.json"#"/home/aidan/covid/june_runs/configuration/run_sets/quick_examples/local_example.yaml"
#)

from june.hdf5_savers import generate_world_from_hdf5
from june.groups.leisure import generate_leisure_for_config
from june.groups.group import Group, Subgroup
from june.interaction import Interaction, InteractiveGroup
from june.interaction.interaction import _get_contacts_in_school
from june.infection import HealthIndexGenerator
from june.infection_seed import InfectionSeed, Observed2Cases
from june.infection import InfectionSelector, HealthIndexGenerator
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

        self.load_interactions()
        if self.simulator is not None:
            self.world = self.simulator.world
            self.timer = self.simulator.timer

            self.group_types = [
                #self.world.care_homes,
                #self.world.cinemas, 
                #self.world.city_transports, 
                #self.world.inter_city_transports, 
                #self.world.companies, 
                #self.world.groceries, 
                #self.world.hospitals, 
                #self.world.households, 
                #self.world.pubs, 
                self.world.schools, 
                #self.world.universities
            ]
            self.contact_types = (
                [groups[0].spec for groups in self.group_types if len(groups) > 0]
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

            self.interaction_matrices["school"]["contacts"] = (
                Interaction.adapt_contacts_to_schools(
                    self.interaction_matrices["school"]["contacts"],
                    self.interaction_matrices["school"]["xi"],
                    age_min=0,
                    age_max=20,
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

    @staticmethod
    def _random_round(x):
        """round float to integer randomly with probability x%1.
            eg. round 3.7 to 4 with probability 70%, else round to 3.
        """
        return int(np.floor(x+np.random.random()))
        """
        f = x % 1
        if np.random.uniform(0,1,1) < f:
            return int(x)+1
        else:
            return int(x)"""

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

    def get_contacts_per_subgroup(self, subgroup_type, group: InteractiveGroup):
        """
        Get contacts that a person of subgroup type `subgroup_type` will have with each of the other subgroups,
        in a given group.
        eg. household has subgroups[subgroup_type]: kids[0], young_adults[1], adults[2], old[3]
        subgroup_type is the integer representing the type of person you're wanting to look at.
        
        """ 
        spec = group.spec
        matrix = self.interaction_matrices[spec]["contacts"]
        delta_t = self.timer.delta_time.seconds / 3600.
        characteristic_time = self.interaction_matrices[spec]["characteristic_time"]
        factor = delta_t / characteristic_time
        if spec == "household":
            factor = delta_t / characteristic_time
            contacts_per_subgroup = [
                matrix[subgroup_type][ii]*factor 
                for ii, _ in enumerate(group.subgroup_member_ids) # this is a list of lists.
            ]
        elif spec == "school":
            contacts_per_subgroup = [
                _get_contacts_in_school(matrix, group.school_years, subgroup_type, other_type)
                if len(subgroup_ids) > 0 else 0 for 
                other_type, subgroup_ids in enumerate(group.subgroup_member_ids)
            ]
        elif spec == "care_home":
            group_timings = [8.,24.,3.] # [wk,res,vis]
            factors = [
                min(time, group_timings[subgroup_type]) / characteristic_time
                for time in group_timings
            ]
            contacts_per_subgroup = [
                matrix[subgroup_type][ii]*factors[ii] for 
                ii, _ in enumerate(group.subgroup_member_ids) # this is a list of lists.
            ]
        else:
            contacts_per_subgroup = [
                matrix[subgroup_type][ii]*factor
                for ii, _ in enumerate(group.subgroup_member_ids) # this is a list of lists.
            ]
        return contacts_per_subgroup

    def simulate_1d_contacts(self, group: InteractiveGroup):
        """get the total number of contacts each person has in a simulation.
            Estimate contact matrices by choosing the the allotted number of people
            per subgroup.
        """
        
        all_members = [ 
            np.array([x for x in subgroup]) 
            for subgroup in group.subgroup_member_ids
        ]

        for subgroup_type, subgroup_ids in enumerate(group.subgroup_member_ids):    
            prob_lists = []
            for ii, m in enumerate(group.subgroup_member_ids):
                len_subgroup = len(m) - (subgroup_type == ii)
                if len_subgroup > 0:
                    prob_lists.append(np.full(len_subgroup, 1./len_subgroup))
                else:
                    prob_lists.append(np.array([]))           
            for pid in subgroup_ids:
                t1 = time.time()
                subgroup_members = [x for x in all_members]
                subgroup_members[subgroup_type] = np.setdiff1d(
                    all_members[subgroup_type], np.array([pid]), assume_unique=True
                )
                t2 = time.time()
                print(group.spec, id(group), "do copy", f"{(t2-t1)*1000:.4f}")
                #t1 = time.time()
                #subgroup_members[subgroup_type].remove(pid)
                #t2 = time.time()
                #print(group.spec, id(group), "pop", f"{(t2-t1)*1000:.4f}")
                t1 = time.time()
                contacts_per_subgroup = self.get_contacts_per_subgroup(
                    subgroup_type, group
                )
                t2 = time.time() 
                print(group.spec, id(group), "get_contacts", f"{(t2-t1)*1000:.4f}")
                #t1 = time.time()
                total_contacts = sum([
                    c for c,m in zip(contacts_per_subgroup, subgroup_members) if len(m) > 0
                ])
                t2 = time.time()
                print(group.spec, id(group), "total_contacts", f"{(t2-t1)*1000:.4f}")
                #t1 = time.time()
                self.counter[group.spec][pid] += total_contacts
                int_contacts = [
                    self._random_round( x ) for x in contacts_per_subgroup
                ]
                #t2 = time.time()
                #print(group.spec, id(group), "random_round", f"{(t2-t1)*1000:.4f}")
                #t1 = time.time()
                potential_contacts = [
                    c if len(m) > 0 else 0 for c,m in zip(int_contacts, subgroup_members)
                ]
                #t2 = time.time()
                #print(group.spec, id(group), "potential contacts", f"{(t2-t1)*1000:.4f}")
                #t1 = time.time()
                #contact_ids = [ # I think this version is much slower?
                #    cid
                #    for members, x in zip(subgroup_members, potential_contacts)
                #    for cid in np.random.choice(members, x)
                #]
                contact_ids = [
                    #members[np.random.randint(0, len(members), c)] 
                    random_choice_numba(members, probs)
                    for members, probs, c in zip(subgroup_members, prob_lists, potential_contacts)
                    for _ in range(c)
                ]
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
                    #self.contact_matrices[bin_type]["global"][age_idx,:] += bincount
                    self.contact_matrices[bin_type][group.spec][age_idx,:] += bincount 
                if self.contact_tracker:
                    self.contact_pairs.extend([
                        (pid, cid) for cid in contact_ids
                    ])

    def operations(
        self, people_from_abroad_dict, to_send_abroad, record_time_step=False
    ):  
        
        tick = time.time()               
        self.contact_pairs = []

        self.export_import_traveller_age_data(to_send_abroad)

        for group_type in self.group_types:
            if len(group_type) == 0:
                continue
            group_spec = group_type[0].spec
            for group in group_type:
                if group.external:
                    continue
                if (
                    group.spec in people_from_abroad_dict
                    and group.id in people_from_abroad_dict[group.spec]
                ):
                    foreign_people = people_from_abroad_dict[group.spec][group.id]
                else:
                    foreign_people = None

                int_group = InteractiveGroup(
                    group, foreign_people, save_subgroup_ids=True
                )
                if int_group.size == 0:
                    continue
                if self.interaction_type == "1d":
                    self.simulate_1d_contacts(int_group)
                elif self.interaction_type == "network":
                    self.simulate_network_contacts(int_group)
            self.tracker[group_spec] = self.tracker[group_spec] + Counter(self.contact_pairs)
        tock = time.time()
        print(f"{mpi_rank} {self.timer.date} done in {(tock-tick)/60.} min")

        if record_time_step:
            self.record_output()

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
        with open(combined_cm_path, "wb+") as pkl:
            pickle.dump(self.contact_matrices, pkl)

        self.read = RecordReader(
            self.simulation_outputs_path, 
            record_name="simulation_record.h5"
        )
        self.population = self.read.table_to_df("population")
        drop_cols = [
            'primary_activity_id', 
            'residence_id', 
            'area_id', 
            'primary_activity_type'
        ]
        self.population.drop(drop_cols, axis=1, inplace=True)
        self.contacts = self.read.table_to_df("counter", index="id")
        self.contacts.set_index(
            ["contact_type", "timestamp"], append=True, inplace=True
        )

    def get_age_profiles(self, age_data):
        self.age_profiles = {}
        for bin_type,bins in self.age_bins.items():
            hist, edges = np.histogram(age_data, bins=bins)
            self.age_profiles[bin_type] = hist
        combined_age_profiles_path = self.simulation_outputs_path / "age_profiles.pkl"
        with open(combined_age_profiles_path, "wb+") as pkl:
            pickle.dump(self.age_profiles, pkl)

    def convert_contacts(self):
        all_contacts = self.contacts.groupby(["id", "contact_type"]).sum()
        self.contacts_df = all_contacts["num_contacts"].unstack("contact_type", fill_value=0)
        self.contacts_df = self.contacts_df.join(
            self.population, on="id"
        )
        for bin_type, bins in self.age_bins.items():
            bins_idx = f"{bin_type}_idx"
            self.contacts_df[bins_idx] = np.digitize(self.contacts_df["age"], bins) - 1

    def calc_average_contacts(self):
        """ average contacts over age bins. Returns a dict of {bin_type: df} -- where df is
            has rows of age bins, columns of group_type -- for each set of bins in age_bins"""
        self.average_contacts = {}
        for bin_type in self.age_bins.keys():
            bins_idx = f"{bin_type}_idx"
            self.average_contacts[bin_type] = (
                self.contacts_df.groupby(self.contacts_df[bins_idx]).mean() / self.simulation_days
            )
        combined_ave_contacts_path = self.simulation_outputs_path / "average_contacts.pkl"
        with open(combined_ave_contacts_path, "wb+") as pkl:
            pickle.dump(self.average_contacts, pkl)

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

    def load_results(self):
        combined_age_profiles_path = self.simulation_outputs_path / "age_profiles.pkl"
        with open(combined_age_profiles_path, "rb") as pkl:
            self.age_profiles = pickle.load(pkl)
        combined_cm_path = self.simulation_outputs_path / "contact_matrices.pkl"
        with open(combined_cm_path, "rb") as pkl:
            self.contact_matrices = pickle.load(pkl)  
        self.normalise_contact_matrices()
        combined_ave_contacts_path = self.simulation_outputs_path / "average_contacts.pkl"
        with open(combined_ave_contacts_path, "rb") as pkl:
            self.average_contacts = pickle.load(pkl)       

    @staticmethod
    def _read_contact_data(contact_data_path):
        contact_data = pd.read_csv(contact_data_path)
        important_cols = np.array(["age_min", "age_max", "contacts"])
        mask = np.array([col in contact_data.columns for col in important_cols])
        if any(mask):
            print(f"{contact_data_path} missing col(s) {important_cols[mask]}")
        return contact_data

    """
    def load_real_contact_data(
        self,
        contact_data_paths=default_contact_data_paths
    ):
        '''
        Parameters
        ----------
        contact_data_path
            either the path to a csv containing "real" data, or a dict of "data_name": path
            for plotting several sets of real data. eg. {"bbc_data": "/path/to/data"}.
            CSV(s) should contain at least columns: age_min, age_max, contacts.
        '''
        if type(contact_data_paths) is dict:
            contact_data = {}
            for key, data_path in contact_data_paths.items():
                contact_data[key] = self._read_contact_data(data_path)
        else:
            contact_data = self._read_contact_data(contact_data_paths)
        self.contact_data = contact_data       """

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
        print(bbc_contact_data)
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
        plotted = 0

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
                    real_kwargs = {"marker":"x", "ms":5, "lw":1, "ls":"--",}
                    for jj, (key, data) in enumerate(self.real_contact_data.items()):
                        self._plot_real_data(
                            ax, data, contact_type=contact_type, errorbar=False,
                            color=f"C{ii%6}", **real_kwargs, 
                        )
            else:
                print("\"Real\" data not loaded - do contact_tracker.load_contact_data() before plotting.")

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
        self, bin_type="bbc", contact_type="school", ratio_with_real=False, **kwargs
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
            model_mat = self.normalised_contact_matrices[bin_type][contact_type]
            real_mat = self.real_contact_matrices[bin_type][contact_type]
            mat = model_mat / real_mat
            vmin, vmax= 0.2, 3.0
            #plot_kwargs["vmin"]=vmin
            #plot_kwargs["vmax"]=vmax
            plot_kwargs["norm"]=colors.LogNorm(vmin=vmin, vmax=vmax)
            
        else:
            mat = self.normalised_contact_matrices[bin_type][contact_type]
            plot_kwargs["vmin"]=0.0
            plot_kwargs["vmax"]=4.0

        plot_kwargs.update(kwargs)

        cmap = copy.copy(cm.get_cmap('RdYlBu_r'))
        cmap.set_bad(color="lightgrey")
        plot_kwargs["cmap"] = cmap

        f, ax = plt.subplots()
        im = ax.imshow(mat.T, origin='lower', **plot_kwargs)
        if labels is not None:
            ax.set_xticks(np.arange(len(mat)))
            ax.set_xticklabels(labels,rotation=90)
            ax.set_yticks(np.arange(len(mat)))
            ax.set_yticklabels(labels)
        f.colorbar(im)

        if self.world_name is not None:
            world_name = self.world_name.split("_")[0].capitalize()
            title = f"{contact_type} contacts in {world_name} ({bin_type} bins)"
        else:
            title = f"{contact_type} contacts ({bin_type} bins)"
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
                    bin_type=rbt, contact_type=rct
                )
                mat_plot.plot()
                plt.savefig(mat_dir / f"{rct}.png", dpi=150, bbox_inches='tight')    
                if rbt not in ratio_bin_types:
                    continue
                ratio_plot = self.plot_contact_matrix(
                    bin_type=rbt, contact_type=rct, ratio_with_real=True
                )
                ratio_plot.plot()
                plt.savefig(mat_dir / f"{rct}_ratio.png", dpi=150, bbox_inches='tight')
            
if __name__ == "__main__":
    print("Use simulation_plotter.")



