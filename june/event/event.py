from abc import ABC
import yaml
import datetime
import logging
from typing import Union, List

from june.utils import read_date, str_to_class
from june.paths import configs_path
from june.mpi_setup import mpi_rank

default_config_filename = configs_path / "defaults/event/events.yaml"
logger = logging.getLogger("events")
if mpi_rank > 0:
    logger.propagate = False


class Event(ABC):
    """
    This class represents an event. An event is a sequence of actions to the world,
    that can happen at the beginning of each time step during a defined period of time.
    """

    def __init__(
        self,
        start_time: Union[str, datetime.datetime],
        end_time: Union[str, datetime.datetime],
    ):
        self.start_time = read_date(start_time)
        self.end_time = read_date(end_time)

    def is_active(self, date: datetime.datetime):
        return self.start_time <= date < self.end_time

    def initialise(self, world):
        raise NotImplementedError

    def apply(self, world, simulator, activities, day_type):
        raise NotImplementedError


class Events:
    def __init__(self, events=None):
        self.events = events

    @classmethod
    def from_file(
        cls,
        config_file=default_config_filename,
        base_event_modules=("june.event",),
    ):
        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader) or {}
        events = []
        for event, event_data in config.items():
            camel_case_key = "".join(x.capitalize() or "_" for x in event.split("_"))
            if "start_time" not in event_data:
                for event_i, event_data_i in event_data.items():
                    if (
                        "start_time" not in event_data_i.keys()
                        or "end_time" not in event_data_i.keys()
                    ):
                        raise ValueError("event config file not valid.")
                    events.append(
                        str_to_class(camel_case_key, base_event_modules)(**event_data_i)
                    )
            else:
                events.append(
                    str_to_class(camel_case_key, base_event_modules)(**event_data)
                )
        return cls(events)

    def init_events(self, world):
        logger.info(f"Initialising events...")
        for event in self.events:
            event.initialise(world=world)
            logger.info(f"Event {event.__class__.__name__} initialised")

    def apply(
        self,
        date,
        world,
        simulator,
        activities: List[str],
        day_type: bool,
    ):
        for event in self.events:
            if event.is_active(date=date):
                event.apply(
                    world=world,
                    simulator=simulator,
                    activities=activities,
                    day_type=day_type,
                )
