import os
import yaml
from covid.parameter_distributions import parameter_initializer


class Transmission:
    def __init__(self, required_parameters):
        print(f"Transmission class {type(self).__name__}")
        self.required_parameters = required_parameters
        self.tranmission_type = type(self).__name__
        self.default_parameters = self.read_default_parameters()

    def read_default_parameters(self):
        default_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "..",
            "..",
            "configs",
            "defaults",
            "transmission",
            self.tranmission_type + ".yaml",
        )
        try:
            with open(default_path, "r") as f:
                default_params = yaml.load(f, Loader=yaml.FullLoader)
        except FileNotFoundError:
            raise FileNotFoundError("Default parameter config file not found")
        return default_params

    def initialize_parameters(self, user_parameters):
        parameter_values_dict = {}
        for parameter in self.required_parameters:
            if parameter not in user_parameters:
                parameter_values_dict[parameter] = parameter_initializer(
                    self.default_parameters[parameter]
                )
            else:
                parameter_values_dict[parameter] = parameter_initializer(
                    user_parameters[parameter]
                )
        for parameter, value in parameter_values_dict.items():
            setattr(self, parameter, value)

    @property
    def probability(self):
        return None


if __name__ == "__main__":
    trans = Transmission(None)
    print(trans.default_parameters)
