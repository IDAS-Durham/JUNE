import time
import logging
import numpy as np
import numba as nb
import random
import json
from pathlib import Path
from mpi4py import MPI
import h5py
import sys
import cProfile
import argparse
import yaml

from june.hdf5_savers import generate_world_from_hdf5, load_population_from_hdf5
from june.interaction import Interaction
from june.epidemiology.infection import (
    Infection,
    InfectionSelector,
    InfectionSelectors,
    HealthIndexGenerator,
    SymptomTag,
    ImmunitySetter,
    Covid19,
    B16172,
)
from june.groups import Hospitals, Schools, Companies, Households, CareHomes, Cemeteries
from june.groups.travel import Travel
from june.groups.leisure import Cinemas, Pubs, Groceries, generate_leisure_for_config
from june.simulator import Simulator
from june.epidemiology.epidemiology import Epidemiology
from june.epidemiology.infection_seed import (
    InfectionSeed,
    Observed2Cases,
    InfectionSeeds,
)
from june.policy import Policies
from june.event import Events
from june import paths
from june.records import Record
from june.records.records_writer import combine_records
from june.domains import Domain, DomainSplitter
from june.mpi_setup import mpi_comm, mpi_rank, mpi_size

from june.tracker.tracker import Tracker
from june.tracker.tracker_plots import PlotClass


from collections import defaultdict


def set_random_seed(seed=999):
    """
    Sets global seeds for testing in numpy, random, and numbaized numpy.
    """
    @nb.njit(cache=True)
    def set_seed_numba(seed):
        random.seed(seed)
        return np.random.seed(seed)

    np.random.seed(seed)
    set_seed_numba(seed)
    random.seed(seed)
    return
    

set_random_seed(0)

# disable logging for ranks
if mpi_rank > 0:
    logging.disable(logging.CRITICAL)


def keys_to_int(x):
    return {int(k): v for k, v in x.items()}

# =============== Argparse =========================#

parser = argparse.ArgumentParser(description="Full run of the England")

parser.add_argument(
    "-w",
    "--world_path",
    help="path to saved world file",
    required=False,
    default="/cosma5/data/do010/dc-walk3/world.hdf5",
)

parser.add_argument(
    "-c",
    "--comorbidities",
    help="True to include comorbidities",
    required=False,
    default="True",
)
parser.add_argument(
    "-con",
    "--config",
    help="Config file",
    required=False,
    default=paths.configs_path / "config_example.yaml",
)
parser.add_argument(
    "-p",
    "--parameters",
    help="Parameter file",
    required=False,
    default=paths.configs_path / "defaults/interaction/interaction.yaml",
)

parser.add_argument(
    "-tr",
    "--tracker",
    help="Activate Tracker for CM tracing",
    required=False,
    default="False",
)

parser.add_argument(
    "-ro",
    "--region_only",
    help="Run only one region",
    required=False,
    default="False",
)

parser.add_argument(
    "-hb", "--household_beta", help="Household beta", required=False, default=0.25
)
parser.add_argument(
    "-nnv", "--no_vaccines", help="Implement no vaccine policies", required=False, default="False"
)
parser.add_argument(
    "-v", "--vaccines", help="Implement vaccine policies", required=False, default="False"
)
parser.add_argument(
    "-nv", "--no_visits", help="No shelter visits", required=False, default="False"
)
parser.add_argument(
    "-ih",
    "--indoor_beta_ratio",
    help="Indoor/household beta ratio scaling",
    required=False,
    default=0.55,
)
parser.add_argument(
    "-oh",
    "--outdoor_beta_ratio",
    help="Outdoor/household beta ratio scaling",
    required=False,
    default=0.05,
)
parser.add_argument(
    "-inf",
    "--infectiousness_path",
    help="path to infectiousness parameter file",
    required=False,
    default="nature",
)
parser.add_argument(
    "-cs",
    "--child_susceptibility",
    help="Reduce child susceptibility for under 12s",
    required=False,
    default="False",
)
parser.add_argument(
    "-u",
    "--isolation_units",
    help="True to include isolation units",
    required=False,
    default="False",
)
parser.add_argument(
    "-t",
    "--isolation_testing",
    help="Mean testing time",
    required=False,
    default=3,
)
parser.add_argument(
    "-i", "--isolation_time", help="Ouput file name", required=False, default=7
)
parser.add_argument(
    "-ic",
    "--isolation_compliance",
    help="Isolation unit self reporting compliance",
    required=False,
    default=0.6,
)
parser.add_argument(
    "-m",
    "--mask_wearing",
    help="True to include mask wearing",
    required=False,
    default="False",
)
parser.add_argument(
    "-mc",
    "--mask_compliance",
    help="Mask wearing compliance",
    required=False,
    default="False",
)
parser.add_argument(
    "-mb",
    "--mask_beta_factor",
    help="Mask beta factor reduction",
    required=False,
    default=0.5,
)

