import sys
from june.groups.pub import PubFiller

class GroupMaker:
    def __init__(self, simulator):
        self.simulator = simulator
        #self.world = world
        print ("initialized group maker")
        self.pubfiller = PubFiller(world)
        
    def distribute_people(self,grouptype):
        if grouptype=="pubs":
            #print ("distribute people for ",grouptype,"in",
            #       len(self.world.areas.members),"areas.")
            for area in self.world.areas.members:
                self.pubfiller.fill(area)
            #self.make_histogram()
        if grouptype=='commute':
            self.simulator.commuteunit_distributor.distribute_people()
            self.simulator.commutecityunit_distribute.distribute_people()

    def make_histogram(self):
        import matplotlib.pyplot as plt
        customers = []
        for pub in self.world.pubs.members:
            if len(pub.people)>0:
                customers.append(len(pub.people))
        plt.hist(customers,bins=100)
        plt.show()
        sys.exit(1)
