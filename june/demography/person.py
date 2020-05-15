from itertools import count


class HealthInformation:
    def __init__(self):
        self.susceptibility = 1.0
        self.susceptible = True
        self.infected = False
        self.infection = None
        self.recovered = False
        self.number_of_infected = 0
        self.maximal_symptoms = 0
        self.maximal_symptoms_time = -1
        self.maximal_symptoms_tag = "none"
        self.time_of_infection = -1
        self.group_type_of_infection = "none"
        self.length_of_infection = -1

    def set_infection(self, infection):
        self.infection = infection
        self.infected = True
        self.susceptible = False
        self.susceptibility = 0.

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
    def infected_at_home(self) -> bool:
        return self.infected and not (self.dead or self.in_hospital)

    @property
    def dead(self) -> bool:
        return self.tag == "dead"

    def update_health_status(self, time, delta_time):
        if self.infected:
            if self.infection.symptoms.is_recovered(delta_time):
                self.recovered = True
                # self.set_recovered(time)
            else:
                self.infection.update_at_time(time + delta_time)

    def set_recovered(self, time):
        self.recovered = True
        self.infected = False
        self.susceptible = False
        self.susceptibility = 0.0
        self.set_length_of_infection(time)
        self.infection = None

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

    def update_symptoms(self, time):  # , symptoms, time):
        if self.infection.symptoms.severity > self.maximal_symptoms:
            self.maximal_symptoms = self.infection.symptoms.severity
            self.maximal_symptoms_tag = self.get_symptoms_tag(
                self.infection.symptoms
            )
            self.maximal_symptoms_time = time - self.time_of_infection

    def update_infection_data(self, time, group_type=None):
        self.time_of_infection = time
        if group_type is not None:
            self.group_type_of_infection = group_type

    def set_length_of_infection(self, time):
        self.length_of_infection = time - self.time_of_infection

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
    _id = count()

    def __init__(
            self,
            age=-1,
            nomis_bin=None,
            sex=None,
            ethnicity=None,
            econ_index=None,
            mode_of_transport=None,
            area=None
    ):
        """
        Inputs:
        """
        self.id = next(self._id)
        # biological attributes
        self.age = age
        self.nomis_bin = nomis_bin
        self.sex = sex
        self.ethnicity = ethnicity
        # geo-graphical attributes
        self.work_super_area = None
        self.household = None
        self.area = area
        # primary activity attributes
        self.mode_of_transport = mode_of_transport
        self.school = None
        self.carehome = None
        self.primary_activity = None  # school, company, key-industr. (e.g. hospital, schools)
        self.active_group = None
        self.groups = []
        self.sector = None
        self.sub_sector = None
        self.company_id = None
        self.hospital = None
        self.in_hospital = None
        self.home_city = None
        self.econ_index = econ_index
        self.health_information = HealthInformation()


class People:
    def __init__(self, world):
        self.members = []

    @property
    def total_people(self):
        return len(self.members)

    @property
    def infected(self):
        return [
            person for person in self.members
            if person.health_information.infected and not
            person.health_information.dead

        ]

    @property
    def susceptible(self):
        return [
            person for person in self.members
            if person.health_information.susceptible

        ]

    @property
    def recovered(self):
        return [
            person for person in self.members
            if person.health_information.recovered

        ]
