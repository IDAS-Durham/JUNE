import numpy as np
import random
import sys
import covid.transmission as Transmission
import covid.symptoms as Symptoms


class Infection:
    """
    The description of the infection, with two time dependent characteristics,
    which may vary by individual:
    - transmission probability, Ptransmission.
    - symptom severity, Severity
    Either of them will be a numer between 0 (low) and 1 (high, strong sypmotoms), 
    and for both we will have some thresholds.
    Another important part for the infection is their begin, starttime, which must
    be given in the constructor.  Transmission probability and symptom severity
    can be added/modified a posteriori.
    """

    # person, timer, startime -> call timer.now, 
    def __init__(self, time, transmission=None, symptoms=None):
        self.threshold_transmission = 0.001
        self.threshold_symptoms     = 0.001
        self.starttime = time
        self.transmission = transmission
        self.symptoms = symptoms

    def set_transmission(self, transmission):
        if not isinstance(transmission, Transmission.Transmission):
            print(
                "Error in Infection.set_transmission(",
                transmission,
                ") is not a transmission.",
            )
            print("--> Exit the code.")
            sys.exit()
        self.transmission = transmission

    def get_transmission(self):
        return self.transmission

    def set_symptoms(self, symptoms):
        if symptoms != None and not isinstance(symptoms, Symptoms.Symptoms):
            print("Error in Infection.set_symptoms(", symptoms, ") is not a symptoms.")
            print("--> Exit the code.")
            sys.exit()
        self.symptoms = symptoms

    def get_symptoms(self):
        return self.symptoms

    def transmission_probability(self, time):
        if self.transmission == None:
            return 0.0
        return self.transmission.probability(time)

    def symptom_severity(self, time):
        if self.symptoms == None:
            return 0.0
        return self.symptoms.get_severity(time)

    def symptom_tag(self, tagno):
        return self.symptoms.tag(tagno)

    def still_infected(self, time):
        transmission_bool = (
            self.transmission != None
            and self.transmission.probability(time) > self.threshold_transmission
        )
        symptoms_bool = (
            self.symptoms != None
            and self.symptoms.get_severity(time) > self.threshold_symptoms
        )
        is_infected = transmission_bool or symptoms_bool
        return is_infected
