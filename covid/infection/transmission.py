class Transmission:

    def __init__(self, start_time):

        self.start_time = start_time
        self.probability = 0.0

    def update_probability_at_time(self, time):
        raise NotImplementedError()

class TransmissionConstant(Transmission):

    def __init__(self, start_time, proabability=0.3):

        super().__init__(start_time=start_time)

        self.probability = proabability

    def update_probability_at_time(self, time):

        self.last_time_updated = time