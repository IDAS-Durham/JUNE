import copy
import logging
import random
from datetime import datetime
from itertools import chain
from typing import List, Optional

import yaml

from june import paths
from june.demography import Person, Activities
from june.groups.commute.commutecityunit_distributor import CommuteCityUnitDistributor
from june.groups.commute.commuteunit_distributor import CommuteUnitDistributor
from june.groups.travel.travelunit_distributor import TravelUnitDistributor
from june.infection.infection import InfectionSelector
from june.interaction import Interaction
from june.logger.logger import Logger
from june.policy import Policies
from june.time import Timer
from june.world import World

default_config_filename = paths.configs_path / "config_example.yaml"

sim_logger = logging.getLogger(__name__)


class SimulatorError(BaseException):
    pass


class Simulator:
    def __init__(
            self,
            world: World,
            interaction: Interaction,
            selector: InfectionSelector,
            activity_to_groups: dict,
            time_config: dict,
            seed: Optional["Seed"] = None,
            leisure: Optional["Leisure"] = None,
            min_age_home_alone: int = 15,
            stay_at_home_complacency: float = 0.95,
            policies: Optional["Policies"] = None,
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
        infection:
            instance of Infection class
        activity_to_groups:
            mapping between an activity and its corresponding groups
        time_config:
            dictionary with temporal configuration to set up the simulation
        min_age_home_alone:
            minimum age of a child to be left alone at home when ill
        stay_at_home_complacency:
            probability that an ill person will not stay at home
        policies:
            policies to be implemented at different time steps
        save_path:
            path to save logger results
        """
        self.world = world
        self.interaction = interaction
        self.beta_copy = copy.deepcopy(self.interaction.beta)
        self.seed = seed
        self.selector = selector
        self.policies = policies
        self.light_logger = light_logger
        self.activity_hierarchy = [
            "box",
            "hospital",
            "rail_travel_out",
            "rail_travel_back",
            "commute",
            "primary_activity",
            "leisure",
            "residence",
        ]
        self.check_inputs(time_config)
        self.timer = Timer(
            total_days=time_config["total_days"],
            weekday_step_duration=time_config["step_duration"]["weekday"],
            weekend_step_duration=time_config["step_duration"]["weekend"],
            weekday_activities=time_config["step_activities"]["weekday"],
            weekend_activities=time_config["step_activities"]["weekend"],
        )
        if not self.world.box_mode:
            self.logger = Logger(save_path=save_path, file_name=output_filename)
        else:
            self.logger = None
        self.all_activities = self.get_all_activities(time_config)
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
        self.stay_at_home_complacency = stay_at_home_complacency
        if "commute" in self.all_activities:
            self.initialize_commute(activity_to_groups["commute"])
        if "leisure" in self.all_activities:
            self.leisure = leisure
            self.leisure.distribute_social_venues_to_people(self.world.people)
        if (
                "rail_travel_out" in self.all_activities
                or "rail_travel_back" in self.all_activities
        ):
            self.initialize_rail_travel(activity_to_groups["rail_travel"])

    @classmethod
    def from_file(
            cls,
            world: "World",
            interaction: "Interaction",
            selector: "InfectionSelector",
            policies: Optional["Policies"] = None,
            seed: Optional["Seed"] = None,
            leisure: Optional["Leisure"] = None,
            config_filename: str = default_config_filename,
            save_path: str = "results",
    ) -> "Simulator":

        """
        Load config for simulator from world.yaml

        Parameters
        ----------
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
        return cls(
            world,
            interaction,
            selector,
            activity_to_groups,
            time_config,
            policies=policies,
            seed=seed,
            leisure=leisure,
            save_path=save_path,
        )

    def get_all_activities(self, time_config):
        weekday_activities = [
            activity for activity in time_config["step_activities"]["weekday"].values()
        ]
        weekend_activities = [
            activity for activity in time_config["step_activities"]["weekend"].values()
        ]
        return set(chain(*(weekday_activities + weekend_activities)))

    def initialize_commute(self, commute_options):
        if "commuteunits" in commute_options:
            self.commute_unit_distributor = CommuteUnitDistributor(
                self.world.commutehubs.members
            )
        if "commutecityunits" in commute_options:
            self.commute_city_unit_distributor = CommuteCityUnitDistributor(
                self.world.commutecities.members
            )

    def distribute_commuters(self):
        if hasattr(self, "commute_unit_distributor"):
            self.commute_unit_distributor.distribute_people()
        if hasattr(self, "commute_city_unit_distributor"):
            self.commute_city_unit_distributor.distribute_people()

    def initialize_rail_travel(self, travel_options):
        if "travelunits" in travel_options:
            self.travelunit_distributor = TravelUnitDistributor(
                self.world.travelcities.members, self.world.travelunits.members
            )

    def distribute_rail_out(self):
        if hasattr(self, "travelunit_distributor"):
            self.travelunit_distributor.distirbute_people_out()

    def distribute_rail_back(self):
        if hasattr(self, "travelunit_distributor"):
            self.travelunit_distributor.distribute_people_back()

    def check_inputs(self, time_config: dict):
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
        all_groups = self.activity_hierarchy
        for step, activities in time_config["step_activities"]["weekday"].items():
            assert all(group in all_groups for group in activities)

        for step, activities in time_config["step_activities"]["weekend"].items():
            assert all(group in all_groups for group in activities)

    def apply_activity_hierarchy(self, activities: List[str]) -> List[str]:
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
        activities.sort(key=lambda x: self.activity_hierarchy.index(x))
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

    def clear_world(self):
        """
        Removes everyone from all possible groups, and sets everyone's busy attribute
        to False.

        """
        for group_name in self.activities_to_groups(self.all_activities):
            if group_name in ["care_home_visits", "household_visits"]:
                continue
            grouptype = getattr(self.world, group_name)
            for group in grouptype.members:
                group.clear()

        for person in self.world.people.members:
            person.busy = False
            person.subgroups.leisure = None

    def get_subgroup_active(
            self, activities: List[str], person: "Person", date, duration, is_weekend
    ) -> "Subgroup":
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
                    # delta_time=duration,
                    # is_weekend=is_weekend,
                    # closed_venues=self.policies.find_closed_venues(date),
                )
            else:
                subgroup = getattr(person, activity)
            if subgroup is not None:
                return subgroup
        raise SimulatorError(
            "Attention! Some people do not have an activity in this timestep."
        )

    def kid_drags_guardian(
            self,
            kid: "Person",
            guardian: "Person",
            activities: List[str],
            date,
            duration,
            is_weekend,
    ):
        """
        A kid makes their guardian go home.

        Parameters
        ----------
        kid:
            kid that wants to take their guardian home
        guardian:
            guardian to be sent home
        activities:
            list of activities that take place at a given time step
        """

        if guardian is not None:
            if guardian.busy:
                guardian_subgroup = self.get_subgroup_active(
                    activities, guardian, date, duration, is_weekend
                )
                guardian_subgroup.remove(guardian)
            guardian.residence.append(guardian)

    def move_mild_kid_guardian_to_household(
            self, kid: "Person", activities: List[str], date, duration, is_weekend
    ):
        """
        Move  a kid and their guardian to the household, so no kid is left
        home alone.

        Parameters
        ----------
        kid:
            kid to be sent home
        activities:
            list of activities that take place at a given time step
        """
        possible_guardians = [
            housemate for housemate in kid.residence.group.people if housemate.age >= 18
        ]
        if len(possible_guardians) == 0:
            guardian = kid.find_guardian()
            self.kid_drags_guardian(
                kid, guardian, activities, date, duration, is_weekend
            )
        kid.residence.append(kid)

    def move_mild_ill_to_household(
            self, person: "Person", activities: List[str], date, duration, is_weekend
    ):
        """
        Move person with a mild illness to their households. For kids that will
        always happen, and if they are left alone at home they will also drag one
        of their guardians home. For adults, they will go home with a probability 
        given by stay_at_home_complacency

        Parameters
        ----------
        person:
            person to be sent home
        activities:
            list of activities that take place at a given time step
        """
        if person.age < self.min_age_home_alone:
            self.move_mild_kid_guardian_to_household(
                person, activities, date, duration, is_weekend
            )
        elif random.random() <= self.stay_at_home_complacency:
            person.residence.append(person)
        else:
            subgroup = self.get_subgroup_active(
                activities, person, date, duration, is_weekend
            )
            subgroup.append(person)

    def move_people_to_active_subgroups(
            self,
            activities: List[str],
            date: datetime = datetime(2020, 2, 2),
            days_from_start=0.0,
            duration=0.0,
            is_weekend=True,
    ):
        """
        Sends every person to one subgroup. If a person has a mild illness,
        they stay at home with a certain probability given by stay_at_home_complacency

        Parameters
        ----------
        active_groups:
            list of groups that are active at a time step
        """
        skip_activity_collection = self.policies.skip_activity_collection(
            date=date
        )
        stay_home_collection = self.policies.stay_home_collection(
            date=date
        )

        activities = self.apply_activity_hierarchy(activities)
        for person in self.world.people.members:
            if person.dead or person.busy:
                continue
            allowed_activities = skip_activity_collection(
                person, activities
            )
            if stay_home_collection(person, days_from_start):
                self.move_mild_ill_to_household(
                    person, allowed_activities, date, duration, is_weekend
                )
            else:
                subgroup = self.get_subgroup_active(
                    allowed_activities, person, date, duration, is_weekend
                )
                subgroup.append(person)

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
        if self.policies is not None:
            self.policies.apply_change_probabilities_leisure(
                self.timer.date, self.leisure
            )
        self.leisure.generate_leisure_probabilities_for_timestep(
            self.timer.duration,
            self.timer.is_weekend,
            self.policies.find_closed_venues(self.timer.date),
        )
        self.move_people_to_active_subgroups(
            activities,
            self.timer.date,
            self.timer.now,
            duration=self.timer.duration,
            is_weekend=self.timer.is_weekend,
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
            f"Date = {self.timer.date}, number of deaths =  {n_people}, number of infected = {len(self.world.people.infected)}"
        )

        if (
                self.policies.social_distancing
                and self.policies.social_distancing_start
                <= self.timer.date
                < self.policies.social_distancing_end
        ):

            self.interaction.beta = self.policies.apply_social_distancing_policy(
                self.beta_copy, self.timer.now
            )
        else:
            self.interaction.beta = self.beta_copy

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
        self.update_health_status(time=self.timer.now, duration=self.timer.duration)
        if self.logger:
            self.logger.log_infection_location(self.timer.date)
            self.logger.log_hospital_capacity(self.timer.date, self.world.hospitals)
        self.clear_world()

    def run(self):
        """
        Run simulation with n_seed initial infections

        Parameters
        ----------
        save:
            whether to save the last state of the world

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
            if self.seed:
                if (time >= self.seed.min_date) and (time <= self.seed.max_date):
                    self.seed.unleash_virus_per_region(time)
            self.do_timestep()


class SimulatorBox(Simulator):
    def __init__(
            self,
            world: World,
            interaction: Interaction,
            selector: InfectionSelector,
            activity_to_groups: dict,
            time_config: dict,
            seed: Optional["Seed"] = None,
            leisure: Optional["Leisure"] = None,
            min_age_home_alone: int = 15,
            stay_at_home_complacency: float = 0.95,
            policies=Policies(),
            save_path: str = "results",
            output_filename: str = "logger.hdf5",
            light_logger: bool = False,
    ):
        """
        Class to run an epidemic spread simulation on a box. It is 
        basically a wrapper around the Simualtor class, disabling
        the options that are not available in box mode, like
        moving ill people to households.

        Parameters
        ----------
        world: 
            instance of World class
        interaction:
            instance of Interaction class 
        infection:
            instance of Infection class
        activity_to_groups:
            mapping between an activity and its corresponding groups
        time_config:
            dictionary with temporal configuration to set up the simulation
        min_age_home_alone:
            minimum age of a child to be left alone at home when ill
        stay_at_home_complacency:
            probability that an ill person will not stay at home
        policies:
            policies to be implemented at different time steps
        save_path:
            path to save logger results
        """
        super().__init__(
            world,
            interaction,
            selector,
            activity_to_groups,
            time_config,
            seed,
            leisure,
            min_age_home_alone,
            stay_at_home_complacency,
            policies,
            save_path,
            output_filename,
            light_logger,
        )

    def kid_drags_guardian(
            self, kid: "Person", guardian: "Person", activities: List[str]
    ):
        # not available in box
        pass

    def move_mild_kid_guardian_to_household(self, kid: "Person", activities: List[str]):
        # not available in box
        pass

    def move_mild_ill_to_household(self, person: "Person", activities: List[str]):
        # not available in box
        pass

    def move_people_to_active_subgroups(self, activities: List[str]):
        """
        Sends every person to one subgroup. If a person has a mild illness,
        they stay at home with a certain probability given by stay_at_home_complacency

        Parameters
        ----------
        active_groups:
            list of groups that are active at a time step
        """
        activities = self.apply_activity_hierarchy(activities)
        for person in self.world.people.members:
            if person.dead or person.busy:
                continue
            subgroup = self.get_subgroup_active(activities, person)
            subgroup.append(person)
