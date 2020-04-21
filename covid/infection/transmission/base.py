from covid.parameters import ParameterInitializer

class Transmission(ParameterInitializer):
    def __init__(self, timer, user_parameters, required_parameters):
        super().__init__("transmission", required_parameters)
        self.initialize_parameters(user_parameters)
        self.timer = timer
        if timer != None:
            self.infection_start_time = self.timer.now
            self.last_time_updated = self.timer.now  # for testing
        self.probability = 0.0

    def update_probability(self):
        pass



