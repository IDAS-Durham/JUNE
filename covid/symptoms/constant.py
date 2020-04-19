from covid.symptoms import Symptoms 

class SymptomsConstant(Symptoms):
    def __init__(self, infection, user_parameters={}):
        required_parameters = ["time_offset", "end_time"]
        super().__init__(infection, user_parameters, required_parameters)
        self.Toffset = max(0.0, self.time_offset)
        self.Tend = max(0.0, self.end_time)

    def _calculate_severity(self, time):
        if time > self.infection.starttime + self.Toffset and time < self.infection.starttime + self.Tend:
            severity = self.maxseverity
        else:
            severity = 0.
        return severity



if __name__=='__main__':

    sc = SymptomsConstant(1)
    print(sc.time_offset)
    print(sc.end_time)

    user_config = {
                'time_offset': 
                {
                    'distribution': 'gaussian',
                    'parameters': 
                    {
                        'mean': 5,
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


    sc = SymptomsConstant(None, user_config)
    print(sc.time_offset)
    print(sc.end_time)
