import h5py
import numpy as np

from june.infection.transmission_xnexp import TransmissionXNExp
from june.infection.transmission import TransmissionGamma
from june.infection.symptoms import Symptoms, SymptomTag
from june.hdf5_savers.infection_savers import (
    save_transmissions_to_hdf5,
    load_transmissions_from_hdf5,
    save_symptoms_to_hdf5,
    load_symptoms_from_hdf5,
)


class TestTransmissionSavers:
    def test__save_xnexp(self):
        with h5py.File("checkpoint_tests.hdf5", "w") as f:
            pass
        transmission1 = TransmissionXNExp(
            max_probability=1,
            time_first_infectious=1,
            norm_time=2,
            n=3,
            alpha=4,
            max_symptoms="asymptomatic",
            asymptomatic_infectious_factor=5,
            mild_infectious_factor=6,
        )
        transmission2 = TransmissionXNExp(
            max_probability=7,
            time_first_infectious=8,
            norm_time=9,
            n=10,
            alpha=11,
            max_symptoms="mild",
            asymptomatic_infectious_factor=12,
            mild_infectious_factor=13,
        )
        transmissions = [transmission1, transmission2]
        save_transmissions_to_hdf5("checkpoint_tests.hdf5", transmissions, chunk_size=1)
        transmissions_recovered = load_transmissions_from_hdf5(
            "checkpoint_tests.hdf5", chunk_size=1
        )
        assert len(transmissions_recovered) == len(transmissions)
        for transmission, transmissions_recovered in zip(
            transmissions_recovered, transmissions
        ):
            for attribute in [
                "time_first_infectious",
                "norm_time",
                "n",
                "norm",
                "alpha",
                "probability",
            ]:
                assert getattr(transmission, attribute) == getattr(
                    transmissions_recovered, attribute
                )

    def test__save_gamma(self):
        with h5py.File("checkpoint_tests.hdf5", "w") as f:
            pass
        transmission1 = TransmissionGamma(
            max_infectiousness=1.0,
            shape=2.0,
            rate=3.0,
            shift=-2.0,
            max_symptoms="mild",
            asymptomatic_infectious_factor=0.5,
            mild_infectious_factor=0.7,
        )
        transmission2 = TransmissionGamma(
            max_infectiousness=1.1,
            shape=2.1,
            rate=3.1,
            shift=-2.1,
            max_symptoms="asymptomatic",
            asymptomatic_infectious_factor=0.2,
            mild_infectious_factor=0.2,
        )
        transmissions = [transmission1, transmission2]
        save_transmissions_to_hdf5("checkpoint_tests.hdf5", transmissions, chunk_size=1)
        transmissions_recovered = load_transmissions_from_hdf5(
            "checkpoint_tests.hdf5", chunk_size=1
        )
        assert len(transmissions_recovered) == len(transmissions)
        for transmission, transmissions_recovered in zip(
            transmissions_recovered, transmissions
        ):
            for attribute in ["shape", "shift", "scale", "norm", "probability"]:
                assert getattr(transmission, attribute) == getattr(
                    transmissions_recovered, attribute
                )


class TestSymptomSavers:
    def test__save_symptoms(self):
        with h5py.File("checkpoint_tests.hdf5", "w") as f:
            pass
        health_index = np.linspace(0, 1, 5)
        symptoms1 = Symptoms(health_index=health_index)
        symptoms2 = Symptoms(health_index=health_index)
        symptoms = [symptoms1, symptoms2]
        save_symptoms_to_hdf5("checkpoint_tests.hdf5", symptoms, chunk_size=1)
        symptoms_recovered = load_symptoms_from_hdf5(
            "checkpoint_tests.hdf5", chunk_size=1
        )
        assert len(symptoms_recovered) == len(symptoms)
        for symptom, symptom_recovered in zip(symptoms, symptoms_recovered):
            for attribute_name in [
                "max_tag",
                "tag",
                "max_severity",
                "stage",
                "time_of_symptoms_onset",
            ]:
                assert getattr(symptom, attribute_name) == getattr(
                    symptom_recovered, attribute_name
                )
            trajectory = symptom.trajectory
            trajectory_recovered = symptom_recovered.trajectory
            assert len(trajectory) == len(trajectory_recovered)
            for stage, stage_recovered in zip(trajectory, trajectory_recovered):
                assert isinstance(stage_recovered[1], SymptomTag)
                assert stage[0] == stage_recovered[0]
                assert stage[1] == stage_recovered[1]
