import numpy as np
import random
import transmission as Transmission
import symptoms as Symptoms
import sys

class InfectionSelector:
    def __init__(self,Tparams,Sparams):
        self.transmission_params = Tparams
        self.symptoms_params     = Sparams

    def make_infection(self,time):
        transmission = self.select_transmission(time)
        if self.symptoms_params!=None:
            symptoms = self.select_severity(time)
        else:
            symptoms = None
        infection =  Infection(time)
        infection.set_transmission(transmission)
        infection.set_symptoms(symptoms)
        return infection
        
    def select_transmission(self,time):
        if self.transmission_params["Transmission:Type"]=="SI":
            names = ["Transmission:Probability"]
            params = self.make_parameters(self.transmission_params,names)
            transmission = Transmission.TransmissionSI(params,time)
        elif self.transmission_params["Transmission:Type"]=="XNExp":
            names = ["Transmission:Probability",
                     "Transmission:Exponent",
                     "Transmission:Norm"]
            params, variations = self.make_parameters(self.transmission_params,names)
            transmission = Transmission.TransmissionXNExp(params,time)
        elif self.transmission_params["Transmission:Type"]=="Box":
            names = ["Transmission:Probability",
                     "Transmission:EndTime"]
            params = self.make_parameters(self.transmission_params,names)
            transmission = Transmission.TransmissionConstantInterval(params,time)
        return transmission

    def select_severity(self,time):
        if self.symptoms.params["Symptoms:Type"]==None:
            return None
        if self.symptoms_params["Symptoms:Type"]=="Gauss":
            names = ["Symptoms:MaximalSeverity",
                     "Symptoms:MeanTime",
                     "Symptoms:SigmaTime"]
            params, variations = self.make_parameters(self.symptoms_params,names)
            sever = Symptoms.SymptomsGaussian(params,time)
        return symptoms
            
    def make_parameters(self,parameters,names):
        for tag in names:
            mean   = parameters[tag]["Mean"]
            if "WidthPlus" in parameters[tag]:
                widthP = parameters[tag]["WidthPlus"]
            else:
                widthP = None
            if "WidthMinus" in parameters[tag]:
                widthM = parameters[tag]["WidthMinus"]
            else:
                widthM = None
            if "Lower" in parameters[tag]:
                lower  = parameters[tag]["Lower"]
            else:
                lower = None
            if "Upper" in parameters[tag]:
                upper  = parameters[tag]["Upper"]
            else:
                upper = None                
            if widthP==None and widthM==None:
                parameters[tag]["Value"] = mean
                continue
            elif widthP==None:
                widthP = widthM
            elif widthM==None:
                widthM = widthP
                
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
            parameters[tag]["Value"] = value
        return parameters
            
class Infection:
    """
    The description of the infection, with two time dependent characteristics,
    which may vary by individual:
    - transmission probability, Ptransmission.
    - symptom severity, Severity
    Either of them will be a numer between 0 (low) and 1 (high, strong sypmotoms), 
    and for both we will have some thresholds.
    Another important part for the infection is their begin, starttime, which must
    be given in the constructor.  Transmission probability and symptom severity
    can be added/modified a posteriori.
    """
    def __init__(self,time,transmission=None,symptoms=None):
        self.threshold_transmission = 0.01
        self.threshold_symptoms     = 0.01
        self.starttime              = time
        self.transmission           = transmission
        self.symptoms               = symptoms

    def set_transmission(self, transmission):
        if not isinstance(transmission, Transmission.Transmission):
            print ("Error in Infection.set_transmission(",transmission,") is not a transmission.")
            print("--> Exit the code.")
            sys.exit()
        self.transmission = transmission

    def get_transmission(self):
        return self.transmission
        
    def set_symptoms(self, symptoms):
        if symptoms!=None and not isinstance(symptoms, Symptoms.Symptoms):
            print ("Error in Infection.set_symptoms(",symptoms,") is not a symptoms.")
            print("--> Exit the code.")
            sys.exit()
        self.symptoms = symptoms

    def get_symptoms(self):
        return self.symptoms
        
    def transmission_probability(self,time):
        if self.transmission==None:
            return 0.
        return self.transmission.probability(time)

    def symptom_severity(self,time):
        if not self.symptoms:
            return 0.
        return self.symptoms.severity(time)

    def still_infected(self,time):
        return ((self.transmission!=None and
                 self.transmission.probability(time)>self.threshold_transmission) or
                (self.symptoms!=None and
                 self.symptoms.severity(time)>self.threshold_symptoms))
