import pytest
import os

from covid.groups.people import person as p

test_data_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "data", "census_data", "commute.csv")

class TestHealthInformation:

