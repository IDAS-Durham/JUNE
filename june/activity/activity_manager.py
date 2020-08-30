import logging
from datetime import datetime
from itertools import chain
from typing import List, Optional
from collections import defaultdict
import numpy as np

from june.demography import Person
from june.exc import SimulatorError
from june.groups import Subgroup
from june.groups.commute.commutecityunit_distributor import CommuteCityUnitDistributor
from june.groups.commute.commuteunit_distributor import CommuteUnitDistributor
from june.groups.leisure import Leisure
from june.groups.travel.travelunit_distributor import TravelUnitDistributor
from june.policy import (
    IndividualPolicies,
    LeisurePolicies,
    MedicalCarePolicies,
    InteractionPolicies,
)
from june.mpi_setup import mpi_comm, mpi_size, mpi_rank

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


def _get_supergroup_from_group(group_name):
    if group_name == "grocery":
        return "groceries"
    elif group_name == "company":
        return "companies"
    else:
        return group_name + "s"


def _count_people_in_dict(people_from_abroad_dict):
    ret = 0
    for group_spec in people_from_abroad_dict:
        for group_id in people_from_abroad_dict[group_spec]:
            for subgroup_type in people_from_abroad_dict[group_spec][group_id]:
                ret += len(people_from_abroad_dict[group_spec][group_id][subgroup_type])
    return ret


def _update_data(people_from_abroad, data):
    for group_spec in data:
        if group_spec not in people_from_abroad:
            people_from_abroad[group_spec] = {}
        for group_id in data[group_spec]:
            if group_id not in people_from_abroad[group_spec]:
                people_from_abroad[group_spec][group_id] = {}
            for subgroup_type in data[group_spec][group_id]:
                if subgroup_type not in people_from_abroad[group_spec][group_id]:
                    people_from_abroad[group_spec][group_id][subgroup_type] = {}
                for person_id, person_data in data[group_spec][group_id][
                    subgroup_type
                ].items():
                    people_from_abroad[group_spec][group_id][subgroup_type][
                        person_id
                    ] = person_data


