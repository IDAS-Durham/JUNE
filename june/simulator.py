import copy
import logging
from datetime import datetime
from itertools import chain
from typing import List, Optional

import yaml

from june import paths
from june.demography import Person, Activities
from june.groups import Subgroup
from june.groups.commute.commutecityunit_distributor import CommuteCityUnitDistributor
from june.groups.commute.commuteunit_distributor import CommuteUnitDistributor
from june.groups.leisure import Leisure
from june.groups.travel.travelunit_distributor import TravelUnitDistributor
from june.infection.infection import InfectionSelector
from june.infection.symptom_tag import SymptomTag
from june.infection_seed import InfectionSeed
from june.interaction import ContactAveraging
from june.logger.logger import Logger
from june.policy import Policies
from june.time import Timer
from june.world import World

default_config_filename = paths.configs_path / "config_example.yaml"

sim_logger = logging.getLogger(__name__)


class SimulatorError(BaseException):
    pass


activity_hierarchy = [
    "box",
    "hospital",
    "rail_travel_out",
    "rail_travel_back",
    "commute",
    "primary_activity",
    "leisure",
    "residence",
]


class ActivityManager:
    def __init__(
            self,
            world,
            policies,
            timer,
            all_activities,
            interaction,
            logger,
            activity_to_groups: dict,
            leisure: Optional["Leisure"] = None,
            min_age_home_alone: int = 15,
    ):
        self.interaction = interaction
        self.logger = logger
        self.policies = policies
        self.world = world
        self.timer = timer
        self.leisure = leisure
        self.all_activities = all_activities

        if self.world.box_mode:
            self.activity_to_group_dict = {
                "box": ["boxes"],
            }
        else:
            self.activity_to_group_dict = {
                "hospital": ["hospitals"],
                "primary_activity": activity_to_groups.get("primary_activity", []),
                "leisure": activity_to_groups.get("leisure", []),
                "residence": activity_to_groups.get("residence", []),
                "commute": activity_to_groups.get("commute", []),
                "rail_travel": activity_to_groups.get("rail_travel", []),
            }
        self.min_age_home_alone = min_age_home_alone

        if "commute" in self.all_activities:
            commute_options = activity_to_groups["commute"]
            if "commuteunits" in commute_options:
                self.commute_unit_distributor = CommuteUnitDistributor(
                    self.world.commutehubs.members
                )
            if "commutecityunits" in commute_options:
                self.commute_city_unit_distributor = CommuteCityUnitDistributor(
                    self.world.commutecities.members
                )

        if (
                "rail_travel_out" in self.all_activities
                or "rail_travel_back" in self.all_activities
        ):
            travel_options = activity_to_groups["rail_travel"]
            if "travelunits" in travel_options:
                self.travelunit_distributor = TravelUnitDistributor(
                    self.world.travelcities.members, self.world.travelunits.members
                )

    @property
    def all_groups(self):
        return self.activities_to_groups(self.all_activities)

    def distribute_commuters(self):
        if hasattr(self, "commute_unit_distributor"):
            self.commute_unit_distributor.distribute_people()
        if hasattr(self, "commute_city_unit_distributor"):
            self.commute_city_unit_distributor.distribute_people()

    def distribute_rail_out(self):
        if hasattr(self, "travelunit_distributor"):
            self.travelunit_distributor.distribute_people_out()

    def distribute_rail_back(self):
        if hasattr(self, "travelunit_distributor"):
            self.travelunit_distributor.distribute_people_back()

    @staticmethod
    def apply_activity_hierarchy(activities: List[str]) -> List[str]:
        """
        Returns a list of activities with the right order, obeying the permanent activity hierarcy
        and shuflling the random one.

        Parameters
        ----------
        activities:
            list of activities that take place at a given time step
        Returns
        -------
        Ordered list of activities according to hierarchy
        """
        activities.sort(key=lambda x: activity_hierarchy.index(x))
        return activities

    def activities_to_groups(self, activities: List[str]) -> List[str]:
        """
        Converts activities into Groups, the interaction will run over these Groups.

        Parameters
        ---------
        activities:
            list of activities that take place at a given time step
        Returns
        -------
        List of groups that are active.
        """

        groups = [self.activity_to_group_dict[activity] for activity in activities]
        return list(chain(*groups))

    def move_to_active_subgroup(
            self, activities: List[str], person: "Person"
    ) -> Optional["Subgroup"]:
        """
        Given the hierarchy of activities and a person, decide what subgroup
        should they go to

        Parameters
        ----------
        activities:
            list of activities that take place at a given time step
        person:
            person that is looking for a subgroup to go to
        Returns
        -------
        Subgroup to which person has to go, given the hierarchy of activities
        """
        for activity in activities:
            if activity == "leisure" and person.leisure is None:
                subgroup = self.leisure.get_subgroup_for_person_and_housemates(
                    person=person,
                )
            else:
                subgroup = getattr(person, activity)
            if subgroup is not None:
                subgroup.append(person)
                return
        raise SimulatorError(
            "Attention! Some people do not have an activity in this timestep."
        )

    def do_timestep(self):
        activities = self.timer.activities

        if not activities or len(activities) == 0:
            sim_logger.info("==== do_timestep(): no active groups found. ====")
            return

        if "commute" in activities:
            self.distribute_commuters()
        if "rail_travel_out" in activities:
            self.distribute_rail_out()
        if "rail_travel_back" in activities:
            self.distribute_rail_back()
        if self.leisure is not None:
            self.leisure.generate_leisure_probabilities_for_timestep(
                self.timer.duration,
                self.timer.is_weekend,
                self.policies.find_closed_venues(self.timer.date),
            )
            if self.policies is not None:
                self.policies.apply_change_probabilities_leisure(
                    self.timer.date, self.leisure
                )
                self.policies.apply_social_distancing_policy(
                    self.timer.date, self.interaction
                )
        self.move_people_to_active_subgroups(
            activities, self.timer.date, self.timer.now,
        )
        active_groups = self.activities_to_groups(activities)
        group_instances = [
            getattr(self.world, group)
            for group in active_groups
            if group not in ["household_visits", "care_home_visits"]
        ]
        n_people = 0

        for cemetery in self.world.cemeteries.members:
            n_people += len(cemetery.people)
        sim_logger.info(
            f"Date = {self.timer.date}, "
            f"number of deaths =  {n_people}, "
            f"number of infected = {len(self.world.people.infected)}"
        )
        for group_type in group_instances:
            n_people_group = 0
            for group in group_type.members:
                self.interaction.time_step(
                    self.timer.now, self.timer.duration, group, self.logger,
                )
                n_people += group.size
                n_people_group += group.size

        if n_people != len(self.world.people.members):
            raise SimulatorError(
                f"Number of people active {n_people} does not match "
                f"the total people number {len(self.world.people.members)}"
            )

    @staticmethod
    def kid_drags_guardian(
            guardian: "Person",
    ):
        """
        A kid makes their guardian go home.

        Parameters
        ----------
        guardian:
            guardian to be sent home
        """
        if guardian is not None:
            if guardian.busy:
                for subgroup in guardian.subgroups.iter():
                    if guardian in subgroup:
                        subgroup.remove(guardian)
                        break
            guardian.residence.append(guardian)

    def move_mild_kid_guardian_to_household(self, kid: "Person"):
        """
        Move  a kid and their guardian to the household, so no kid is left
        home alone.

        Parameters
        ----------
        kid:
            kid to be sent home
        """
        possible_guardians = [
            housemate for housemate in kid.residence.group.people if housemate.age >= 18
        ]
        if len(possible_guardians) == 0:
            guardian = kid.find_guardian()
            self.kid_drags_guardian(guardian)
        kid.residence.append(kid)

    def move_mild_ill_to_household(self, person: "Person"):
        """
        Move person with a mild illness to their households. For kids that will
        always happen, and if they are left alone at home they will also drag one
        of their guardians home.

        Parameters
        ----------
        person:
            person to be sent home
        """
        if person.age < self.min_age_home_alone:
            self.move_mild_kid_guardian_to_household(person)
        else:
            person.residence.append(person)

    def move_people_to_active_subgroups(
            self,
            activities: List[str],
            date: datetime = datetime(2020, 2, 2),
            days_from_start=0,
    ):
        """
        Sends every person to one subgroup. If a person has a mild illness,
        they stay at home

        Parameters
        ----------

        """
        skip_activity_collection = self.policies.skip_activity_collection(date=date)
        stay_home_collection = self.policies.stay_home_collection(date=date)

        activities = self.apply_activity_hierarchy(activities)
        for person in self.world.people.members:
            if person.dead or person.busy:
                continue
            if stay_home_collection(person, days_from_start):
                self.move_mild_ill_to_household(person)
            else:
                allowed_activities = skip_activity_collection(person, activities, )
                self.move_to_active_subgroup(allowed_activities, person)


