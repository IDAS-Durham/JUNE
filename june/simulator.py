import logging
import datetime
import numpy as np
import pickle
import yaml
from itertools import chain
from typing import Optional, List, Dict, Union
from pathlib import Path
from time import perf_counter
from time import time as wall_clock
from mpi4py import MPI

from june import paths
from june.activity import ActivityManager, activity_hierarchy
from june.demography import Person, Activities
from june.exc import SimulatorError
from june.groups.leisure import Leisure
from june.groups.travel import Travel
from june.groups.group.interactive import InteractiveGroup
from june.epidemiology.epidemiology import Epidemiology
from june.interaction import Interaction
from june.policy import Policies
from june.event import Events
from june.time import Timer
from june.records import Record
from june.world import World
from june.mpi_setup import mpi_comm, mpi_size, mpi_rank, move_info
from june.utils.profiler import profile

default_config_filename = paths.configs_path / "config_example.yaml"

output_logger = logging.getLogger("simulator")
mpi_logger = logging.getLogger("mpi")
rank_logger = logging.getLogger("rank")
mpi_logger.propagate = False
if mpi_rank > 0:
    output_logger.propagate = False
    mpi_logger.propagate = False


def enable_mpi_debug(results_folder):
    from june.logging import MPIFileHandler

    logging_file = Path(results_folder) / "mpi.log"
    with open(logging_file, "w") as f:
        pass
    mh = MPIFileHandler(logging_file)
    rank_logger.addHandler(mh)


def _read_checkpoint_dates_from_file(config_filename):
    with open(config_filename) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return _read_checkpoint_dates(config.get("checkpoint_save_dates", None))


def _read_checkpoint_dates(checkpoint_dates):
    if isinstance(checkpoint_dates, datetime.date):
        return (checkpoint_dates,)
    elif type(checkpoint_dates) == str:
        return (datetime.datetime.strptime(checkpoint_dates, "%Y-%m-%d"),)
    elif type(checkpoint_dates) in [list, tuple]:
        ret = []
        for date in checkpoint_dates:
            if type(date) == str:
                dd = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            else:
                dd = date
            ret.append(dd)
        return tuple(ret)
    else:
        return ()


