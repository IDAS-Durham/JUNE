import autofit as af
from june.infection import symptoms as sym
from june.infection import symptom_trajectory as strans

import os
import numpy as np


class TestTrajectoryMaker:
    def test__make__trajectories(tmaker):
        tmaker = strans.TrajectoryMaker(parameters=None)
        assert bool(len(tmaker.trajectories)==5) is True
        assert bool(tmaker.incubation_info==[strans.VariationType.constant,"asymptomatic",5.1]) is True
        assert bool(tmaker.trajectories["asymptomatic"]==[[strans.VariationType.constant,"asymptomatic",5.1],
                                                          [strans.VariationType.constant,"asymptomatic",14.]]) is True


class TestSymptomTrajectory:
    def __init__(self):
        self.symptoms = strans.SymptomsTrajectory(health_index=[0.1, 0.2, 0.3, 0.4, 0.5])
        
    def test__construct__trajectory__from__maxseverity(self):
        self.symptoms.max_severity = 0.9
        self.symptoms.make_trajectory()
        #print(self.symptoms.trajectory)
        assert bool(self.symptoms.trajectory==
                    [[5.1,"asymptomatic"],
                     [7.1,"influenza-like illness"],
                     [9.1,"hospitalised"],
                     [19.1,"intensive care"],
                     [19.1,"death"]]) is True        

    def test__times(self):
        pass
        
    
if __name__=="__main__":
    tmaker = strans.TrajectoryMaker(None)
    TestTrajectoryMaker.test__make__trajectories(tmaker)
    tester = TestSymptomTrajectory()
    tester.test__construct__trajectory__from__maxseverity()
    tester.test__times()
