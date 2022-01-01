import datetime
import pytest
import numpy as np

from june.groups import CareHome
from june.demography import Person, Population

from june.epidemiology.vaccines import Vaccine, Vaccines
from june.epidemiology.infection.infection import Delta, Omicron
from june.records import Record, RecordReader

delta_id = Delta.infection_id()
omicron_id = Omicron.infection_id()


