from covid.infection.symptoms import Symptoms 

class SymptomsStep(Symptoms):
    def __init__(self, timer, health_index, user_parameters={}):
        required_parameters = ["time_offset", "end_time"]
        super().__init__(timer, health_index, user_parameters, required_parameters)
        self.Toffset = max(0.0, self.time_offset)
        self.Tend = max(0.0, self.end_time)

    def _calculate_severity(self, time):
        if time > self.starttime + self.Toffset and time < self.starttime + self.Tend:
            severity = self.maxseverity
        else:
            severity = 0.
        return severity

