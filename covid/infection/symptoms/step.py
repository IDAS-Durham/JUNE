from covid.infection.symptoms import Symptoms


class SymptomsStep(Symptoms):
    def __init__(self, timer, health_index, user_parameters={}):
        required_parameters = ["time_offset", "end_time"]
        super().__init__(timer, health_index, user_parameters, required_parameters)
        self.time_offset = max(0.0, self.time_offset)
        self.end_time = max(0.0, self.end_time)

    def update_severity(self):
        time = self.timer.now
        if (
            time > self.infection_start_time + self.time_offset
            and time < self.infection_start_time + self.end_time
        ):
            severity = self.maxseverity
        else:
            severity = 0.0

        self.last_time_updated = time
        self.severity = severity
