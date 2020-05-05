import yaml
import logging

from covid.time import Timer
from covid.interaction import *
from covid.infection import Infection

default_config_filename = Path(__file__).parent.parent / "configs/defaults/world.yaml"


sim_logger = logging.getLogger(__name__)


class Simulator:
    def __init__(self, world: "World", config: dict):
        """
        Class to run an epidemic spread simulation on the world

        Parameters
        ----------
        world: 
            instance of World class
             
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

    def initialize_interaction(self):
        """
        Initialize interaction from config file
        """
        # TODO: Interaction should have a from config file
        interaction_type = self.config["interaction"]["type"]
        if "parameters" in self.config["interaction"]:
            interaction_parameters = self.config["interaction"]["parameters"]
        else:
            interaction_parameters = {}
        interaction_class_name = "Interaction" + interaction_type.capitalize()
        interaction = globals()[interaction_class_name](
            interaction_parameters, self.world
        )
        return interaction

    def set_active_group_to_people(self, active_groups: List["Groups"]):
        """
        Calls the set_active_members() method of each group, if the group
        is set as active

        Parameters
        ----------
        active_groups:
            list of groups that are active at a time step
        """
        for group_name in active_groups:
            grouptype = getattr(self, group_name)
            if 'pubs' in active_groups:
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

    def initialize_infection(self):
        """
        Initialize infection from config file
        """

        # TODO: Infection should have a from config file
        if "parameters" in self.config["infection"]:
            infection_parameters = self.config["infection"]["parameters"]
        else:
            infection_parameters = {}
        if "transmission" in self.config["infection"]:
            transmission_type = self.config["infection"]["transmission"]["type"]
            transmission_parameters = self.config["infection"]["transmission"][
                "parameters"
            ]
            transmission_class_name = "Transmission" + transmission_type.capitalize()
        else:
            trans_class = "TransmissionConstant"
            transmission_parameters = {}
        trans_class = getattr(transmission, transmission_class_name)
        transmission_class = trans_class(**transmission_parameters)
        if "symptoms" in self.config["infection"]:
            symptoms_type = self.config["infection"]["symptoms"]["type"]
            symptoms_parameters = self.config["infection"]["symptoms"]["parameters"]
            symptoms_class_name = "Symptoms" + symptoms_type.capitalize()
        else:
            symptoms_class_name = "SymptomsGaussian"
            symptoms_parameters = {}
        symp_class = getattr(symptoms, symptoms_class_name)
        reference_health_index = HealthIndex().get_index_for_age(40)
        symptoms_class = symp_class(
            health_index=reference_health_index, **symptoms_parameters
        )
        infection = Infection(
            self.timer.now, transmission_class, symptoms_class, **infection_parameters
        )
        return infection

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
        if active_groups == None or len(active_groups) == 0:
            sim_logger.info("==== do_timestep(): no active groups found. ====")
            return
        self.set_active_group_to_people(active_groups)

        # TODO: update people's status that is currently in interaction
        # needs to change time_step updates before and after running interaction

        # i) Run on world people (health update status to infected only on susceptible people? is it different than recovered only on infected?
        # Do it within this loop
        groups_instances = [getattr(self, group) for group in active_groups]
        self.interaction.groups = groups_instances
        self.interaction.time_step()
        # Update people that recovered in hospitals
        # TODO: only if hospitals are in the world
        # + this should be a method of Hospitals
        for hospital in self.hospitals.members:
            hospital.update_status_lists(self.timer.now, delta_time=0)
        self.set_allpeople_free()

    def run(self, n_seed: int = 100):
        """
        Run simulation with n_seed initial infections

        Parameters
        ----------
        n_seed:
            number of initial infections

        """
        sim_logger.info(
            "Starting group_dynamics for ",
            self.timer.total_days,
            " days at day",
            self.timer.day,
        )
        if self.box_mode:
            self.seed_infections_box(n_seed)
        else:
            sim_logger.info(
                "Infecting individuals in their household,",
                "for in total ",
                len(self.households.members),
                " households.",
            )
            for household in self.households.members:
                self.seed_infections_group(household, 1)
        sim_logger.info(
            "starting the loop ..., at ",
            self.timer.day,
            " days, to run for ",
            self.timer.total_days,
            " days",
        )

        for day in self.timer:
            if day > self.timer.total_days:
                break
            self.logger.log_timestep(day)
            self.do_timestep(self.timer)
