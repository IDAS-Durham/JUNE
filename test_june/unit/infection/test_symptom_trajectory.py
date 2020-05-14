import autofit as af

from june.demography.person import Person
from june.infection import infection as infect
from june.infection import symptoms as sym, Symptom_Tags 
from june.infection import symptom_trajectory as strans
from june.infection import transmission as trans
from june.infection.symptoms import SymptomsStep
from june.infection.health_index import HealthIndexGenerator
from june.infection.symptoms import Symptom_Tags

import os
import numpy as np

class Test_TrajectoryMaker:    
    def test__make__trajectories(self,trajectories):
        assert bool(len(trajectories.trajectories)==6) is True
        assert bool(trajectories.incubation_info==[strans.VariationType.constant,Symptom_Tags.infected,5.1]) is True
        assert bool(trajectories.recovery_info==[strans.VariationType.constant,Symptom_Tags.recovered,0.0]) is True
        assert bool(trajectories.trajectories[Symptom_Tags.asymptomatic]==
                    [[strans.VariationType.constant,Symptom_Tags.infected,5.1],
                     [strans.VariationType.constant,Symptom_Tags.asymptomatic,14.],
                     [strans.VariationType.constant,Symptom_Tags.recovered,0.0]]) is True

class Test_SymptomsTrajectory:    
    def test__right_frequency_in_health_index(self):
        N_samples = 1000
        health_index = HealthIndexGenerator.from_file()(27, 'm')
        
        frequencies = np.zeros(len(Symptom_Tags))
        for i in range(N_samples):
            symptoms = SymptomsStep(health_index = health_index, time_offset=0.)
            symptoms.update_severity_from_delta_time(0.01)
            # check their symptoms matches the frequency in health index 
            if symptoms.tag != Symptom_Tags.healthy:
                frequencies[symptoms.tag-2] += 1
        #for index in range(5):
        #    print(Symptom_Tags(index),":",frequencies[index]/N_samples)
        np.testing.assert_allclose(frequencies[0]/N_samples, health_index[0], atol=0.05)
        np.testing.assert_allclose(frequencies[1]/N_samples, health_index[1]-health_index[0], atol=0.05)
        np.testing.assert_allclose(frequencies[2]/N_samples, health_index[2]-health_index[1], atol=0.05)
        np.testing.assert_allclose(frequencies[3]/N_samples, health_index[3]-health_index[2], atol=0.05)
        np.testing.assert_allclose(frequencies[4]/N_samples, health_index[4]-health_index[3], atol=0.05)
            
    def test__construct__trajectory__from__maxseverity(self,trajectories, symptoms_trajectories, person=None):
        symptoms_trajectories.max_severity = 0.9
        assert bool(symptoms_trajectories.make_trajectory(trajectories,person)==
                    [[0.0,Symptom_Tags.infected],
                     [5.1,Symptom_Tags.influenza],
                     [7.1,Symptom_Tags.hospitalised],
                     [9.1,Symptom_Tags.intensive_care],
                     [19.1,Symptom_Tags.dead]]) is True        
        symptoms_trajectories.max_severity = 0.45
        assert bool(symptoms_trajectories.make_trajectory(trajectories,person)==
                    [[0.0,Symptom_Tags.infected],
                     [5.1,Symptom_Tags.influenza],
                     [7.1,Symptom_Tags.hospitalised],
                     [9.1,Symptom_Tags.intensive_care],
                     [29.1,Symptom_Tags.hospitalised],
                     [49.1,Symptom_Tags.recovered]]) is True        

    def test__infected_person_infects(self,transmission, trajectories):
        health_index_generator = HealthIndexGenerator.from_file()
        dummy                  = Person(sex='m', age=65)
        health_index           = health_index_generator(dummy.age, dummy.sex)
        fixed_severity         = 0.8
        symptoms = strans.SymptomsTrajectory(health_index = health_index,
                                             trajectory_maker = trajectories,
                                             patient = dummy)
        infection = infect.Infection(start_time=0.1, transmission=transmission,
                                     symptoms=symptoms,trajectory_maker = trajectories)
        infection.infect_person_at_time(person=dummy, health_index_generator=health_index_generator, time=0.2)
        # fix a max_severity in dummy's symptoms to guarantee a trajectory
        dummy.health_information.infection.symptoms.max_severity = fixed_severity
        max_tag = dummy.health_information.infection.symptoms.max_tag(fixed_severity)
        assert bool(max_tag==Symptom_Tags.hospitalised) is True
        dummy.health_information.infection.symptoms.trajectory = trajectories[max_tag,dummy]
        assert bool(dummy.health_information.infection.symptoms.trajectory==
                    [[0.0, Symptom_Tags.infected], [5.1, Symptom_Tags.influenza],
                     [7.1, Symptom_Tags.hospitalised], [27.1, Symptom_Tags.recovered]]) is True
        dummy.health_information.infection.update_at_time(float(0))
        assert bool(dummy.health_information.tag==Symptom_Tags.infected) is True
        dummy.health_information.infection.update_at_time(float(5))
        assert bool(dummy.health_information.tag==Symptom_Tags.infected) is True
        dummy.health_information.infection.update_at_time(float(6))
        assert bool(dummy.health_information.tag==Symptom_Tags.influenza) is True
        dummy.health_information.infection.update_at_time(float(10))
        assert bool(dummy.health_information.tag==Symptom_Tags.hospitalised) is True
        dummy.health_information.infection.update_at_time(float(20))
        assert bool(dummy.health_information.tag==Symptom_Tags.hospitalised) is True
        dummy.health_information.infection.update_at_time(float(30))
        assert bool(dummy.health_information.tag==Symptom_Tags.recovered) is True
    
if __name__=="__main__":
    transmission = trans.TransmissionConstant(probability=0.3)
    test__make__trajectories(trajectories)
    test__right_frequency_in_health_index()
    test__construct__trajectory__from__maxseverity(trajectories,symptoms)
    test__infected_person_infects(transmission, trajectories)
