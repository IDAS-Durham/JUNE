import os
import yaml
import logging
import logging.config


def get_creation_logger(self, config_file: str = None):
    """
    Create logger to make debugging easier
    """
    if config_file is None:
        config_file = self.configs_dir + "config_create_world.yaml"
    if os.path.isfile(config_file):
        with open(config_file, 'rt') as f:
            log_config = yaml.safe_load(f.read())
            logging.config.dictConfig(log_config)
    else:
        print("The provided logging config file does not exist.")
        log_file = os.path.join(self.output_dir, "world_creation.log")
        logging.basicConfig(
            filename=log_file, level=logging.DEBUG
        )
