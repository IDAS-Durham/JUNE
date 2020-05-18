import autofit as af

from june.demography.person import Person
from june.infection import infection as infect
from june.infection import symptoms as sym
from june.infection import symptoms_trajectory as strans
from june.infection import trajectory_maker as tmaker
from june.infection import transmission as trans
from june.infection.symptoms import SymptomsStep
from june.infection.health_index import HealthIndexGenerator

import os
import numpy as np

class Test_TrajectoryMaker:    
    def test__make__trajectories(self,trajectories):
        assert bool(len(trajectories.trajectories)==6) is True
        assert bool(trajectories.incubation_info==
                    [tmaker.VariationType.constant,sym.Symptom_Tags.infected,5.1]) is True
        assert bool(trajectories.recovery_info==
                    [tmaker.VariationType.constant,sym.Symptom_Tags.recovered,0.0]) is True
        assert bool(trajectories.trajectories[sym.Symptom_Tags.asymptomatic]==
                    [[tmaker.VariationType.constant,sym.Symptom_Tags.infected,5.1],
                     [tmaker.VariationType.constant,sym.Symptom_Tags.asymptomatic,14.],
                     [tmaker.VariationType.constant,sym.Symptom_Tags.recovered,0.0]]) is True

class Test_SymptomsTrajectory:    
    def test__right_frequency_in_health_index(self):
        N_samples    = 1000
        health_index = HealthIndexGenerator.from_file()(Person(age=27, sex='m'))     
        frequencies  = np.zeros(len(sym.Symptom_Tags))
        for i in range(N_samples):
            symptoms = SymptomsStep(health_index = health_index, time_offset=0.)
            symptoms.update_severity_from_delta_time(0.01)
            # check their symptoms matches the frequency in health index 
            if symptoms.tag != sym.Symptom_Tags.healthy:
                frequencies[symptoms.tag-2] += 1
        np.testing.assert_allclose(frequencies[0]/N_samples, health_index[0], atol=0.05)
        np.testing.assert_allclose(frequencies[1]/N_samples, health_index[1]-health_index[0],
                                   atol=0.05)
        np.testing.assert_allclose(frequencies[2]/N_samples, health_index[2]-health_index[1],
                                   atol=0.05)
        np.testing.assert_allclose(frequencies[3]/N_samples, health_index[3]-health_index[2],
                                   atol=0.05)
        np.testing.assert_allclose(frequencies[4]/N_samples, health_index[4]-health_index[3],
                                   atol=0.05)
            
    def test__construct__trajectory__from__maxseverity(self,trajectories,
                                                       symptoms_trajectories):
        dummy = Person(sex='m', age=65)
        symptoms_trajectories.max_severity = 0.9
        symptoms_trajectories.make_trajectory(trajectories,dummy)
        assert bool(symptoms_trajectories.trajectory==
                    [[0.0,sym.Symptom_Tags.infected],
                     [5.1,sym.Symptom_Tags.influenza],
                     [7.1,sym.Symptom_Tags.hospitalised],
                     [9.1,sym.Symptom_Tags.intensive_care],
                     [19.1,sym.Symptom_Tags.dead]]) is True        
        symptoms_trajectories.max_severity = 0.45
        symptoms_trajectories.make_trajectory(trajectories,dummy)
        assert bool(symptoms_trajectories.trajectory==
                    [[0.0,sym.Symptom_Tags.infected],
                     [5.1,sym.Symptom_Tags.influenza],
                     [7.1,sym.Symptom_Tags.hospitalised],
                     [9.1,sym.Symptom_Tags.intensive_care],
                     [29.1,sym.Symptom_Tags.hospitalised],
                     [49.1,sym.Symptom_Tags.recovered]]) is True        

    def test__symptoms__progression(self):
        selector       = infect.InfectionSelector()
        dummy          = Person(sex='m', age=65)
        infection      = selector.make_infection(person=dummy,time=0.1)
        fixed_severity = 0.8
        infection.symptoms.max_severity = fixed_severity
        max_tag        = infection.symptoms.max_tag(fixed_severity)
        assert bool(max_tag==sym.Symptom_Tags.hospitalised) is True
        infection.symptoms.trajectory = selector.trajectory_maker[max_tag,dummy]
        assert bool(infection.symptoms.trajectory==
                    [[0.0, sym.Symptom_Tags.infected],
                     [5.1, sym.Symptom_Tags.influenza],
                     [7.1, sym.Symptom_Tags.hospitalised],
                     [27.1, sym.Symptom_Tags.recovered]]) is True
        infection.update_at_time(float(1.))
        assert bool(infection.symptoms.tag==sym.Symptom_Tags.infected) is True
        infection.update_at_time(float(5.))
        assert bool(infection.symptoms.tag==sym.Symptom_Tags.infected) is True
        infection.update_at_time(float(6.))
        assert bool(infection.symptoms.tag==sym.Symptom_Tags.influenza) is True
        infection.update_at_time(float(10.))
        assert bool(infection.symptoms.tag==sym.Symptom_Tags.hospitalised) is True
        infection.update_at_time(float(20.))
        assert bool(infection.symptoms.tag==sym.Symptom_Tags.hospitalised) is True
        infection.update_at_time(float(30.))
        assert bool(infection.symptoms.tag==sym.Symptom_Tags.recovered) is True

