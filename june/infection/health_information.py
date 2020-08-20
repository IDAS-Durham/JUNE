from june.infection.symptom_tag import SymptomTag

dead_tags = (SymptomTag.dead_home, SymptomTag.dead_hospital, SymptomTag.dead_icu)

class HealthInformation:
    __slots__ = (
        "infection",
        "number_of_infected",
        "time_of_symptoms_onset"
    )

    def __init__(self):
        self.infection = None
        self.number_of_infected = 0

    def set_infection(self, infection):
        self.infection = infection
        time_to_symptoms = infection.symptoms.
        if time_to_symptoms is None:
            self.time_of_symptoms_onset = None
        else:
            self.time_of_symptoms_onset = self.time_of_infection + time_to_symptoms

    @property
    def tag(self):
        if self.infection is not None:
            return self.infection.symptoms.tag
        return None

    @property
    def time_of_infection(self):
        try:
            return self.infection.start_time
        except:
            return None

    @property
    def should_be_in_hospital(self) -> bool:
        return self.tag in (SymptomTag.hospitalised, SymptomTag.intensive_care)

    @property
    def infected_at_home(self) -> bool:
        return self.infected and not (self.dead or self.should_be_in_hospital)

    @property
    def is_dead(self) -> bool:
        return self.tag in dead_tags

    def update_health_status(self, time, delta_time):
        self.infection.update_at_time(time + delta_time)
        if self.infection.symptoms.is_recovered():
            self.recovered = True

    def set_recovered(self, time):
        self.recovered = True
        self.infected = False
        self.susceptible = False
        self.set_length_of_infection(time)
        self.infection = None

    def set_dead(self, time):
        self.dead = True
        self.infected = False
        self.susceptible = False
        self.set_length_of_infection(time)
        self.infection = None

    def transmission_probability(self, time):
        if self.infection is not None:
            return 0.0
        return self.infection.transmission_probability(time)

    def symptom_severity(self, severity):
        if self.infection is None:
            return 0.0
        return self.infection.symptom_severity(severity)

    def set_length_of_infection(self, time):
        self.length_of_infection = time - self.time_of_infection