parser.add_argument(
    "-s",
    "--save_path",
    help="Path of where to save logger",
    required=False,
    default="results",
)

parser.add_argument(
    "--n_seeding_days",
    help="number of seeding days",
    required=False,
    default=10,
)
parser.add_argument(
    "--n_seeding_case_per_day",
    help="number of seeding cases per day",
    required=False,
    default=10,
)

args = parser.parse_args()
args.save_path = Path(args.save_path)

if mpi_rank == 0:
    counter = 1
    OG_save_path = args.save_path 
    while args.save_path.is_dir() == True:
        args.save_path = Path( str(OG_save_path) + "_%s" % counter)
        counter += 1
    args.save_path.mkdir(parents=True, exist_ok=False)
    
mpi_comm.Barrier()
args.save_path = mpi_comm.bcast(args.save_path, root=0)
mpi_comm.Barrier()

     
if args.tracker == "True":
    args.tracker = True
else:
    args.tracker = False

if args.comorbidities == "True":
    args.comorbidities = True
else:
    args.comorbidities = False

if args.child_susceptibility == "True":
    args.child_susceptibility = True
else:
    args.child_susceptibility = False
    
if args.no_vaccines == "True":
    args.no_vaccines = True
else:
    args.no_vaccines = False
    
if args.vaccines == "True":
    args.vaccines = True
else:
    args.vaccines = False

if args.no_visits == "True":
    args.no_visits = True
else:
    args.no_visits = False

if args.isolation_units == "True":
    args.isolation_units = True
else:
    args.isolation_units = False

if args.mask_wearing == "True":
    args.mask_wearing = True
else:
    args.mask_wearing = False


    

if args.infectiousness_path == "nature":
    transmission_config_path = paths.configs_path / "defaults/transmission/nature.yaml"
elif args.infectiousness_path == "correction_nature":
    transmission_config_path = (
        paths.configs_path / "defaults/transmission/correction_nature.yaml"
    )
elif args.infectiousness_path == "nature_larger":
    transmission_config_path = (
        paths.configs_path
        / "defaults/transmission/nature_larger_presymptomatic_transmission.yaml"
    )
elif args.infectiousness_path == "nature_lower":
    transmission_config_path = (
        paths.configs_path
        / "defaults/transmission/nature_lower_presymptomatic_transmission.yaml"
    )
elif args.infectiousness_path == "xnexp":
    transmission_config_path = paths.configs_path / "defaults/transmission/XNExp.yaml"
else:
    raise NotImplementedError

if mpi_rank == 0:
	print("Comorbidities set to: {}".format(args.comorbidities))
	print("Parameters path set to: {}".format(args.parameters))
	print("Indoor beta ratio is set to: {}".format(args.indoor_beta_ratio))
	print("Outdoor beta ratio set to: {}".format(args.outdoor_beta_ratio))
	print("Infectiousness path set to: {}".format(args.infectiousness_path))
	print("Child susceptibility change set to: {}".format(args.child_susceptibility))

	print("Isolation units set to: {}".format(args.isolation_units))
	print("Household beta set to: {}".format(args.household_beta))
	if args.isolation_units:
	    print("Testing time set to: {}".format(args.isolation_testing))
	    print("Isolation time set to: {}".format(args.isolation_time))
	    print("Isolation compliance set to: {}".format(args.isolation_compliance))

	print("Mask wearing set to: {}".format(args.mask_wearing))
	if args.mask_wearing:
	    print("Mask compliance set to: {}".format(args.mask_compliance))
	    print("Mask beta factor set up: {}".format(args.mask_beta_factor))

	print("World path set to: {}".format(args.world_path))
	print("Save path set to: {}".format(args.save_path))

	print("\n", args.__dict__, "\n")


# =============== world creation =========================#
CONFIG_PATH = args.config

