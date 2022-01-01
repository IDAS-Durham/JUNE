import operator
from typing import List, Optional, Dict
from random import random
import numpy as np
import datetime
import yaml
import logging
from pathlib import Path

from june import paths
from june.utils import read_date

logger = logging.getLogger("vaccination")


default_config_filename = (
    paths.configs_path / "defaults/epidemiology/vaccines/vaccination_campaigns.yaml"
)
#TODO:
# i) Reformat vaccination campaign
# ii) Do as in symptoms with update trajectory to avoid searchsorted
# iii) Vaccinate individually given age, region, n doses, and vaccine type (could be made of combinations)

class VaccinationCampaign:
    pass
    
class VaccinationCampaigns:
    pass
