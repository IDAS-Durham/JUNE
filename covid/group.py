import person as Person
import sys
import random
import matplotlib
import matplotlib.pyplot as plt 


allowed_groups = ["Household",
                  "Work:Outdoor", "Work:Indoor",
                  "Commute:Public", "Commute:Private",
                  "Leisure:Outdoor", "Leisure:Indoor",
                  "Shopping",
                  "ReferenceGroup","Random"]

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
    patterns, which may be time-dependent.  So, far I have made a first pass at
    a list of group specifiers - we could promote it to a dicitonary with
    default intensities (maybe mean+width with a pre-described range?).
    """
    def __init__(self,name,spec,number=-1):
        if not self.sane(name,spec):
            return
        self.name      = name
        self.spec      = spec
        self.intensity = 1.  # None
        self.people    = []
        self.infected  = []
        self.healthy   = []
        if self.spec=="Random":
            self.fill_random_group(number)
        
    def sane(self,name,spec):
        if not spec in allowed_groups:
            print ("Error: tried to initialise group with wrong specification:",spec)
            return False
        return True

    def set_intensity(self,intensity):
        self.intensity = intensity
        
    def get_intensity(self,time=0):
        if self.intensity == None:
            return 1.
        return self.intensity #.intensity(time)

    def add(self, person):
        if not isinstance(person, Person.Person):
            print ("Error in Group.Add(",p,") is not a person.")
            print("--> Exit the code.")
            sys.exit()
        if person in self.people:
            print ("Tried to add already present person",person.Name(),
                   " to group ",self.gname,".")
            print("--> Ignore and proceed.")
        else:
            self.people.append(person)
            if (person.is_healthy()):
                self.healthy.append(person)
            else:
                self.infected.append(person)

    def update_status_lists(self,time=0):
        self.healthy.clear()
        self.infected.clear()
        for person in self.people:
            person.update_health_status(time)
            if person.is_healthy():
                self.healthy.append(person)
            else:
                self.infected.append(person)

    def clear(self,all=True):
        if all:
            self.people.clear();
        self.healthy.clear()
        self.infected.clear()
                
    def size(self):
        return len(self.people)
    
    def size_healthy(self):
        return len(self.healthy)
        
    def size_infected(self):
        return len(self.infected)
    
    def people(self):
        return self.people

    def healthy_people(self):
        return self.healthy
        
    def infected_people(self):
        return self.infected

    def fill_random_group(self,number):
        print ("Filling random group with ",number,"members.")
        for i in range(number):
            age = random.randrange(0,100)
            sex = random.choice(("M","F"))
            self.add(Person.Person(str(i), 0, age, sex, 0, 0))
        self.output(False,False)
                
    def output(self,plot=False,full=False):
        print ("==================================================")
        print ("Group ",self.name,", type = ",self.spec," with ",
               len(self.people)," people.")
        print("* ",self.size_healthy(),
              "(",round(self.size_healthy()/self.size()*100),"%) are healthy, ",
              self.size_infected(),
              "(",round(self.size_infected()/self.size()*100),"%) are infected.")
        ages = []
        M    = 0
        F    = 0
        for p in self.people:
            ages.append(p.get_age())
            if p.get_sex()=="F":
                F += 1
            else:
                M += 1
        print("* ",F,"(",round(F/self.size()*100.),"%) females, ",
              M,"(",round(M/self.size()*100),"%) males;")
        if plot:
            fig, axes = plt.subplots()
            axes.hist(ages, 20, range=(0,100), density=True, facecolor='blue', alpha=0.5)
            plt.show()
        if full:
            for p in self.people:
                p.Output()
        
