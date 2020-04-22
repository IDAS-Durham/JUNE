import sys

from covid.infection import Infection


class HealthInformation:
    def __init__(self, counter):
        self.counter = counter
        self.susceptibility = 1.0
        self.susceptible = True
        self.infected = False
        self.infection = None
        self.recovered = False

    def set_infection(self, infection):
        if not isinstance(infection, Infection) and infection is not None:
            print("Error in Infection.Add(", infection, ") is not an infection")
            print("--> Exit the code.")
            sys.exit()
        self.infection = infection
        if self.infection is None:
            if self.infected:
                self.recovered = True
                self.susceptible = False
            self.infected = False
        else:
            self.infected = True
            self.susceptible = False

    def update_health_status(self):
        if self.recovered is True:
            self.infected = False
            self.infection = None
        if self.infection is not None:
            self.susceptible = False
            if self.infection.still_infected:
                self.infected = True
                self.infection.update_infection_probability()
                if self.infection.symptoms is None:
                    print("error!")
                self.counter.update_symptoms()
            else:
                self.infected = False
                self.infection = None
                self.counter.set_length_of_infection()

    def is_recovered(self):
        return self.recovered

    def get_infection(self):
        return self.infection

    def is_susceptible(self):
        return self.susceptible

    def is_infected(self):
        return self.infected

    def set_recovered(self, is_recovered):
        if self.infected:
            self.recovered = is_recovered

    def get_symptoms_tag(self, symptoms):
        return self.infection.symptoms.fix_tag(symptoms.severity)

    def transmission_probability(self, time):
        if self.infection is not None:
            return 0.0
        return self.infection.transmission_probability(time)

    def symptom_severity(self, severity):
        if self.infection is None:
            return 0.0
        return self.infection.symptom_severity(severity)


class Counter:
    def __init__(self, person):
        self.person = person
        self.number_of_infected = 0
        self.maximal_symptoms = 0
        self.maximal_symptoms_time = -1
        self.maximal_symptoms_tag = "none"
        self.time_of_infection = -1
        self.grouptype_of_infection = "none"
        self.length_of_infection = -1

    @property
    def timer(self):
        return self.person.world.timer

    def update_symptoms(self):  # , symptoms, time):
        if self.person.infection.symptoms.severity > self.maximal_symptoms:
            self.maximal_symptoms = self.person.infection.symptoms.severity
            self.maximal_symptoms_tag = self.person.get_symptoms_tag(
                self.person.infection.symptoms
            )
            self.maximal_symptoms_time = self.timer.now - self.time_of_infection

    def update_infection_data(self, time, grouptype=None):
        self.time_of_infection = time
        if grouptype != None:
            self.grouptype_of_infection = grouptype

    def set_length_of_infection(self):
        self.length_of_infection = self.timer.now - self.time_of_infection

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
            self,
            person_id=None,
            area=None,
            work_msoa=None,
            age=-1,
            nomis_bin=None,
            sex=None,
            health_index=None,
            econ_index=None
    ):
        if not 0 <= age <= 120 or sex not in ("M", "F"):
            raise AssertionError(
                f"Attempting to initialise a person"
            )
        self.id = person_id
        self.age = age
        self.nomis_bin = nomis_bin
        self.sex = sex
        self.health_index = health_index
        self.econ_index = econ_index
        self.area = area
        self.work_msoarea = work_msoa
        self.econ_index = econ_index
        self.area = area
        self.active_group = None
        self.household = None
        self.school = None
        self.industry = None
        self.industry_specific = None
        self.health_information = HealthInformation(
            Counter(self)
        )

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

    def set_household(self, household):
        self.household = household

    def susceptibility(self):
        return self.susceptibility

    def set_susceptibility(self, susceptibility):
        self.susceptibility = susceptibility

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
        if self.health_information.is_susceptible():
            print("-- person is susceptible.")
        if self.health_information.is_infected():
            print(
                "-- person is infected: ",
                self.health_information.get_symptoms_tag(time + 5),
                "[",
                self.health_information.infection.symptom_severity(time + 5),
                "]",
            )
        if self.health_information.is_recovered():
            print("-- person has recovered.")


class People:
    def __init__(self, world):
        self.world = world
        self.members = []
        self.total_people = 0
