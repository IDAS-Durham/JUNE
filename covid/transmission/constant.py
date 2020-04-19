from covid.parameters import ParameterInitializer

class TransmissionConstant(ParameterInitializer):
    def __init__(self, transmission_parameters={}):
        required_parameters = ["probability_transmission"]
        super().__init__("transmission", required_parameters)
        self.initialize_parameters(transmission_parameters)

    @property
    def probability(self):
        return self.probability_transmission

if __name__ == "__main__":
    trans = TransmissionConstant()
    print(trans.probability)
