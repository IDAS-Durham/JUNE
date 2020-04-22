from covid.infection.transmission import Transmission


class TransmissionConstant(Transmission):
    def __init__(self, timer, user_parameters={}):
        required_parameters = ["transmission_probability"]
        super().__init__(timer, user_parameters, required_parameters)

    def update_probability(self):
        time = self.timer.now
        self.last_time_updated = time


if __name__ == "__main__":
    trans = TransmissionConstant(None)
    print(trans.probability)
    user_config = {
        "transmission_probability": {
            "distribution": "constant", "parameters": {"value": 0.5}
        }
    }
    trans = TransmissionConstant(None, user_config)
    print(trans.transmission_probability)
