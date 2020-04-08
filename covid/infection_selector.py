import numpy as np
import random
import sys
import covid.transmission as Transmission
import covid.symptoms as Symptoms
import covid.infection as Infection

class InfectionSelector:
    def __init__(self,Tparams,Sparams):
        self.transmission_params = Tparams
        self.symptoms_params     = Sparams

    def make_infection(self,person,time):
        transmission = self.select_transmission(person,time)
        if self.symptoms_params!=None:
            symptoms = self.select_severity(person,time)
        else:
            symptoms = None
        infection =  Infection.Infection(time)
        infection.set_transmission(transmission)
        infection.set_symptoms(symptoms)
        return infection
        
    def select_transmission(self,person,time):
        if self.transmission_params["Transmission:Type"]=="SI":
            names = ["Transmission:Probability"]
            params = self.make_parameters(self.transmission_params,names)
            transmission = Transmission.TransmissionSI(person,params,time)
        elif self.transmission_params["Transmission:Type"]=="SIR":
            names = ["Transmission:Probability",
                     "Transmission:Recovery",
                     "Transmission:RecoverCutoff"]
            params = self.make_parameters(self.transmission_params,names)
            transmission = Transmission.TransmissionSIR(person,params,time)
        elif self.transmission_params["Transmission:Type"]=="XNExp":
            names = ["Transmission:Probability",
                     "Transmission:Exponent",
                     "Transmission:Norm"]
            params, variations = self.make_parameters(self.transmission_params,names)
            transmission = Transmission.TransmissionXNExp(person,params,time)
        elif self.transmission_params["Transmission:Type"]=="Box":
            names = ["Transmission:Probability",
                     "Transmission:EndTime"]
            params = self.make_parameters(self.transmission_params,names)
            transmission = Transmission.TransmissionConstantInterval(person,params,time)
        return transmission

    def select_severity(self,person,time):
        if self.symptoms_params["Symptoms:Type"]==None:
            return None
        elif self.symptoms_params["Symptoms:Type"]=="Gauss":
            names = ["Symptoms:MaximalSeverity",
                     "Symptoms:MeanTime",
                     "Symptoms:SigmaTime"]
            params = self.make_parameters(self.symptoms_params,names)
            symptoms = Symptoms.SymptomsGaussian(person,params, time)
        return symptoms

    def make_parameters(self,parameters,names):
        for tag in names:
            mode = None
            if "Mode" in parameters[tag]:
                mode = parameters[tag]["Mode"]
            if mode=="Gamma":
                self.make_parameters_Gamma(parameters[tag])
            else:
                self.make_parameters_Gaussian(parameters[tag])
        return parameters
        
    def make_parameters_Gamma(self,parameters):
        mean   = parameters["Mean"]
        alpha  = parameters["Shape"]
        beta   = alpha/mean
        parameters["Value"] = random.gammavariate(alpha,beta)
            
    def make_parameters_Gaussian(self,parameters):
        mean   = parameters["Mean"]
        if "WidthPlus" in parameters:
            widthP = parameters["WidthPlus"]
        else:
            widthP = None
        if "WidthMinus" in parameters:
            widthM = parameters["WidthMinus"]
        else:
            widthM = None
        if widthP==None and widthM==None:
            parameters["Value"] = mean
            return
        elif widthP==None:
            widthP = widthM
        elif widthM==None:
            widthM = widthP
        
        if "Lower" in parameters:
            lower  = parameters["Lower"]
        else:
            lower = None
        if "Upper" in parameters:
            upper  = parameters["Upper"]
        else:
            upper = None                
            
        while (True):
            if random.random()<widthP/(widthP+widthM):
                value = mean-1.
                while value<mean:
                    value = random.gauss(mean,widthP)
            else:
                value = mean+1.
                while value>mean:
                    value = random.gauss(mean,widthM)
            if ((lower==None or value>lower) and
                (upper==None or value<upper)):
                break
        parameters["Value"] = value
            
