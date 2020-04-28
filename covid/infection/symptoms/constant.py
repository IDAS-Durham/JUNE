import numpy as np
from scipy import stats
from covid.infection.symptoms import Symptoms


class SymptomsConstant(Symptoms):
    def __init__(self, timer, health_index, user_parameters=None):
        user_parameters = user_parameters or dict()
        required_parameters = ["recovery_rate"]
        super().__init__(timer, health_index, user_parameters, required_parameters)
        self.predicted_recovery_time = self.predict_recovery_time()

    def predict_recovery_time(self):
        """
        If the probabiliy of recovery per day is p, then the recovery day can be estimated 
        by sampling from a geometric distribution with parameter p.
        """
        days_to_recover = stats.expon.rvs(scale=1.0 / self.recovery_rate)
        # day_of_recovery = self.timer.now + days_to_recover
        return days_to_recover

    def is_recovered(self):
        deltat = self.timer.now - self.timer.previous
        prob_recovery = 1.0 - np.exp(-self.recovery_rate * deltat)
        if np.random.rand() <= prob_recovery:
            return True
        else:
            return False

    def update_severity(self):
        self.last_time_updated = self.timer.now
        self.severity = self.maxseverity


if __name__ == "__main__":

    sc = SymptomsConstant(1)
    print(sc.time_offset)
    print(sc.end_time)

    user_config = {
        "time_offset": {
            "distribution": "gaussian",
            "parameters": {"mean": 5, "width_minus": 3,},
        },
        "end_time": {
            "distribution": "gaussian",
            "parameters": {"mean": 15, "width_minus": 3,},
        },
    }

    sc = SymptomsConstant(None, user_config)
    print(sc.time_offset)
    print(sc.end_time)
