import numpy as np
import random
import sys
from covid.transmission import Transmission


class Infection(TypeInitializer, ParametersInitializer):
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

    def __init__(self, person, timer, user_params):

        self.threshold_transmission = 0.001
        self.threshold_symptoms     = 0.001
        self.starttime = timer.now
        self.params = params
        self.person = person

        #self.transmission = self.set_transmission(transmission)
        #self.symptoms = self.set_symptoms(symptoms)
        self.transmission = TransmissionConstant()
        self.symptoms = SymptomsConstant(self) 

    def infect(self, person_to_infect):

        person_to_infect.infection = self.__init__(person_to_infect,
                self.timer,
                self.params)


    def set_transmission(self, transmission):
        if not isinstance(transmission, Transmission):
            print(
                "Error in Infection.set_transmission(",
                transmission,
                ") is not a transmission.",
            )
            print("--> Exit the code.")
            sys.exit()
        self.transmission = transmission


    def set_symptoms(self, symptoms):
        if symptoms != None and not isinstance(symptoms, Symptoms):
            print("Error in Infection.set_symptoms(", symptoms, ") is not a symptoms.")
            print("--> Exit the code.")
            sys.exit()
        self.symptoms = symptoms

    @property
    def transmission_probability(self):
        if self.transmission == None:
            return 0.0
        return self.transmission.probability

    @property
    def symptom_severity(self):
        if self.symptoms == None:
            return 0.0
        return self.symptoms.severity

    def symptom_tag(self, tagno):
        return self.symptoms.tag

    @property
    def still_infected(self):
        transmission_bool = (
            self.transmission != None
            and self.transmission.probability > self.threshold_transmission
        )
        symptoms_bool = (
            self.symptoms != None
            and self.symptoms.severity > self.threshold_symptoms
        )
        is_infected = transmission_bool or symptoms_bool
        return is_infected
