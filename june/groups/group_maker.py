import sys
from june.groups.pub import Pubs

class GroupMaker:
    def __init__(self,world):
        self.world = world
        print ("initialized group maker")
        self.pubs = self.world.pubs
        
    def distribute_people(self,grouptype):
        if grouptype=="pubs":
            print ("distribute people for ",grouptype,"in",
                   len(self.world.areas.members),"areas.")
            self.pubs.send_people_to_pub()
            self.make_histogram()

    def make_histogram(self):
        import matplotlib.pyplot as plt
        customers = []
        for pub in self.world.pubs.members:
            if len(pub.people)>0:
                customers.append(len(pub.people))
        plt.hist(customers,bins=100)
        plt.show()
        sys.exit(1)
