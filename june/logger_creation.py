import os
import yaml
import logging
import logging.config
from pathlib import Path

default_logging_config_filename = Path(__file__).parent.parent / \
    "configs/config_world_creation_logger.yaml"


def logging(config_file: str = None):
    """
    Create logger to make debugging easier
    """
    if config_file is None:
        config_file = default_logging_config_filename
    if os.path.isfile(config_file):
        print("Set up logger with default settings")
        with open(config_file, 'rt') as f:
            log_config = yaml.safe_load(f.read())
            logging.config.dictConfig(log_config)
    else:
        print("The provided logging config file does not exist.")
        log_file = os.path.join("./", "world_creation.log")
        logging.basicConfig(
            filename=log_file, level=logging.DEBUG
        )