class Simulator:
    ActivityManager = ActivityManager

    def __init__(
        self,
        world: World,
        interaction: Interaction,
        timer: Timer,
        activity_manager: ActivityManager,
        epidemiology: Epidemiology,
        events: Optional[Events] = None,
        record: Optional[Record] = None,
        checkpoint_save_dates: List[datetime.date] = None,
        checkpoint_save_path: str = None,
    ):
        """
        Class to run an epidemic spread simulation on the world.

        Parameters
        ----------
        world:
            instance of World class
        """
        self.activity_manager = activity_manager
        self.world = world
        self.interaction = interaction
        self.events = events
        self.timer = timer
        self.epidemiology = epidemiology
        if self.epidemiology:
            self.epidemiology.set_medical_care(
                world=world, activity_manager=activity_manager
            )
            self.epidemiology.set_immunity(self.world.people)
        if self.events is not None:
            self.events.init_events(world=world)
        # self.comment = comment
        self.checkpoint_save_dates = _read_checkpoint_dates(checkpoint_save_dates)
        if self.checkpoint_save_dates:
            if not checkpoint_save_path:
                checkpoint_save_path = "results/checkpoints"
            self.checkpoint_save_path = Path(checkpoint_save_path)
            self.checkpoint_save_path.mkdir(parents=True, exist_ok=True)
        self.record = record
        if self.record is not None and self.record.record_static_data:
            self.record.static_data(world=world)

    @classmethod
    def from_file(
        cls,
        world: World,
        interaction: Interaction,
        policies: Optional[Policies] = None,
        events: Optional[Events] = None,
        epidemiology: Optional[Epidemiology] = None,
        leisure: Optional[Leisure] = None,
        travel: Optional[Travel] = None,
        config_filename: str = default_config_filename,
        checkpoint_save_path: str = None,
        record: Optional[Record] = None,
    ) -> "Simulator":

        """
        Load config for simulator from world.yaml

        Parameters
        ----------
        leisure
        policies
        interaction
        world
        config_filename
            The path to the world yaml configuration
        comment
            A brief description of the purpose of the run(s)

        Returns
        -------
        A Simulator
        """
        checkpoint_save_dates = _read_checkpoint_dates_from_file(config_filename)
        timer = Timer.from_file(config_filename=config_filename)
        activity_manager = cls.ActivityManager.from_file(
            config_filename=config_filename,
            world=world,
            leisure=leisure,
            travel=travel,
            policies=policies,
            timer=timer,
        )
        return cls(
            world=world,
            interaction=interaction,
            timer=timer,
            events=events,
            activity_manager=activity_manager,
            epidemiology=epidemiology,
            record=record,
            checkpoint_save_dates=checkpoint_save_dates,
            checkpoint_save_path=checkpoint_save_path,
        )

    @classmethod
    def from_checkpoint(
        cls,
        world: World,
        checkpoint_load_path: str,
        interaction: Interaction,
        epidemiology: Optional[Epidemiology] = None,
        policies: Optional[Policies] = None,
        leisure: Optional[Leisure] = None,
        travel: Optional[Travel] = None,
        config_filename: str = default_config_filename,
        record: Optional[Record] = None,
        events: Optional[Events] = None,
        reset_infections=False,
    ):
        from june.hdf5_savers.checkpoint_saver import generate_simulator_from_checkpoint

        return generate_simulator_from_checkpoint(
            world=world,
            checkpoint_path=checkpoint_load_path,
            interaction=interaction,
            policies=policies,
            epidemiology=epidemiology,
            leisure=leisure,
            travel=travel,
            config_filename=config_filename,
            record=record,
            events=events,
            reset_infections=reset_infections,
        )

    def clear_world(self):
        """
        Removes everyone from all possible groups, and sets everyone's busy attribute
        to False.
        """
        for super_group_name in self.activity_manager.all_super_groups:
            if "visits" in super_group_name:
                continue
            grouptype = getattr(self.world, super_group_name)
            if grouptype is not None:
                for group in grouptype.members:
                    group.clear()

        for person in self.world.people.members:
            person.busy = False
            person.subgroups.leisure = None

    def do_timestep(self):
        """
        Perform a time step in the simulation. First, ActivityManager is called
        to send people to the corresponding subgroups according to the current daytime.
        Then we iterate over all the groups and create an InteractiveGroup object, which
        extracts the relevant information of each group to carry the interaction in it.
        We then pass the interactive group to the interaction module, which returns the ids
        of the people who got infected. We record the infection locations, update the health
        status of the population, and distribute scores among the infectors to calculate R0.
        """
        output_logger.info("==================== timestep ====================")
        tick, tickw = perf_counter(), wall_clock()
        if self.activity_manager.policies is not None:
            self.activity_manager.policies.interaction_policies.apply(
                date=self.timer.date,
                interaction=self.interaction,
            )
            self.activity_manager.policies.regional_compliance.apply(
                date=self.timer.date, regions=self.world.regions
            )
            if self.activity_manager.policies.vaccine_distribution is not None:
                self.activity_manager.policies.vaccine_distribution.update_vaccinated(
                    self.world.people, date=self.timer.date
                )
        activities = self.timer.activities
        # apply events
        if self.events is not None:
            self.events.apply(
                date=self.timer.date,
                world=self.world,
                activities=activities,
                day_type=self.timer.day_type,
                simulator=self,
            )
        if not activities or len(activities) == 0:
            output_logger.info("==== do_timestep(): no active groups found. ====")
            return
        (
            people_from_abroad_dict,
            n_people_from_abroad,
            n_people_going_abroad,
            to_send_abroad,  # useful for knowing who's MPI-ing, so can send extra info as needed.
        ) = self.activity_manager.do_timestep()
        tick_interaction = perf_counter()

        # get the supergroup instances that are active in this time step:
        active_super_groups = self.activity_manager.active_super_groups
        super_group_instances = []
        for super_group_name in active_super_groups:
            if "visits" not in super_group_name:
                super_group_instance = getattr(self.world, super_group_name)
                if super_group_instance is None or len(super_group_instance) == 0:
                    continue
                super_group_instances.append(super_group_instance)

        # for checking that people is conserved
        n_people = 0
        # count people in the cemetery
        for cemetery in self.world.cemeteries.members:
            n_people += len(cemetery.people)
        output_logger.info(
            f"Info for rank {mpi_rank}, "
            f"Date = {self.timer.date}, "
            f"number of deaths =  {n_people}, "
            f"number of infected = {len(self.world.people.infected)}"
        )

        # main interaction loop
        infected_ids = []  # ids of the newly infected people
        infection_ids = []  # ids of the viruses they got
        for super_group in super_group_instances:
            for group in super_group:
                if group.external:
                    continue
                else:
                    people_from_abroad = people_from_abroad_dict.get(
                        group.spec, {}
                    ).get(group.id, None)
                    (
                        new_infected_ids,
                        new_infection_ids,
                        group_size,
                    ) = self.interaction.time_step_for_group(
                        group=group,
                        people_from_abroad=people_from_abroad,
                        delta_time=self.timer.duration,
                        record=self.record,
                    )
                    infected_ids += new_infected_ids
                    infection_ids += new_infection_ids
                    n_people += group_size
        tock_interaction = perf_counter()
        rank_logger.info(
            f"Rank {mpi_rank} -- interaction -- {tock_interaction-tick_interaction}"
        )
        self.epidemiology.do_timestep(
            world=self.world,
            timer=self.timer,
            record=self.record,
            infected_ids=infected_ids,
            infection_ids=infection_ids,
            people_from_abroad_dict=people_from_abroad_dict,
        )
        tick, tickw = perf_counter(), wall_clock()
        mpi_comm.Barrier()
        tock, tockw = perf_counter(), wall_clock()
        rank_logger.info(f"Rank {mpi_rank} -- interaction_waiting -- {tock-tick}")

        # recount people active to check people conservation
        people_active = (
            len(self.world.people) + n_people_from_abroad - n_people_going_abroad
        )
        if n_people != people_active:
            raise SimulatorError(
                f"Number of people active {n_people} does not match "
                f"the total people number {people_active}.\n"
                f"People in the world {len(self.world.people)}\n"
                f"People going abroad {n_people_going_abroad}\n"
                f"People coming from abroad {n_people_from_abroad}\n"
                f"Current rank {mpi_rank}\n"
            )

        # remove everyone from their active groups
        self.clear_world()
        tock, tockw = perf_counter(), wall_clock()
        output_logger.info(
            f"CMS: Timestep for rank {mpi_rank}/{mpi_size} - {tock - tick},"
            f"{tockw-tickw} - {self.timer.date}\n"
        )
        mpi_logger.info(f"{self.timer.date},{mpi_rank},timestep,{tock-tick}")

    def run(self):
        """
        Run simulation with n_seed initial infections
        """
        output_logger.info(
            f"Starting simulation for {self.timer.total_days} days at day {self.timer.date},"
            f"to run for {self.timer.total_days} days"
        )
        self.clear_world()
        if self.record is not None:
            self.record.parameters(
                interaction=self.interaction,
                epidemiology=self.epidemiology,
                activity_manager=self.activity_manager,
            )
        while self.timer.date < self.timer.final_date:
            if self.epidemiology:
                self.epidemiology.infection_seeds_timestep(
                    self.timer, record=self.record
                )
            mpi_comm.Barrier()
            if mpi_rank == 0:
                rank_logger.info("Next timestep")
            self.do_timestep()
            if (
                self.timer.date.date() in self.checkpoint_save_dates
                and (self.timer.now + self.timer.duration).is_integer()
            ):  # this saves in the last time step of the day
                saving_date = self.timer.date.date()
                # we can resume consistenly
                output_logger.info(
                    f"Saving simulation checkpoint at {self.timer.date.date()}"
                )
                self.save_checkpoint(saving_date)
            next(self.timer)

    def save_checkpoint(self, saving_date):
        from june.hdf5_savers.checkpoint_saver import save_checkpoint_to_hdf5

        if mpi_size == 1:
            save_path = self.checkpoint_save_path / f"checkpoint_{saving_date}.hdf5"
        else:
            save_path = (
                self.checkpoint_save_path / f"checkpoint_{saving_date}.{mpi_rank}.hdf5"
            )
        save_checkpoint_to_hdf5(
            population=self.world.people,
            date=str(saving_date),
            hdf5_file_path=save_path,
        )
