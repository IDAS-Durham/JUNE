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

    def __init__(self):
        super().__init__()


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
    def __init__(self, city):
        super().__init__()
        self.city = city

    @property
    def area(self):
        return self.city.super_area.areas[0]

    @property
    def super_area(self):
        return self.city.super_area

    @property 
    def coordinates(self):
        return self.area.coordinates


class CityTransports(Transports):
    """
    Inner city transports
    """


class InterCityTransport(Transport):
    """
    Transport between cities.
    """
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



class InterCityTransports(Transports):
    """
    Inter city transports
    """


class InterRegionalTransport(Transport):
    """
    Transport between regions
    """


class InterRegionalTransports(Transports):
    """
    Transports between regions
    """
