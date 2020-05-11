from june.groups.group import Group
from june.logger_creation import logger
from enum import IntEnum


class Cemetery(Group):
    class GroupType(IntEnum):
        default = 0
        
    def __init__(self):
        super().__init__("Cemetery", "cemetery")

    def must_timestep(self):
        return False

    def update_status_lists(self, time=1, delta_time=1):
        pass

    def set_active_members(self):
        pass


class Cemeteries:
    def __init__(self, world=None):
        self.world = world
        self.members = [Cemetery()]

    def get_nearest(self, person):
        return self.members[0]
