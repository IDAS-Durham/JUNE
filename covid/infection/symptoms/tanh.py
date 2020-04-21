from covid.infection.symptoms import Symptoms 
import numpy as np

class SymptomsTanh(Symptoms):
    def __init__(self, timer, health_index, user_parameters={}):
        required_parameters = ["max_time", "onset_time", "end_time"]
        super().__init__(timer, health_index, user_parameters, required_parameters)

        self.Tmax        = max(0.0, self.max_time)
        self.Tonset      = max(0.0, self.onset_time)
        self.Tend = max(0.0, self.end_time)
        self.delta_onset = (self.Tmax-self.Tonset)
        self.delta_end   = (self.Tend-self.Tmax)

    def _calculate_severity(self,time):
        time_since_start = time - self.starttime
        if time_since_start<=self.Tmax:
            severity = (1.+np.tanh(3.14*(time_since_start-self.Tonset)/self.delta_onset))/2.
        elif time_since_start>self.Tmax:
            severity = (1.+np.tanh(3.14*(self.Tend-time_since_start)/self.delta_end))/2.
        elif (time>self.Tend):
            severity = 0.
        severity *= self.maxseverity
        return severity


if __name__=='__main__':

    sc = SymptomsTanh(1)
    user_config = {
                'max_time': 
                {
                    'distribution': 'gaussian',
                    'parameters': 
                    {
                        'mean': 5,
                        'width_minus': 3,
                    }
                },
                'onset_time':
                {
                    'distribution': 'gaussian',
                    'parameters': 
                    {
                        'mean': 15,
                        'width_minus': 3,
                    }
                },
                'end_time':
                {
                    'distribution': 'gaussian',
                    'parameters': 
                    {
                        'mean': 15,
                        'width_minus': 3,
                    }
                }


            }


    sc = SymptomsTanh(None, user_config)

    print(sc.max_time)
    print(sc.onset_time)
    print(sc.end_time)


