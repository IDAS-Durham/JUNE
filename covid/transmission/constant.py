from covid.transmission import Transmission

class TransmissionConstant(Transmission):
    def __init__(self, user_parameters={}):
        required_parameters = ["transmission_probability"]
        super().__init__(user_parameters, required_parameters)

    @property
    def probability(self):
        return self.transmission_probability


if __name__ == "__main__":
    trans = TransmissionConstant()
    print(trans.probability)
    user_config = {
        "transmission_probability": {
            "distribution": "gaussian",
            "parameters": {"mean": 0.3,
                "width_minus" : 0.5},
        }
    }
    trans = TransmissionConstant(user_config)
    print(trans.probability)
