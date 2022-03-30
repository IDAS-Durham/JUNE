import numpy as np
import yaml
import pandas as pd
from pathlib import Path

import pytest

from june import paths
from june.tracker.tracker import Tracker


from june.groups.group import make_subgroups

from june.geography import Geography
from june.groups.leisure import Pubs

from june.world import generate_world_from_geography

interaction_config = paths.configs_path / "tests/tracker/tracker_test_interaction.yaml"
test_config = paths.configs_path / "tests/tracker/tracker_test_config.yaml"


class TestTracker():
    @pytest.fixture(name="world", autouse=True, scope='class')
    def make_world(self):
        geography = Geography.from_file({"super_area": ["E02005103"]})
        world = generate_world_from_geography(geography, include_households=True)

        Pubs.Get_Interaction(interaction_config)
        world.pubs = Pubs.for_geography(geography)

        return world


    @pytest.fixture(name="tracker", autouse=True, scope='class')
    def setup_tracker(self, world):
        Pubs.Get_Interaction(interaction_config)
        world.pubs = Pubs.from_coordinates(np.array([pub.coordinates for pub in world.pubs]), world.super_areas)

        
        group_types=[
            world.pubs,
            world.households
        ]

        tracker = Tracker(
            world=world,
            record_path=None,
            group_types=group_types,
            load_interactions_path=interaction_config,
            track_contacts_count=True,
            contact_sexes=["unisex","male", "female"]
        )

        # tracker.simulation_days = 1/24
        # tracker.delta_t = 3600
        # tracker.trackertimestep(["households", "pubs"], 0)
        # tracker = postprocess_functions(tracker)
        return tracker

    def test__tracker_init(self, tracker):
        ''''''
        #Check loaded in correct values from made up obscene values
        assert tracker.interaction_matrices["pub"]["contacts"] == [[10]] 
        assert tracker.interaction_matrices["pub"]["proportion_physical"] == [[0.2]]  
        assert tracker.interaction_matrices["pub"]["type"] == "Age"  
        assert tracker.interaction_matrices["pub"]["bins"] == [1,99]  

        #Check functionality of calls from make_subgroups
        assert tracker.world.pubs[0].subgroup_bins == [1,99] 
        assert tracker.world.pubs[0].subgroup_type == "Age" 
        assert tracker.world.pubs[0].subgroup_labels == ["A"] 


        #Check the feed in groups we care about tracking
        assert sorted(tracker.group_type_names) == ["household", "pub"]

        #Check CM that are initialised
        assert sorted(tracker.contact_matrices["syoa"].keys() ) == ["global", "household", "pub"]
        assert sorted(tracker.contact_matrices["syoa"]["global"].keys() ) == ['female', 'male', 'unisex']

        #Check person contact counts
        assert len(tracker.contact_counts) == len(tracker.world.people)

    def test__intersection(self, tracker):
        #Check intersection of lists functionality
        assert sorted(tracker.intersection(["A", "B", "C", "D"], ["C", "D", "E", "F", "D"], permute=False)) == ["C", "D"]
        assert sorted(tracker.intersection(["A", "B", "C", "D"], ["C", "D", "E", "F", "D"], permute=True)) == ["C", "D"]

    def test__contractmatrix(self, tracker):
        #Check contract matrix functionality
        bins_syoa =  np.arange(0,101,1)
        CM = np.ones((len(bins_syoa),len(bins_syoa)))

        assert np.array_equal(tracker.contract_matrix(CM, [0,18,100], method = np.sum) , np.array([[18**2, (100-18)*18],[(100-18)*18, (100-18)**2]]))
        assert np.array_equal(tracker.contract_matrix(CM, [0,18,100], method = np.mean) , np.array([[1, 1],[1,1]]))

        assert np.array_equal(tracker.contract_matrix(CM, [0, 100], method = np.sum) , np.array([[100**2]]))
        assert np.array_equal(tracker.contract_matrix(CM, [10, 90], method = np.sum) , np.array([[80**2]]))

    def test__Probabilistic_Contacts(self, tracker):
        func = tracker.Probabilistic_Contacts
        SigTol = 2
        N = 100
        Mean = 10
        Error = 0

        Results = np.zeros(N)
        for i in range(N):
            Results[i] = func(Mean, Error)
        Errorless_STD = np.std(Results, ddof=1)

        #Make sure all non neg number of contacts
        assert all(i >= 0 for i in Results)
        #Make distribution is poisson under tolerance
        assert pytest.approx(np.mean(Results), abs = SigTol*np.sqrt(Mean/N)) == Mean
        
        Error = 5
        for i in range(N):
            Results[i] = func(Mean, Error)
        Errored_STD = np.std(Results, ddof=1)

        #Make sure all non neg number of contacts
        assert all(i >= 0 for i in Results)
        #Make distribution is poisson under tolerance
        assert pytest.approx(np.mean(Results), abs = SigTol*np.sqrt(Mean/N)) == Mean

        #Errored increase the variance of the results
        assert Errored_STD >= Errorless_STD
        

def postprocess_functions(tracker: Tracker):
    tracker.contract_matrices("Interaction", np.array([]))
    tracker.convert_dict_to_df()
    tracker.calc_age_profiles()
    tracker.calc_average_contacts()
    tracker.normalise_contact_matrices()
    return tracker

    

