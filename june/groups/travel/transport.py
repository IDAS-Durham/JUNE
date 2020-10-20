from enum import IntEnum
import numpy as np
from typing import List

from june.groups import Group, Supergroup


class Transport(Group):
    """
    A class representing a transport unit.
    """

    class SubgroupType(IntEnum):
        passengers = 0

    def __init__(self, station):
        super().__init__()
        self.station = station

    @property
    def area(self):
        return self.station.super_area.areas[0]

    @property
    def super_area(self):
        return self.station.super_area

    @property
    def coordinates(self):
        return self.area.coordinates


class Transports(Supergroup):
    """
    A collection of transport units.
    """

    def __init__(self, transports: List[Transport]):
        super().__init__(transports)


class CityTransport(Transport):
    """
    Inner city transport
    """


class CityTransports(Transports):
    """
    Inner city transports
    """


class InterCityTransport(Transport):
    """
    Transport between cities.
    """


class InterCityTransports(Transports):
    """
    Inter city transports
    """
