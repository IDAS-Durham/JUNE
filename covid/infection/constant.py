from covid.infection import Infection

class InfectionConstant(Infection):
    def __init__(self, person, timer, user_config={}, user_parameters={}):
        required_parameters = ["threshold_transmission", "threshold_symptoms"]
        super().__init__(person, timer, user_config, user_parameters, required_parameters)

    @property
    def still_infected(self):
        #transmission_bool = (
        #    self.transmission != None
        #    and self.transmission.probability > self.threshold_transmission
        #)
        #symptoms_bool = (
        #    self.symptoms != None and self.symptoms.severity > self.threshold_symptoms
        #)
        #is_infected = transmission_bool or symptoms_bool
        return True

