import sys
import random
from covid.infection import Infection

class Counter:
    def __init__(self,person):
        self.person = person
        self.number_of_infected     = 0
        self.maximal_symptoms       = 0
        self.maximal_symptoms_time  = -1
        self.maximal_symptoms_tag   = "none"
        self.time_of_infection      = -1
        self.grouptype_of_infection = "none"
        self.length_of_infection    = -1

    def update_symptoms(self,symptoms,time):
        if symptoms > self.maximal_symptoms:
            self.maximal_symptoms      = symptoms
            self.maximal_symptoms_tag  = person.get_symptoms_tag(symptoms) 
            self.maximal_symptoms_time = time - self.time_of_infection

    def update_infection_data(self,time,grouptype=None):
        self.time_of_infection = time
        if grouptype != None:
            self.grouptype_of_infection = grouptype

    def set_length_of_infection(self,endtime):
        self.length_of_infection = endtime - self.time_of_infection

    def increment_infected(self):
        self.number_of_infected += 1

        
        
class Person:
    """
    Primitive version of class person.  This needs to be connected to the full class 
    structure including health and social indices, employment, etc..  The current 
    implementation is only meant to get a simplistic dynamics of social interactions coded.
    
    The logic is the following:
    People can get infected with an Infection, which is characterised by time-dependent
    transmission probabilities and symptom severities (see class descriptions for
    Infection, Transmission, Severity).  The former define the infector part for virus
    transmission, while the latter decide if individuals realise symptoms (we need
    to define a threshold for that).  The symptoms will eventually change the behavior 
    of the person (i.e. intensity and frequency of social contacts), if they need to be 
    treated, hospitalized, plugged into an ICU or even die.  This part of the model is 
    still opaque.   
    
    Since the realization of the infection will be different from person to person, it is
    a characteristic of the person - we will need to allow different parameters describing
    the same functional forms of transmission probability and symptom severity, distributed
    according to a (tunable) parameter distribution.  Currently a non-symmetric Gaussian 
    smearing of 2 sigma around a mean with left-/right-widths is implemented.    
    """

    def __init__(
        self, person_id, area, work_msoa, age, nomis_bin, sex, health_index, econ_index
    ):
        # if not self.is_sane(self, person_id, area, age, sex, health_index, econ_index):
        #    return
        self.id           = person_id
        self.age          = age
        self.nomis_bin    = nomis_bin
        self.sex          = sex
        self.health_index = health_index
        self.econ_index = econ_index
        self.area = area
        self.work_msoarea = work_msoa
        self.r0 = 0
        self.econ_index   = econ_index
        self.area         = area
        self.r0           = 0
        self.active_group = None
        self.household = None
        self.school = None
        self.industry = None
        self.init_counter()
        self.init_health_information()

    def is_sane(self, person_id, area, age, sex, health_index, econ_index):
        if age < 0 or age > 120 or not (sex == "M" or sex == "F"):
            print("Error: tried to initialise person with descriptors out of range: ")
            print("Id = ", person_id, " age / sex = ", age, "/", sex)
            print("economical/health indices: ", econ_index, health_index)
            sys.exit()
        return True

    def init_counter(self):
        self.counter = Counter(self)
    
    def get_counter(self):
        return self.counter
    
    def get_name(self):
        return self.id

    def get_age(self):
        return self.age

    def get_sex(self):
        return self.sex

    def get_health_index(self):
        return self.health_index

    def get_econ_index(self):
        return self.econ_index

    def get_susceptibility(self):
        return self.susceptibility

    def get_infection(self):
        return self.infection

    def set_household(self, household):
        self.household = household

    def init_health_information(self):
        self.susceptibility = 1.0
        self.susceptible = True
        self.infected = False
        self.infection = None
        self.recovered = False

    def set_infection(self, infection):
        if not isinstance(infection, Infection) and not infection == None:
            print("Error in Infection.Add(", infection, ") is not an infection")
            print("--> Exit the code.")
            sys.exit()
        self.infection = infection
        if self.infection == None:
            if self.infected:
                self.recovered = True
                self.susceptible = False
            self.infected = False
        else:
            self.infected = True
            self.susceptible = False

    def update_health_status(self, time):
        if self.recovered == True:
            self.infected = False
            self.infection = None
        if self.infection != None:
            self.susceptible = False
            if self.infection.still_infected(time):
                self.infected = True
            else:
                self.infected = False
                self.infection = None
                self.set_length_of_infection(time)
            self.counter.update_symptoms(time)

    def is_susceptible(self):
        return self.susceptible

    def is_infected(self):
        return self.infected

    def set_recovered(self, is_recovered):
        if self.infected == True:
            self.recovered = is_recovered

    def is_recovered(self):
        return self.recovered

    def get_symptoms_tag(self, severity):
        return self.infection.get_symptoms().fix_tag(severity)

    def susceptibility(self):
        return self.susceptibility

    def set_susceptibility(self, susceptibility):
        self.susceptibility = susceptibility

    def transmission_probability(self, time):
        if self.infection == None:
            return 0.0
        return self.infection.transmission_probability(time)

    def symptom_severity(self, severity):
        if self.infection == None:
            return 0.0
        return self.infection.symptom_severity(severity)

    def output(self, time=0):
        print("--------------------------------------------------")
        if self.health_index != 0:
            print(
                "Person [",
                self.id,
                "]: age = ",
                self.age,
                " sex = ",
                self.sex,
                "health: ",
                self.health_index,
            )
        else:
            print("Person [", self.id, "]: age = ", self.age, " sex = ", self.sex)
        if self.is_susceptible():
            print("-- person is susceptible.")
        if self.is_infected():
            print(
                "-- person is infected: ",
                self.get_symptoms_tag(time + 5),
                "[",
                self.infection.symptom_severity(time + 5),
                "]",
            )
        if self.is_recovered():
            print("-- person has recovered.")


class People:
    def __init__(self, world):
        self.world = world
        self.members = []
        self.total_people = 0

    def populate_area(self, area):
        distributor = PersonDistributor(self, area)
        distributor.populate_area()
