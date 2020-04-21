from covid.symptoms import Symptoms 

class SymptomsGaussian(Symptoms):
    def __init__(self, infection, user_parameters={}):
        required_parameters = ["mean_time", "sigma_time"]
        super().__init__(infection, user_parameters, required_parameters)
        self.Tmean = max(0.0, self.mean_time)
        self.sigmaT = max(0.001, self.sigma_time)

    def _calculate_severity(self, time):
        dt = time - (self.infection.starttime + self.Tmean)
        return self.maxseverity * np.exp(-(dt ** 2) / self.sigmaT ** 2)


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