class ActivityManager:
    def __init__(
        self,
        world,
        policies,
        timer,
        all_activities,
        activity_to_groups: dict,
        leisure: Optional[Leisure] = None,
        min_age_home_alone: int = 15,
    ):
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

        self.furlough_ratio = 0
        self.key_ratio = 0
        self.random_ratio = 0
        for person in self.world.people:
            if person.lockdown_status == "furlough":
                self.furlough_ratio += 1
            elif person.lockdown_status == "key_worker":
                self.key_ratio += 1
            elif person.lockdown_status == "random":
                self.random_ratio += 1
        if self.furlough_ratio != 0 and self.key_ratio != 0 and self.random_ratio != 0:
            self.furlough_ratio /= (
                self.furlough_ratio + self.key_ratio + self.random_ratio
            )
            self.key_ratio /= self.furlough_ratio + self.key_ratio + self.random_ratio
            self.random_ratio /= (
                self.furlough_ratio + self.key_ratio + self.random_ratio
            )
        else:
            self.furlough_ratio = None
            self.key_ratio = None
            self.random_ratio = None

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
        return list(chain.from_iterable(groups))

    def move_to_active_subgroup(
        self, activities: List[str], person: Person
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
                subgroup = self.get_personal_subgroup(person=person, activity=activity)
            if subgroup is not None:
                if subgroup.external:
                    person.busy = True
                    # this person goes to another MPI domain
                    return subgroup
                subgroup.append(person)
                return
        raise SimulatorError(
            "Attention! Some people do not have an activity in this timestep."
        )

    def get_personal_subgroup(self, person: "Person", activity: str) -> "Subgroup":
        """
        Find the subgroup a person belongs to for a particular activity.
        
        Parameters
        ----------
        person:
            person that is looking for a subgroup 
        activity:
            the activity the person wants to find a subgroup for
        Returns
        -------
        Subgroup for activity
        """
        return getattr(person, activity)

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
                self.policies.leisure_policies.apply(
                    date=self.timer.date, leisure=self.leisure,
                )
            self.leisure.generate_leisure_probabilities_for_timestep(
                delta_time=self.timer.duration,
                is_weekend=self.timer.is_weekend,
                working_hours="primary_activity" in activities,
            )
        n_people_going_abroad, to_send_abroad = self.move_people_to_active_subgroups(
            activities, self.timer.date, self.timer.now,
        )
        (
            people_from_abroad,
            n_people_from_abroad,
        ) = self.send_and_receive_people_from_abroad(to_send_abroad)
        return people_from_abroad, n_people_from_abroad, n_people_going_abroad

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
        active_individual_policies = self.policies.individual_policies.get_active(
            date=date
        )
        activities = self.apply_activity_hierarchy(activities)
        to_send_abroad = {}
        n_people_going_abroad = 0
        for person in self.world.people.members:
            if person.dead or person.busy:
                continue
            allowed_activities = self.policies.individual_policies.apply(
                active_policies=active_individual_policies,
                person=person,
                activities=activities,
                days_from_start=days_from_start,
                furlough_ratio=self.furlough_ratio,
                key_ratio=self.key_ratio,
                random_ratio=self.random_ratio,
            )
            ret = self.move_to_active_subgroup(allowed_activities, person)
            if ret is not None:
                n_people_going_abroad += 1
                if ret.domain_id not in to_send_abroad:
                    to_send_abroad[ret.domain_id] = {}  # allocate domain id
                if ret.group_spec not in to_send_abroad[ret.domain_id]:
                    to_send_abroad[ret.domain_id][ret.group_spec] = {}
                if ret.group_id not in to_send_abroad[ret.domain_id][ret.group_spec]:
                    to_send_abroad[ret.domain_id][ret.group_spec][ret.group_id] = {}
                if (
                    ret.subgroup_type
                    not in to_send_abroad[ret.domain_id][ret.group_spec][ret.group_id]
                ):
                    to_send_abroad[ret.domain_id][ret.group_spec][ret.group_id][
                        ret.subgroup_type
                    ] = {}
                if person.infected:
                    to_send_abroad[ret.domain_id][ret.group_spec][ret.group_id][
                        ret.subgroup_type
                    ][person.id] = {
                        "inf_prob": person.infection.transmission.probability,
                        "susc": 0.0,
                        "dom": mpi_rank,
                    }
                else:
                    to_send_abroad[ret.domain_id][ret.group_spec][ret.group_id][
                        ret.subgroup_type
                    ][person.id] = {
                        "inf_prob": 0.0,
                        "susc": person.susceptibility,
                        "dom": mpi_rank,
                    }
        return n_people_going_abroad, to_send_abroad

    def send_and_receive_people_from_abroad(self, to_send_abroad):
        # send people abroad
        people_from_abroad = {}
        n_people_from_abroad = 0
        for rank in range(mpi_size):
            if rank == mpi_rank:
                # my turn to send my data
                for rank_receiving in range(mpi_size):
                    if rank == rank_receiving:
                        continue
                    if rank_receiving in to_send_abroad:
                        n_people_this_rank = _count_people_in_dict(
                            to_send_abroad[rank_receiving]
                        )
                        #print(
                        #    f"I am rank {mpi_rank} sending {n_people_this_rank} to {rank_receiving}"
                        #)
                        mpi_comm.send(
                            to_send_abroad[rank_receiving],
                            dest=rank_receiving,
                            tag=rank_receiving,
                        )
                        continue
                    #print(f"I am rank {mpi_rank} sending nothing to {rank_receiving}")
                    mpi_comm.send(None, dest=rank_receiving, tag=rank_receiving)
            else:
                # I have to listen
                # for rank_sending_to_me in range(mpi_size):
                #    if rank_sending_to_me == mpi_rank:
                #        break
                data = mpi_comm.recv(source=rank, tag=mpi_rank)
                if data is not None:
                    n_people_this_rank = _count_people_in_dict(data)
                    #print(
                    #    f"I am rank {mpi_rank} and I have received {n_people_this_rank} people from {rank}"
                    #)
                    _update_data(people_from_abroad, data)
                    n_people_from_abroad += n_people_this_rank
                # break
        return people_from_abroad, n_people_from_abroad
