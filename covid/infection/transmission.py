class Transmission:

    def __init__(self):

        self.probability = 0.0

    def update_probability_at_time(self, time):
        raise NotImplementedError()

class TransmissionConstant(Transmission):

    def __init__(self, proabability=0.3):

        super().__init__()

        self.probability = proabability

    def update_probability_at_time(self, time):

        pass