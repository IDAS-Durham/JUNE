import os
import yaml
import logging
import logging.config
from pathlib import Path

default_logging_config_filename = (
    Path(os.path.abspath(__file__)).parent.parent /
    "configs/config_world_creation_logger.yaml"
)

def logger(config_file: str):
    """
    Create logger to make debugging easier
    """
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
