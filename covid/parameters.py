import os
import random
import yaml


class ParametersError(BaseException):
    def __init__(self, distribution, key):
        message = f"""Parameter distribution {type(distribution).__name__} 
                missing parameter {key}"""
        super().__init__(message)


class ParameterInitializer:
    """
    Given a list of required parameters, initializes the (child) class
    with the parameter values by reading the user config file or the defaults.
    The classtype argument is the kind of class (transmission, symptoms, etc.)
    you are initializing, so it can look the defaults at the right place.
    """
    def __init__(self, classtype:str, user_parameters:dict, required_parameters:dict) -> None:
        self.classtype = classtype
        self.required_parameters = required_parameters
        self.user_parameters = user_parameters
        self.class_name = type(self).__name__
        self.default_parameters = self.read_default_parameters()
        self.initialize_parameters()

    def read_default_parameters(self)->dict:
        default_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "..",
            "configs",
            "defaults",
            self.classtype,
            self.class_name + ".yaml",
        )
        try:
            with open(default_path, "r") as f:
                default_params = yaml.load(f, Loader=yaml.FullLoader)
        except FileNotFoundError:
            print(default_path)
            raise FileNotFoundError("Default parameter config file not found")
        return default_params

    def initialize_parameters(self) ->None:
        parameter_values_dict = {}
        for parameter in self.required_parameters:
            if parameter not in self.user_parameters: # if parameter is not specified by user, take it from defaults
                parameter_config = self.default_parameters[parameter]
                if type(parameter_config) != dict:
                    parameter_values_dict[parameter] = parameter_config
                    continue
                elif "distribution" in parameter_config.keys():
                    parameter_values_dict[parameter] = self.calculate_parameter(
                        parameter_config
                    )
                else:
                    parameter_values_dict[parameter] = parameter_config
            else:
                parameter_config = self.user_parameters[parameter]
                if type(parameter_config) != dict:
                    parameter_values_dict[parameter] = parameter_config
                    continue
                elif "distribution" in parameter_config.keys():
                    parameter_values_dict[parameter] = self.calculate_parameter(
                        parameter_config
                    )
                else:
                    parameter_values_dict[parameter] = parameter_config
        for parameter, value in parameter_values_dict.items():
            setattr(self, parameter, value)

    def calculate_parameter(self, parameter_config: dict)->float:
        try:
            distribution = parameter_config["distribution"]
        except KeyError:
            raise BaseException(f"I need the distribution name")
        try:
            parameters = parameter_config["parameters"]
        except KeyError:
            raise BaseException(f"I need the parameters for {distribution}")
        if distribution == "constant":
            parameter = ConstantParameter(parameters)
            return parameter.value
        elif distribution == "gaussian":
            parameter = GaussianParameter(parameters)
            return parameter.value
        elif distribution == "uniform":
            parameter = UniformParameter(parameters)
            return parameter.value
        else:
            raise NotImplementedError(
                f"Parameter distribution {distribution} not implemented"
            )


class ParameterDistribution:
    def __init__(self):
        pass

    def value(self):
        pass


class ConstantParameter(ParameterDistribution):
    def __init__(self, parameters_dict: dict) -> None:
        try:
            self.value0 = parameters_dict["value"]
        except KeyError:
            raise ParametersError(self, "value")

    @property
    def value(self):
        return self.value0


class GaussianParameter(ParameterDistribution):
    def __init__(self, parameters_dict: dict) -> None:
        try:
            self.mean = parameters_dict["mean"]
        except KeyError:
            raise ParametersError(self, "mean")
        try:
            self.width_minus = parameters_dict["width_minus"]
        except KeyError:
            # raise ParametersError(self, "width_minus")
            self.width_minus = None
        try:
            self.width_plus = parameters_dict["width_plus"]
        except KeyError:
            # raise ParametersError(self, "width_plus")
            self.width_plus = None
        try:
            self.lower = parameters_dict["lower"]
        except KeyError:
            # raise ParametersError(self, "width_plus")
            self.lower = None
        try:
            self.upper = parameters_dict["upper"]
        except KeyError:
            # raise ParametersError(self, "width_plus")
            self.upper = None

    @property
    def value(self) -> float:
        if self.width_minus == None and self.width_plus == None:
            return self.mean
        if self.width_minus == None:
            self.width_minus = self.width_plus
        if self.width_plus == None:
            self.width_plus = self.width_minus
        while True:
            if random.random() < self.width_minus / (
                self.width_plus + self.width_minus
            ):
                value = self.mean - 1.0
                while value < self.mean:
                    value = random.gauss(self.mean, self.width_plus)
            else:
                value = self.mean + 1.0
                while value > self.mean:
                    value = random.gauss(self.mean, self.width_minus)
            if (self.lower == None or value > self.lower) and (
                self.upper == None or value < self.upper
            ):
                break
        return value


class UniformParameter:
    def __init__(self, parameters_dict: dict) -> None:
        try:
            self.lower = parameters_dict["lower"]
        except KeyError:
            raise ParametersError(self, "lower")
        try:
            self.upper = parameters_dict["upper"]
        except KeyError:
            raise ParametersError(self, "upper")

    @property
    def value(self) -> float:
        return self.lower + random.random() * (self.upper - self.lower)


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    params_dict1 = {"lower": 0, "upper": 1}
    parameters_dict = {"value": 0.5, "mean": 0.3, "width_mins": 1, "width_plus": 1}

    constant = ConstantParameter(parameters_dict)
    gaussian = GaussianParameter(parameters_dict)
    uniform = UniformParameter(params_dict1)
    n = 10000
    constant_values = []
    gaussian_values = []
    uniform_values = []
    for i in range(n):
        constant_values.append(constant.value)
        gaussian_values.append(gaussian.value)
        uniform_values.append(uniform.value)
    fig, ax = plt.subplots(1, 3, figsize=(7, 3), sharex=True, sharey=True)
    ax[0].hist(constant_values)
    ax[0].set_title("constant")
    ax[1].hist(gaussian_values)
    ax[1].set_title("gaussian")
    ax[2].hist(uniform_values)
    ax[2].set_title("uniform")
    plt.subplots_adjust(wspace=0, hspace=0)
    plt.show()
