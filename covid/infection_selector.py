import numpy as np
import random
import sys
import covid.transmission as Transmission
import covid.symptoms as Symptoms
import covid.infection as Infection


class InfectionSelector:
    def __init__(self, config):
        self.transmission_params = None
        self.symptoms_params     = None
        if "transmission" in config["infection"]:
            self.transmission_params = config["infection"]["transmission"]
        if "symptoms" in config["infection"]:
            self.symptoms_params = config["infection"]["symptoms"]

    def make_infection(self, person, time):
        if self.transmission_params != None:
            transmission = self.select_transmission(person, time)
        else:
            transmission = None
        if self.symptoms_params != None:
            symptoms = self.select_severity(person, time)
        else:
            symptoms = None
        infection = Infection.Infection(time)
        infection.set_transmission(transmission)
        infection.set_symptoms(symptoms)
        return infection

    def select_transmission(self, person, time):
        if "type" in self.transmission_params:
            if self.transmission_params["type"] == "SI":
                keys = ["probability"]
                params = self.make_parameters(self.transmission_params, keys)
                return Transmission.TransmissionSI(person, params, time)
            elif self.transmission_params["type"] == "SIR":
                keys = ["probability", "recovery", "recovery_cutoff"]
                params = self.make_parameters(self.transmission_params, keys)
                return Transmission.TransmissionSIR(person, params, time)
            elif self.transmission_params["type"] == "XNExp":
                keys = ["probability", "relaxation", "mean_time", "end_time"]
                params = self.make_parameters(self.transmission_params, keys)
                return Transmission.TransmissionXNExp(person, params, time)
            elif self.transmission_params["type"] == "LogNormal":
                keys = ["probability", "mean_time", "width_time", "end_time"]
                params = self.make_parameters(self.transmission_params, keys)
                return Transmission.TransmissionLogNormal(person, params, time)
            elif self.transmission_params["type"] == "Box":
                keys = ["probability", "end_time"]
                params = self.make_parameters(self.transmission_params, keys)
                return Transmission.TransmissionConstantInterval(person, params, time)
        return None

    def select_severity(self, person, time):
        if "type" in self.symptoms_params:
            if self.symptoms_params["type"] == "Constant":
                keys = ["time_offset", "end_time"]
                params = self.make_parameters(self.symptoms_params, keys)
                return Symptoms.SymptomsConstant(person, params, time)
            elif self.symptoms_params["type"] == "Gauss":
                keys = ["mean_time", "sigma_time"]
                params = self.make_parameters(self.symptoms_params, keys)
                return Symptoms.SymptomsGaussian(person, params, time)
            elif self.symptoms_params["type"] == "Tanh":
                keys = ["max_time", "onset_time", "end_time"]
                params = self.make_parameters(self.symptoms_params, keys)
                return Symptoms.SymptomsTanh(person, params, time)
        return None

    def make_parameters(self, parameters, names):
        for tag in names:
            mode = None
            if "mode" in parameters[tag]:
                mode = parameters[tag]["mode"]
            if mode == "Flat":
                self.make_parameters_Flat(parameters[tag])
            elif mode == "Gamma":
                self.make_parameters_Gamma(parameters[tag])
            else:
                self.make_parameters_Gaussian(parameters[tag])
        return parameters

    def make_parameters_Flat(self, parameters):
        upper = parameters["upper"]
        lower = parameters["lower"]
        parameters["value"] = lower + random.random() * (upper - lower)

    def make_parameters_Gamma(self, parameters):
        mean  = parameters["mean"]
        alpha = parameters["width"]**2
        beta  = alpha/mean
        #print ("gamma(",alpha,", ",beta,") --> ",
        #       "mean = ",(alpha/beta)," width = ",(np.sqrt(alpha)/beta),".")
        value = np.random.gamma(alpha, 1./beta)
        parameters["value"] = value

    def make_parameters_Gaussian(self, parameters):
        mean = parameters["mean"]
        if "widthPlus" in parameters:
            widthP = parameters["widthPlus"]
        else:
            widthP = None
        if "widthMinus" in parameters:
            widthM = parameters["widthMinus"]
        else:
            widthM = None
        if widthP == None and widthM == None:
            parameters["value"] = mean
            return
        elif widthP == None:
            widthP = widthM
        elif widthM == None:
            widthM = widthP

        if "lower" in parameters:
            lower = parameters["lower"]
        else:
            lower = None
        if "upper" in parameters:
            upper = parameters["upper"]
        else:
            upper = None

        while True:
            if random.random() < widthP / (widthP + widthM):
                value = mean - 1.0
                while value < mean:
                    value = random.gauss(mean, widthP)
            else:
                value = mean + 1.0
                while value > mean:
                    value = random.gauss(mean, widthM)
            if (lower == None or value > lower) and (upper == None or value < upper):
                break
        parameters["value"] = value
