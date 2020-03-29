import person
import sys
import random
import matplotlib
import matplotlib.pyplot as plt 

class Group:
    """
    A group of people enjoying social interactions.  It contains three lists,
    all people in the group, the healthy ones and the infected ones (we may 
    have to add the immune ones as well).

    This is very basic and we will have to specify derived classes with
    additional information - like household, work, commute - where some,
    like household groups are stable and others, like commute groups, are
    randomly assorted on a step-by-step base.

    The logic is that the group will enjoy one Interaction per time step,
    where the infection spreads, with a probablity driven by transmission
    probabilities and inteaction intensity, plus, possilby, individual
    susceptibility to become infected.

    TODO: we will have to decide in how far specific groups define behavioral
    patterns, which may be time-dependent.
    """
    def __init__(self,gname,gtype,gsize=-1,mode="None"):
        self.gname     = gname
        self.gtype     = gtype
        self.people    = []
        self.infected  = []
        self.healthy   = []
        if mode == "Test":
            for i in range (gsize):
                self.Add(person.Person(i,mode))

    def Add(self, p, time=0):
        if not isinstance(p, person.Person):
            print ("Error in Group.Add(",p,") is not a person.")
            print("--> Exit the code.")
            sys.exit()
        if p in self.people:
            print ("Tried to add already present person",p.Name(),
                   " to group ",self.gname,".")
            print("--> Ignore and proceed.")
        else:
            self.people.append(p)
            if (p.IsInfected(time)):
                self.infected.append(p)
            else:
                self.healthy.append(p)

    def UpdateLists(self,time=0):
        self.healthy.clear()
        self.infected.clear()
        for p in self.people:
            if p.IsHealthy(time):
                self.healthy.append(p)
            else:
                self.infected.append(p)

    def Empty(self,all=True):
        if all:
            self.people.clear();
        self.healthy.clear()
        self.infected.clear()
                
    def Number(self):
        return len(self.people)
    
    def NHealthy(self):
        return len(self.healthy)
        
    def NInfected(self):
        return len(self.infected)
    
    def People(self):
        return self.people

    def Healthy(self):
        return self.healthy
        
    def Infected(self):
        return self.infected

    def Output(self,plot=False,full=False):
        print ("==================================================")
        print ("Group ",self.gname,", type = ",self.gtype," with ",
               len(self.people)," people.")
        print("* ",self.NHealthy(),
              "(",round(self.NHealthy()/self.Number()*100),"%) are healthy, ",
              self.NInfected(),
              "(",round(self.NInfected()/self.Number()*100),"%) are infected.")
        ages = []
        M    = 0
        F    = 0
        for p in self.people:
            ages.append(p.Age())
            if p.Gender()=="F":
                F += 1
            else:
                M += 1
        print("* ",F,"(",round(F/self.Number()*100.),"%) females, ",
              M,"(",round(M/self.Number()*100),"%) males;")
        if plot:
            fig, axes = plt.subplots()
            axes.hist(ages, 20, range=(0,100), density=True, facecolor='blue', alpha=0.5)
            plt.show()
        if full:
            for p in self.people:
                p.Output()
        
