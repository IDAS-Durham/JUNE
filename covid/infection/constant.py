from covid.infection import Infection

class InfectionConstant(Infection):
    def __init__(self, person, timer, user_config={}):
        required_parameters = ["threshold_transmission", "threshold_symptoms"]
        super().__init__(person, timer, user_config, required_parameters)

    def update_infection_probability(self):
        trans_probability = self.transmission.update_probability()
        return trans_probability 


