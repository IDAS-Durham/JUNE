import yaml
import logging

from covid.time import Timer
from covid import interaction
from covid.infection import Infection

default_config_filename = Path(__file__).parent.parent / "configs/defaults/world.yaml"


sim_logger = logging.getLogger(__name__)

valid_group_hierarchy = ['hospital', 'company', 'school', 'pub', 'household']

class Simulator:
    def __init__(self, world: "World", interaction: "Interaction", infection: Infection, config: dict):
        """
        Class to run an epidemic spread simulation on the world

        Parameters
        ----------
        world: 
            instance of World class
        interaction:
            instance of Interaction class, determines
             
        config:
            dictionary with configuration to set up the simulation
        """
        self.world = world
        self.config = config
        self.timer = Timer(self.config["time"])

    @classmethod
    def load_from_file(
        cls, world, config_filename=default_config_filename
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

        assert sum(config["time"]["step_duration"]["weekday"].values()) == 24

        return Simulator(cls, world, config)

    def set_active_group_to_people(self, active_groups: List["Groups"]):
        """
        Calls the set_active_members() method of each group, if the group
        is set as active

        Parameters
        ----------
        active_groups:
            list of groups that are active at a time step
        """
        #TODO: group hierarchy, order them
        #TODO:take care of temporary groups with group_maker 
        for group_name in active_groups:
            grouptype = getattr(self, group_name)
            if "pubs" in active_groups:
                world.group_maker.distribute_people(group_name)
            for group in grouptype.members:
                group.set_active_members()

    def set_allpeople_free(self):
        """ 
        Set everyone's active group to None, 
        ready for next time step

        """
        for person in self.world.people.members:
            person.active_group = None


    def seed_infections_group(self, group: "Group", n_infections: int):
        """
        Randomly pick people in group to seed the infection

        Parameters
        ----------
        group:
            group instance in which to seed the infection

        n_infections:
            number of random people to infect in the given group

        """
        choices = np.random.choice(group.size, n_infections, replace=False)
        infecter_reference = self.initialize_infection()
        for choice in choices:
            infecter_reference.infect_person_at_time(
                group.people[choice], self.timer.now
            )
        group.update_status_lists(self.timer.now, delta_time=0)

    def seed_infections_box(self, n_infections: int):
        """
        Randomly pick people in box to seed the infection

        Parameters
        ----------
        n_infections:
            number of random people to infect in the box

        """
        sim_logger.info("seed ", n_infections, "infections in box")
        choices = np.random.choice(self.people.members, n_infections, replace=False)
        infecter_reference = self.initialize_infection()
        for choice in choices:
            infecter_reference.infect_person_at_time(choice, self.timer.now)
        self.boxes.members[0].update_status_lists(self.timer.now, delta_time=0)

    def do_timestep(self):
        """
        Perform a time step in the simulation

        """
        active_groups = self.timer.active_groups()
        if not active_groups or len(active_groups) == 0:
            world_logger.info("==== do_timestep(): no active groups found. ====")
            return
        # update people (where they are according to time)
        self.set_active_group_to_people(active_groups)
        # infect people in groups
        group_instances = [getattr(self, group) for group in active_groups]
        for group_type in group_instances:
            for group in group_type.members:
                self.interaction.time_step(self.timer.now, self.timer.duration, group)
        # Update people that recovered in hospitals
        for hospital in self.hospitals.members:
            hospital.update_status_lists(self.timer.now, delta_time=0)
        self.set_allpeople_free()

        active_groups = self.timer.active_groups()
        if active_groups == None or len(active_groups) == 0:
            sim_logger.info("==== do_timestep(): no active groups found. ====")
            return

        # TODO: update people's status that is currently in interaction
        # needs to change time_step updates before and after running interaction

        # i) Run on world people (health update status to infected only on susceptible people? is it different than recovered only on infected?
        # Do it within this loop
        # Update people that recovered in hospitals
        # TODO: only if hospitals are in the world
        # + this should be a method of Hospitals

    def run(self, n_seed: int = 100, n_days):
        """
        Run simulation with n_seed initial infections

        Parameters
        ----------
        n_seed:
            number of initial infections

        """
        sim_logger.info(
            f"Starting group_dynamics for {self.timer.total_days} days at day {self.timer.day}"
        )
        if self.box_mode:
            self.seed_infections_box(n_seed)
        else:
            for household in self.households.members:
                self.seed_infections_group(household, 1)
        sim_logger.info(
            f"starting the loop ..., at {self.timer.day} days, to run for {self.timer.total_days} days"
        )

        for day in self.timer:
            if day > self.timer.total_days:
                break
            self.logger.log_timestep(day)
            self.do_timestep(self.timer)