class Simulator:
    def __init__(
            self,
            world: World,
            interaction: ContactAveraging,
            selector: InfectionSelector,
            timer: Timer,
            activity_manager: ActivityManager,
            infection_seed: Optional["InfectionSeed"] = None,
            save_path: str = "results",
            output_filename: str = "logger.hdf5",
            light_logger: bool = False,
    ):
        """
        Class to run an epidemic spread simulation on the world

        Parameters
        ----------
        world: 
            instance of World class
        interaction:
            instance of Interaction class
        save_path:
            path to save logger results
        """
        self.activity_manager = activity_manager
        self.world = world
        self.interaction = interaction
        self.beta_copy = copy.deepcopy(self.interaction.beta)
        self.infection_seed = infection_seed
        self.selector = selector
        self.light_logger = light_logger
        self.timer = timer
        if not self.world.box_mode:
            self.logger = Logger(save_path=save_path, file_name=output_filename)
        else:
            self.logger = None

    @classmethod
    def from_file(
            cls,
            world: "World",
            interaction: "ContactAveraging",
            selector: "InfectionSelector",
            policies: Optional["Policies"] = None,
            infection_seed: Optional["InfectionSeed"] = None,
            leisure: Optional["Leisure"] = None,
            config_filename: str = default_config_filename,
            save_path: str = "results",
    ) -> "Simulator":

        """
        Load config for simulator from world.yaml

        Parameters
        ----------
        save_path
        leisure
        infection_seed
        policies
        selector
        interaction
        world
        config_filename
            The path to the world yaml configuration

        Returns
        -------
        A Simulator
        """
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        if world.box_mode:
            activity_to_groups = None
        else:
            activity_to_groups = config["activity_to_groups"]
        time_config = config["time"]
        weekday_activities = [
            activity for activity in time_config["step_activities"]["weekday"].values()
        ]
        weekend_activities = [
            activity for activity in time_config["step_activities"]["weekend"].values()
        ]
        all_activities = set(chain(*(weekday_activities + weekend_activities)))

        cls.check_inputs(time_config)

        timer = Timer(
            initial_day=time_config["initial_day"],
            total_days=time_config["total_days"],
            weekday_step_duration=time_config["step_duration"]["weekday"],
            weekend_step_duration=time_config["step_duration"]["weekend"],
            weekday_activities=time_config["step_activities"]["weekday"],
            weekend_activities=time_config["step_activities"]["weekend"],
        )

        activity_manager = ActivityManager(
            world=world,
            all_activities=all_activities,
            activity_to_groups=activity_to_groups,
            leisure=leisure,
            policies=policies,
            timer=timer,
            interaction=interaction,
            logger=sim_logger
        )
        return cls(
            world=world,
            interaction=interaction,
            selector=selector,
            activity_manager=activity_manager,
            timer=timer,
            infection_seed=infection_seed,
            save_path=save_path,
        )

    def clear_world(self):
        """
        Removes everyone from all possible groups, and sets everyone's busy attribute
        to False.

        """
        for group_name in self.activity_manager.all_groups:
            if group_name in ["care_home_visits", "household_visits"]:
                continue
            grouptype = getattr(self.world, group_name)
            if grouptype is not None:
                for group in grouptype.members:
                    group.clear()

        for person in self.world.people.members:
            person.busy = False
            person.subgroups.leisure = None

    @staticmethod
    def check_inputs(time_config: dict):
        """
        Check that the iput time configuration is correct, i.e., activities are among allowed activities
        and days have 24 hours.

        Parameters
        ----------
        time_config:
            dictionary with time steps configuration
        """

        # Sadly, days only have 24 hours
        assert sum(time_config["step_duration"]["weekday"].values()) == 24
        # even during the weekend :(
        assert sum(time_config["step_duration"]["weekend"].values()) == 24

        # Check that all groups given in time_config file are in the valid group hierarchy
        all_groups = activity_hierarchy
        for step, activities in time_config["step_activities"]["weekday"].items():
            assert all(group in all_groups for group in activities)

        for step, activities in time_config["step_activities"]["weekend"].items():
            assert all(group in all_groups for group in activities)

    def hospitalise_the_sick(self, person: "Person", previous_tag: str):
        """
        Hospitalise sick person. Also moves them from a regular bed
        to an ICU bed if their symptoms tag has changed.

        Parameters
        ----------
        person:
            person to hospitalise
        previous_tag:
            previous symptoms tag of a person
        """
        if person.hospital is None:
            self.world.hospitals.allocate_patient(person)
        elif previous_tag != person.health_information.tag:
            person.hospital.group.move_patient_within_hospital(person)

    def bury_the_dead(self, person: "Person", time: float):
        """
        When someone dies, send them to cemetery. 
        ZOMBIE ALERT!! 

        Parameters
        ----------
        person:
            person to send to cemetery
        """
        person.dead = True
        cemetery = self.world.cemeteries.get_nearest(person)
        cemetery.add(person)
        person.health_information.set_dead(time)
        person.subgroups = Activities(None, None, None, None, None, None, None)

    def recover(self, person: "Person", time: float):
        """
        When someone recovers, erase the health information they carry and change their susceptibility.

        Parameters
        ----------
        person:
            person to recover
        time:
            time (in days), at which the person recovers
        """
        # TODO: seems to be only used to set the infection length at the moment, but this is not logged
        # anywhere, so we could get rid of this potentially
        person.health_information.set_recovered(time)
        person.susceptibility = 0.0
        person.health_information = None

    def update_health_status(self, time: float, duration: float):
        """
        Update symptoms and health status of infected people.
        Send them to hospital if necessary, or bury them if they
        have died.

        Parameters
        ----------
        time:
            time now
        duration:
            duration of time step
        """
        ids = []
        symptoms = []
        n_secondary_infections = []
        for person in self.world.people.infected:
            health_information = person.health_information
            previous_tag = health_information.tag
            health_information.update_health_status(time, duration)
            if (
                    previous_tag == SymptomTag.exposed
                    and health_information.tag == SymptomTag.influenza
            ):
                person.residence.group.quarantine_starting_date = time
            ids.append(person.id)
            symptoms.append(person.health_information.tag.value)
            n_secondary_infections.append(person.health_information.number_of_infected)
            # Take actions on new symptoms
            if health_information.recovered:
                if person.hospital is not None:
                    person.hospital.group.release_as_patient(person)
                self.recover(person, time)
            elif health_information.should_be_in_hospital:
                self.hospitalise_the_sick(person, previous_tag)
            elif health_information.is_dead:
                self.bury_the_dead(person, time)
        if self.logger:
            self.logger.log_infected(
                self.timer.date, ids, symptoms, n_secondary_infections
            )

    def do_timestep(self):
        """
        Perform a time step in the simulation

        """
        self.activity_manager.do_timestep()

        self.update_health_status(time=self.timer.now, duration=self.timer.duration)
        if self.logger:
            self.logger.log_infection_location(self.timer.date)
            self.logger.log_hospital_capacity(self.timer.date, self.world.hospitals)
        self.clear_world()

    def run(self):
        """
        Run simulation with n_seed initial infections
        """
        sim_logger.info(
            f"Starting group_dynamics for {self.timer.total_days} days at day {self.timer.day}"
        )
        sim_logger.info(
            f"starting the loop ..., at {self.timer.day} days, to run for {self.timer.total_days} days"
        )
        self.clear_world()
        if self.logger:
            self.logger.log_population(
                self.world.people, light_logger=self.light_logger
            )
            self.logger.log_hospital_characteristics(self.world.hospitals)
        for time in self.timer:
            if time > self.timer.final_date:
                break
            if self.infection_seed:
                if self.infection_seed.max_date >= time >= self.infection_seed.min_date:
                    self.infection_seed.unleash_virus_per_region(time)
            self.do_timestep()