def generate_simulator():
    record = Record(record_path=args.save_path, record_static_data=True, mpi_rank=mpi_rank)
    if mpi_rank == 0:
        with h5py.File(args.world_path, "r") as f:
            super_area_ids = f["geography"]["super_area_id"]
            super_area_names = f["geography"]["super_area_name"]
            super_area_name_to_id = {
                name.decode(): id for name, id in zip(super_area_names, super_area_ids)
            }
        super_areas_per_domain, score_per_domain = DomainSplitter.generate_world_split(
            number_of_domains=mpi_size, world_path=args.world_path
        )
        super_area_names_to_domain_dict = {}
        super_area_ids_to_domain_dict = {}
        for domain, super_areas in super_areas_per_domain.items():
            for super_area in super_areas:
                super_area_names_to_domain_dict[super_area] = domain
                super_area_ids_to_domain_dict[
                    int(super_area_name_to_id[super_area])
                ] = domain
        with open("super_area_ids_to_domain.json", "w") as f:
            json.dump(super_area_ids_to_domain_dict, f)
        with open("super_area_names_to_domain.json", "w") as f:
            json.dump(super_area_names_to_domain_dict, f)
    print(f"mpi_rank {mpi_rank} waiting")
    mpi_comm.Barrier()
    if mpi_rank > 0:
        with open("super_area_ids_to_domain.json", "r") as f:
            super_area_ids_to_domain_dict = json.load(f, object_hook=keys_to_int)
    print(f"mpi_rank {mpi_rank} loading domain")
    domain = Domain.from_hdf5(
        domain_id=mpi_rank,
        super_areas_to_domain_dict=super_area_ids_to_domain_dict,
        hdf5_file_path=args.world_path,
        interaction_config=args.parameters,
    )
    print(f"mpi_rank {mpi_rank} has loaded domain")
    # regenerate lesiure
    leisure = generate_leisure_for_config(domain, CONFIG_PATH)
    #
    selector = InfectionSelector.from_file()
    selectors = InfectionSelectors([selector])

    infection_seed = InfectionSeed.from_uniform_cases(
        world=domain, infection_selector=selector, cases_per_capita=0.01, date="2020-03-02 9:00",     seed_past_infections=False,
    )
    infection_seeds = InfectionSeeds([infection_seed])

    epidemiology = Epidemiology(infection_selectors=selectors, infection_seeds=infection_seeds)

    interaction = Interaction.from_file(
        config_filename=args.parameters
    )
    
    policies = Policies.from_file(
        paths.configs_path / "defaults/policy/policy.yaml",
        base_policy_modules=("june.policy", "camps.policy"),
    )

    # events
    events = Events.from_file()

    # create simulator

    travel = Travel()
    
    group_types = []
    domainVenues = {}
    if domain.households is not None:
        if len(domain.households) > 0:
            group_types.append(domain.households)
            domainVenues["households"] = {"N": len(domain.households), "bins": domain.households[0].subgroup_bins}
        else:
            domainVenues["households"] = {"N": 0, "bins": "NaN"}
            
    if domain.care_homes is not None:
       if len(domain.care_homes) > 0:
           group_types.append(domain.care_homes)
           domainVenues["care_homes"] = {"N": len(domain.care_homes), "bins": domain.care_homes[0].subgroup_bins}
       else:
           domainVenues["care_homes"] = {"N": 0, "bins": "NaN"}
           
    if domain.schools is not None:
        if len(domain.schools) > 0:
            group_types.append(domain.schools)
            domainVenues["schools"] = {"N": len(domain.schools), "bins": domain.schools[0].subgroup_bins}
        else:
            domainVenues["schools"] = {"N": 0, "bins": "NaN"}
            
    if domain.hospitals is not None:
        if len(domain.hospitals) > 0:
            group_types.append(domain.hospitals)
            domainVenues["hospitals"] = {"N": len(domain.hospitals)}
        else:
            domainVenues["hospitals"] = {"N": 0, "bins": "NaN"}
            
    if domain.companies is not None:
        if len(domain.companies) > 0:
            group_types.append(domain.companies)
            domainVenues["companies"] = {"N": len(domain.companies), "bins": domain.companies[0].subgroup_bins}
        else:
            domainVenues["companies"] = {"N": 0, "bins": "NaN"}
    	
    if domain.universities is not None:
        if len(domain.universities) > 0:
            group_types.append(domain.universities)
            domainVenues["universities"] = {"N": len(domain.universities), "bins": domain.universities[0].subgroup_bins}
        else:
            domainVenues["universities"] = {"N": 0, "bins": "NaN"}
            
    if domain.pubs is not None:
        if len(domain.pubs) > 0:
            group_types.append(domain.pubs)
            domainVenues["pubs"] = {"N": len(domain.pubs), "bins": domain.pubs[0].subgroup_bins}
        else:
            domainVenues["pubs"] = {"N": 0, "bins": "NaN"}
    	
    if domain.groceries is not None:
        if len(domain.groceries) > 0:
            group_types.append(domain.groceries)
            domainVenues["groceries"] = {"N": len(domain.groceries), "bins": domain.groceries[0].subgroup_bins}
        else:
            domainVenues["groceries"] = {"N": 0, "bins": "NaN"}
            
    if domain.cinemas is not None:
        if len(domain.cinemas) > 0:
            group_types.append(domain.cinemas)
            domainVenues["cinemas"] = {"N": len(domain.cinemas), "bins": domain.cinemas[0].subgroup_bins}
        else:
            domainVenues["cinemas"] = {"N": 0, "bins": "NaN"}
            
    if domain.gyms is not None:
        if len(domain.gyms) > 0:
            group_types.append(domain.gyms)
            domainVenues["gyms"] = {"N": len(domain.gyms), "bins": domain.gyms[0].subgroup_bins}
        else:
            domainVenues["gyms"] = {"N": 0, "bins": "NaN"}
            
    if domain.city_transports is not None:
        if len(domain.city_transports) > 0:
           group_types.append(domain.city_transports)
           domainVenues["city_transports"] = {"N": len(domain.city_transports)}
        else:
           domainVenues["city_transports"] = {"N": 0, "bins": "NaN"}
           
    if domain.inter_city_transports is not None:
        if len(domain.inter_city_transports) > 0:
            group_types.append(domain.inter_city_transports)
            domainVenues["inter_city_transports"] = {"N": len(domain.inter_city_transports)}
        else:
            domainVenues["inter_city_transports"] = {"N": 0, "bins": "NaN"}
            
    print(mpi_rank, domainVenues)

    # ==================================================================================#

    # =================================== tracker ===============================#
    if args.tracker:    
        tracker = Tracker(
            world=domain,
            record_path=args.save_path,
            group_types=group_types,
            load_interactions_path=args.parameters,
            contact_sexes=["unisex", "male", "female"],
            Tracker_Contact_Type=["1D"],
            MaxVenueTrackingSize=100000
        )
    else:
        tracker=None
    
    
    simulator = Simulator.from_file(
        world=domain,
        policies=policies,
        events=events,
        interaction=interaction,
        leisure=leisure,
        travel=travel,
        epidemiology=epidemiology,
        config_filename=CONFIG_PATH,
        record=record,
        tracker=tracker,
    )
    return simulator

