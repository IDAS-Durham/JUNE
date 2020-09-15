import logging.config
import os

import yaml

from june import paths
from . import box
from . import commute_rail_travel
from . import demography
from . import distributors
from . import groups
from . import infection
from . import interaction
from . import simulator
from . import activity
from .demography import Person
from .exc import GroupException
from .time import Timer
from .world import World

default_logging_config_filename = (
        paths.configs_path /
        "config_world_creation_logger.yaml"
)

if os.path.isfile(default_logging_config_filename):
    with open(default_logging_config_filename, 'rt') as f:
        log_config = yaml.safe_load(f.read())
        logging.config.dictConfig(log_config)
else:
    print("The logging config file does not exist.")
    log_file = os.path.join("./", "world_creation.log")
    logging.basicConfig(
        filename=log_file, level=logging.DEBUG
    )
