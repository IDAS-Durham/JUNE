import numpy as np
from covid.infection.symptoms import Symptoms 

class SymptomsGaussian(Symptoms):
    def __init__(self, timer, health_index, user_parameters={}):
        required_parameters = ["mean_time", "sigma_time"]
        super().__init__(timer, health_index, user_parameters, required_parameters)
        self.Tmean = max(0.0, self.mean_time)
        self.sigmaT = max(0.001, self.sigma_time)

    def update_severity(self):
        time = self.timer.now
        dt = time - (self.infection_start_time + self.Tmean)
        self.last_time_updated = time
        self.severity = self.maxseverity * np.exp(-(dt ** 2) / self.sigmaT ** 2)


if __name__=='__main__':

    sc = SymptomsGaussian(1)
    print(sc.mean_time)
    print(sc.sigma_time)

    user_config = {
                'mean_time': 
                {
                    'distribution': 'gaussian',
                    'parameters': 
                    {
                        'mean': 5,
                        'width_minus': 3,
                    }
                },
                'sigma_time':
                {
                    'distribution': 'gaussian',
                    'parameters': 
                    {
                        'mean': 15,
                        'width_minus': 3,
                    }
                }

            }


    sc = SymptomsGaussian(None, user_config)
    print(sc.mean_time)
    print(sc.sigma_time)


