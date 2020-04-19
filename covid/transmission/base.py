from covid.parameters import ParameterInitializer

class Transmission(ParameterInitializer):
    def __init__(self, user_parameters, required_parameters):
        super().__init__("transmission", required_parameters)
        self.initialize_parameters(user_parameters)

    @property
    def probability(self):
        return None



