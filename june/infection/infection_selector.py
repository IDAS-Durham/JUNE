import numpy as np
import random
import sys
from june.infection.infection import Infection
from june.infection.transmission import Transmission
from june.infection.symptoms import Symptoms
from june.infection.symptoms_trajectory import SymptomsTrajectory
from june.infection.trajectory_maker import TrajectoryMaker 
from june.infection.health_index import HealthIndexGenerator


class InfectionSelector:
    def __init__(self, config):
        self.health_index_generator = HealthIndexGenerator.from_file()
        self.trajectory_maker       = Trajectory_Maker.from_file()
        pass

    def make_infection(self, person, time):
        symptoms     = self.select_symptoms(person, time)
        transmission = self.select_transmission(person, time)
        return Infection(transmission = transmission,
                         symptoms     = symptoms,
                         start_time   = time)

    def select_transmission(self, person):
        return Transmission.TransmissionXNExp()

    def select_severity(self, person):
        health_index = health_index_generator(person)
        symptoms = self.symptoms.__class__(health_index = health_index)
        symptoms.make_trajectory(person=person)

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

