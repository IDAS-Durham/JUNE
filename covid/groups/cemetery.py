from covid.groups import Group

class Cemetery(Group):
    def __init__(self):
        self.spec = "cemetery"
        self.people = []

    def add(self,person):
        self.people.append(person)
        
    def must_timestep(self):
        return False
        
    def update_status_lists(self, time=1):
        pass
        #print ("=== update status list for cemetery with ",self.size," people ===")

    def set_active_members(self):
        pass
    
    @property
    def size(self):
        return len(self.people)

class Cemeteries:
    def __init__(self, world):
        self.world = world
        self.members = []
        self.members.append(Cemetery())

    def get_nearest(self,person):
        return self.members[0]
