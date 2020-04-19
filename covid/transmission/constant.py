from covid.parameter_distributions import parameter_initializer

class TransmissionConstant:
    def __init__(self, transmission_parameters):
        self.prob_transmission = parameter_initializer(transmission_parameters)

    @property
    def probability(self):
        return self.prob_transmission