# ==================================================================================#

# =================================== simulator ===============================#

print(f"mpi_rank {mpi_rank} generate simulator")
simulator = generate_simulator()
simulator.run()

# ==================================================================================#

# =================================== read logger ===============================#

mpi_comm.Barrier()

if mpi_rank == 0:
    combine_records(args.save_path)

mpi_comm.Barrier()

# ==================================================================================#

# =================================== tracker figures ===============================#

if args.tracker:
    if mpi_rank == 0:
    	print("Tracker stuff now")
    	
    simulator.tracker.contract_matrices("AC", np.array([0,18,100]))
    simulator.tracker.contract_matrices("Paper",[0,5,10,13,15,18,20,22,25,30,35,40,45,50,55,60,65,70,75,100])                                  
    simulator.tracker.post_process_simulation(save=True)
    
    if mpi_rank == 0:
        print("Merge TODO")
        #tracker_combine_records(args.save_path)

    mpi_comm.Barrier()
    
    #Make Plots
#    Plots = PlotClass(
#        record_path=args.save_path / "Tracker",
#        Tracker_Contact_Type = "1D"
#    )

#    Plots.make_plots(
#    	 plot_BBC=True,
#    	 plot_INPUTOUTPUT=True,
#        plot_AvContactsLocation=True, 
#        plot_dTLocationPopulation=True, 
#        plot_InteractionMatrices=True, 
#        plot_ContactMatrices=True,
#        plot_CompareSexMatrices=True,
#        plot_AgeBinning=True, 
#        plot_Distances=True 
#    )
    
#    #Make Plots
#    Plots = PlotClass(
#        record_path=args.save_path / "Tracker",
#        Tracker_Contact_Type = "All"

#    )
#    Plots.make_plots(
#     	 plot_INPUTOUTPUT=False,
#        plot_AvContactsLocation=False, 
#        plot_dTLocationPopulation=False, 
#        plot_InteractionMatrices=True, 
#        plot_ContactMatrices=True,
#        plot_CompareSexMatrices=True,
#        plot_AgeBinning=False, 
#        plot_Distances=False 
#    )
