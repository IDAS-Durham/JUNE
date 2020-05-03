class HealthInformation:
    def __init__(self, counter):
        self.counter = counter
        self.susceptibility = 1.0
        self.susceptible = True
        self.infected = False
        self.infection = None
        self.recovered = False

    def set_infection(self, infection):
        self.infection = infection
        self.infected = True
        self.susceptible = False

    @property
    def tag(self):
        if self.infection is not None:
            return self.infection.symptoms.tag
        return None

    @property
    def must_stay_at_home(self) -> bool:
        return self.tag in ("influenza-like illness", "pneumonia")

    @property
    def in_hospital(self) -> bool:
        return self.tag in ("hospitalised", "intensive care")

    @property
    def dead(self) -> bool:
        return self.tag == "dead"

    def update_health_status(self, time, delta_time):
        if self.infected:
            if self.infection.symptoms.is_recovered(delta_time):
                self.set_recovered()
            else:
                self.infection.update_at_time(time)

    def set_recovered(self):
        # self.infection = None
        self.recovered = True
        self.infected = False
        self.susceptible = False
        self.susceptibility = 0.0
        self.counter.set_length_of_infection()

    def get_symptoms_tag(self, symptoms):
        return self.infection.symptoms.tag(symptoms.severity)

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
        if grouptype is not None:
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
            world=None,
            person_id=None,
            age=-1,
            nomis_bin=None,
            sex=None,
            mode_of_transport=None
            oarea=None,
            health_index=None,
            econ_index=None,
    ):
        """
        Inputs:
        """
        # if not 0 <= age <= 120 or sex not in ("M", "F"):
        #    raise AssertionError(
        #        f"Attempting to initialise a person"
        #    )
        self.world = world
        self.id = person_id
        # biological attributes
        self.age = age
        self.nomis_bin = nomis_bin
        self.sex = sex
        # geo-graphical attributes
        self.area = oarea
        self.residence_msoa = oarea.msoarea
        self.work_msoarea = None
        self.household = None
        # primary activity attributes
        self.mode_of_transport = mode_of_transport
        self.work_msoarea = work_msoa
        self.primary_activity = None  # school, company, key-industr. (e.g. hospital, schools)
        self.active_group = None
        self.in_hospital = None
        self.health_index = health_index
        self.econ_index = econ_index
        self.health_information = HealthInformation(Counter(self))

    def get_into_hospital(self):
        if self.in_hospital==None:
            hospital = self.world.hospitals.get_nearest(self)
            hospital.add_as_patient(self)

    def bury(self):
        cemetery = self.world.cemeteries.get_nearest(self)
        cemetery.add(self)
        
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
        if self.health_information.susceptible:
            print("-- person is susceptible.")
        if self.health_information.infected:
            print(
                "-- person is infected: ",
                self.health_information.get_symptoms_tag(time + 5),
                "[",
                self.health_information.infection.symptom_severity(time + 5),
                "]",
            )
        if self.health_information.recovered:
            print("-- person has recovered.")


class People:
    def __init__(self, world):
        self.members = []

    #@classmethod
    #def from_file(cls, filename: str,: str) -> "People":
    #    """
    #    """
    #    = pd.read_csv(filename, index_col=0)
    #    return People(,)

    @property
    def total_people(self):
        return len(self.members)
