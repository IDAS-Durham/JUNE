import logging
from datetime import datetime
from itertools import chain
from typing import List, Optional

from june.demography import Person
from june.exc import SimulatorError
from june.groups import Subgroup
from june.groups.commute.commutecityunit_distributor import CommuteCityUnitDistributor
from june.groups.commute.commuteunit_distributor import CommuteUnitDistributor
from june.groups.leisure import Leisure
from june.groups.travel.travelunit_distributor import TravelUnitDistributor

logger = logging.getLogger(__name__)

activity_hierarchy = [
    "box",
    "medical_facility",
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
                "medical_facility": activity_to_groups.get("medical_facility", []),
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

    @property
    def active_groups(self):
        return self.activities_to_groups(self.timer.activities)

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
        if "commute" in activities:
            self.distribute_commuters()
        if "rail_travel_out" in activities:
            self.distribute_rail_out()
        if "rail_travel_back" in activities:
            self.distribute_rail_back()
        if self.leisure is not None:
            if self.policies is not None:
                leisure_policies = self.policies.get_active_leisure_policies(
                    date=self.timer.date
                )
                self.policies.apply_leisure_policies(
                    policies=leisure_policies,
                    date=self.timer.date,
                    leisure=self.leisure,
                )
            self.leisure.generate_leisure_probabilities_for_timestep(
                self.timer.duration,
                self.timer.is_weekend,
                self.policies.find_closed_venues(self.timer.date),
            )
        self.move_people_to_active_subgroups(
            activities, self.timer.date, self.timer.now,
        )

    @staticmethod
    def kid_drags_guardian(guardian: "Person",):
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
        # skip_activity_collection = self.policies.skip_activity_collection(date=date)
        # stay_home_collection = self.policies.stay_home_collection(date=date)
        individual_policies = self.policies.get_active_individual_policies(date=date)
        activities = self.apply_activity_hierarchy(activities)
        for person in self.world.people.members:
            if person.dead or person.busy:
                continue
            allowed_activities = self.policies.apply_individual_policies(
                policies=individual_policies,
                person=person,
                activities=activities,
                days_from_start=days_from_start,
            )
            # if stay_home_collection(person, days_from_start):
            #    self.move_mild_ill_to_household(person)
            # else:
            #    allowed_activities = skip_activity_collection(person, activities, )
            #    self.move_to_active_subgroup(allowed_activities, person)
            # allowed_activities = skip_activity_collection(person, activities,)
            self.move_to_active_subgroup(allowed_activities, person)
