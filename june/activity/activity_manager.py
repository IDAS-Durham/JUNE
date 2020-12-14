import logging
from datetime import datetime
from itertools import chain
from typing import List, Optional
from collections import defaultdict
import numpy as np
from time import perf_counter
from time import time as wall_clock

from june.demography import Person
from june.exc import SimulatorError
from june.groups import Subgroup
from june.event import Events
from june.groups.leisure import Leisure
from june.groups.travel import Travel
from june.policy import (
    IndividualPolicies,
    LeisurePolicies,
    MedicalCarePolicies,
    InteractionPolicies,
)
from june.mpi_setup import (
    mpi_comm,
    mpi_size,
    mpi_rank,
    MovablePeople,
)

logger = logging.getLogger("activity_manager")
if mpi_rank > 0:
    logger.propagate = False

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
        activity_to_super_groups: dict,
        events: Optional[Events] = None,
        leisure: Optional[Leisure] = None,
        travel: Optional[Travel] = None,
    ):
        self.policies = policies
        if self.policies is not None:
            self.policies.init_policies(world=world)
        self.events = events
        if self.events is not None:
            self.events.init_events(world=world)
        self.world = world
        self.timer = timer
        self.leisure = leisure
        self.travel = travel
        self.all_activities = all_activities

        if self.world.box_mode:
            self.activity_to_super_group_dict = {
                "box": ["boxes"],
            }
        else:
            self.activity_to_super_group_dict = {
                "medical_facility": activity_to_super_groups.get(
                    "medical_facility", []
                ),
                "primary_activity": activity_to_super_groups.get(
                    "primary_activity", []
                ),
                "leisure": activity_to_super_groups.get("leisure", []),
                "residence": activity_to_super_groups.get("residence", []),
                "commute": activity_to_super_groups.get("commute", []),
                "rail_travel": activity_to_super_groups.get("rail_travel", []),
            }

    @property
    def all_super_groups(self):
        return self.activities_to_super_groups(self.all_activities)

    @property
    def active_super_groups(self):
        return self.activities_to_super_groups(self.timer.activities)

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

    def activities_to_super_groups(self, activities: List[str]) -> List[str]:
        """
        Converts activities into Supergroups, the interaction will run over these Groups.

        Parameters
        ---------
        activities:
            list of activities that take place at a given time step
        Returns
        -------
        List of groups that are active.
        """
        return list(
            chain.from_iterable(
                self.activity_to_super_group_dict[activity] for activity in activities
            )
        )

    def get_personal_subgroup(self, person: "Person", activity: str):
        return getattr(person, activity)

    def do_timestep(self, return_to_send_abroad=False):
        # get time data
        date = self.timer.date
        is_weekend = self.timer.is_weekend
        activities = self.apply_activity_hierarchy(self.timer.activities)
        delta_time = self.timer.duration
        # apply leisure policies
        if self.leisure is not None:
            if self.policies is not None:
                self.policies.leisure_policies.apply(date=date, leisure=self.leisure)
            self.leisure.generate_leisure_probabilities_for_timestep(
                delta_time=delta_time,
                is_weekend=is_weekend,
                working_hours="primary_activity" in activities,
            )
        # apply events
        if self.events is not None:
            self.events.apply(
                date=date,
                world=self.world,
                activities=activities,
                is_weekend=is_weekend,
            )
        # move people to subgroups and get going abroad people
        to_send_abroad = self.move_people_to_active_subgroups(
            activities=activities, date=date, days_from_start=self.timer.now
        )
        (
            people_from_abroad,
            n_people_from_abroad,
            n_people_going_abroad,
        ) = self.send_and_receive_people_from_abroad(to_send_abroad)
        if return_to_send_abroad:
            return people_from_abroad, n_people_from_abroad, n_people_going_abroad, to_send_abroad
        else:
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
        to_send_abroad = MovablePeople()
        for person in self.world.people:
            if person.dead or person.busy:
                continue
            allowed_activities = self.policies.individual_policies.apply(
                active_policies=active_individual_policies,
                person=person,
                activities=activities,
                days_from_start=days_from_start,
            )
            external_subgroup = self.move_to_active_subgroup(
                allowed_activities, person, to_send_abroad
            )
            if external_subgroup is not None:
                to_send_abroad.add_person(person, external_subgroup)

        return to_send_abroad

    def move_to_active_subgroup(
        self, activities: List[str], person: Person, to_send_abroad=None
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
                    person=person, to_send_abroad=to_send_abroad
                )
            elif activity == "commute":
                subgroup = self.travel.get_commute_subgroup(person=person)
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

    def send_and_receive_people_from_abroad(self, movable_people):
        """
        Deal with the MPI comms.
        """
        n_people_going_abroad = 0
        n_people_from_abroad = 0
        tick, tickw = perf_counter(), wall_clock()
        reqs = []

        for rank in range(mpi_size):

            if mpi_rank == rank:
                continue
            keys, data, n_this_rank = movable_people.serialise(rank)
            if n_this_rank:
                reqs.append(mpi_comm.isend(keys, dest=rank, tag=100))
                reqs.append(mpi_comm.isend(data, dest=rank, tag=200))
                n_people_going_abroad += n_this_rank
            else:
                reqs.append(mpi_comm.isend(None, dest=rank, tag=100))
                reqs.append(mpi_comm.isend(None, dest=rank, tag=200))

        # now it has all been sent, we can start the receiving.

        for rank in range(mpi_size):

            if rank == mpi_rank:
                continue
            keys = mpi_comm.recv(source=rank, tag=100)
            data = mpi_comm.recv(source=rank, tag=200)

            if keys is not None:
                movable_people.update(rank, keys, data)
                n_people_from_abroad += data.shape[0]

        for r in reqs:
            r.wait()

        tock, tockw = perf_counter(), wall_clock()
        logger.info(
            f"CMS: People COMS for rank {mpi_rank}/{mpi_size} - {tock - tick},{tockw - tickw} - {self.timer.date}"
        )
        return movable_people.skinny_in, n_people_from_abroad, n_people_going_abroad
