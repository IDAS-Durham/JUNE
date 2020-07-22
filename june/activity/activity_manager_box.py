from typing import List

from june.demography.person import Person
from june.activity.activity_manager import ActivityManager
from june.exc import SimulatorError


class ActivityManagerBox(ActivityManager):
    def kid_drags_guardian(self, guardian):
        # not available in box
        pass

    def move_mild_kid_guardian_to_household(self, kid: "Person"):
        # not available in box
        pass

    def move_mild_ill_to_household(self, person: "Person"):
        # not available in box
        pass

    def move_people_to_active_subgroups(self, activities: List[str]):
        """
        Sends every person to one subgroup. If a person has a mild illness,
        they stay at home

        Parameters
        ----------
        active_groups:
            list of groups that are active at a time step
        """
        activities = self.apply_activity_hierarchy(activities)
        for person in self.world.people.members:
            if person.dead or person.busy:
                continue
            self.move_to_active_subgroup(activities, person)

    def move_to_active_subgroup(
            self, activities: List[str], person: "Person"
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
            subgroup = getattr(person, activity)
            if subgroup is not None:
                subgroup.append(person)
            return
        raise SimulatorError(
            "Attention! Some people do not have an activity in this timestep."
        )

    def do_timestep(self):
        activities = self.timer.activities

        if self.policies is not None:
            self.policies.apply_change_probabilities_leisure(
                self.timer.date, self.leisure
            )
        self.move_people_to_active_subgroups(activities, )
