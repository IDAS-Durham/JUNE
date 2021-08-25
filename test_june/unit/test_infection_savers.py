import h5py
import pytest
import numpy as np

from june.epidemiology.infection.transmission_xnexp import TransmissionXNExp
from june.epidemiology.infection.transmission import TransmissionGamma
from june.epidemiology.infection.symptoms import Symptoms, SymptomTag
from june.epidemiology.infection import Infection, Immunity
from june.hdf5_savers.infection_savers import (
    save_transmissions_to_hdf5,
    load_transmissions_from_hdf5,
    save_symptoms_to_hdf5,
    load_symptoms_from_hdf5,
    save_infections_to_hdf5,
    load_infections_from_hdf5,
    save_immunities_to_hdf5,
    load_immunities_from_hdf5
)

@pytest.fixture(name="xnexp_transmissions", scope="module")
def setup_xnexp_trans():
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
    return transmissions

@pytest.fixture(name="gamma_transmissions", scope="module")
def setup_gamma_trans():
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
    return transmissions

@pytest.fixture(name="symptoms_list", scope="module")
def setup_symptoms():
    health_index = np.linspace(0, 1, 5)
    symptoms1 = Symptoms(health_index=health_index)
    symptoms2 = Symptoms(health_index=health_index)
    symptoms = [symptoms1, symptoms2]
    return symptoms

@pytest.fixture(name="infections", scope="module")
def setup_infections(xnexp_transmissions, symptoms_list):
    infections = []
    for symptoms, trans in zip(symptoms_list, xnexp_transmissions):
        infection = Infection(transmission=trans, symptoms=symptoms, start_time=2)
        infections.append(infection)
    return infections

class TestTransmissionSavers:
    def test__save_xnexp(self, xnexp_transmissions, test_results):
        with h5py.File(test_results / "checkpoint_tests.hdf5", "w") as f:
            pass
        save_transmissions_to_hdf5(test_results / "checkpoint_tests.hdf5", xnexp_transmissions, chunk_size=1)
        transmissions_recovered = load_transmissions_from_hdf5(
            test_results / "checkpoint_tests.hdf5", chunk_size=1
        )
        assert len(transmissions_recovered) == len(xnexp_transmissions)
        for transmission, transmission_recovered in zip(
            xnexp_transmissions, transmissions_recovered 
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
                    transmission_recovered, attribute
                )

    def test__save_gamma(self, gamma_transmissions, test_results):
        with h5py.File(test_results / "checkpoint_tests.hdf5", "w") as f:
            pass
        save_transmissions_to_hdf5(test_results / "checkpoint_tests.hdf5", gamma_transmissions, chunk_size=1)
        transmissions_recovered = load_transmissions_from_hdf5(
            test_results / "checkpoint_tests.hdf5", chunk_size=1
        )
        assert len(transmissions_recovered) == len(gamma_transmissions)
        for transmission, transmission_recovered in zip(
            gamma_transmissions, transmissions_recovered 
        ):
            for attribute in ["shape", "shift", "scale", "norm", "probability"]:
                assert getattr(transmission, attribute) == getattr(
                    transmission_recovered, attribute
                )


class TestSymptomSavers:
    def test__save_symptoms(self, symptoms_list, test_results):
        with h5py.File(test_results / "checkpoint_tests.hdf5", "w") as f:
            pass
        save_symptoms_to_hdf5(test_results / "checkpoint_tests.hdf5", symptoms_list, chunk_size=1)
        symptoms_recovered = load_symptoms_from_hdf5(
            test_results / "checkpoint_tests.hdf5", chunk_size=1
        )
        assert len(symptoms_recovered) == len(symptoms_list)
        for symptom, symptom_recovered in zip(symptoms_list, symptoms_recovered):
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

class TestInfectionSavers:
    def test__save_infection(self, infections, test_results):
        with h5py.File(test_results / "checkpoint_tests.hdf5", "w") as f:
            pass
        save_infections_to_hdf5(test_results / "checkpoint_tests.hdf5", infections, chunk_size=1)
        infections_recovered= load_infections_from_hdf5(
            test_results / "checkpoint_tests.hdf5", chunk_size=1
        )
        assert len(infections_recovered) == len(infections)
        for infection, infection_recovered in zip(infections, infections_recovered):
            for attribute_name in [
                "start_time",
            ]:
                assert getattr(infection, attribute_name) == getattr(
                    infection_recovered, attribute_name
                )
            symptoms = infection.symptoms
            symptoms_recovered = infection_recovered.symptoms
            for attribute_name in [
                "max_tag",
                "tag",
                "max_severity",
                "stage",
                "time_of_symptoms_onset",
            ]:
                assert getattr(symptoms, attribute_name) == getattr(
                    symptoms_recovered, attribute_name
                )
            trajectory = symptoms.trajectory
            trajectory_recovered = symptoms_recovered.trajectory
            assert len(trajectory) == len(trajectory_recovered)
            for stage, stage_recovered in zip(trajectory, trajectory_recovered):
                assert isinstance(stage_recovered[1], SymptomTag)
                assert stage[0] == stage_recovered[0]
                assert stage[1] == stage_recovered[1]
            transmission = infection.transmission
            transmission_recovered = infection_recovered.transmission
            for attribute in [
                "time_first_infectious",
                "norm_time",
                "n",
                "norm",
                "alpha",
                "probability",
            ]:
                assert getattr(transmission, attribute) == getattr(
                    transmission_recovered, attribute
                )

class TestImmunitySavers:
    def test__save_immunities(self, test_results):
        with h5py.File(test_results / "checkpoint_tests.hdf5", "w") as f:
            pass
        immunities = []
        for i in range(100):
            susc_dict = {i: i / 10}
            imm = Immunity(susc_dict)
            immunities.append(imm)
        save_immunities_to_hdf5(test_results / "checkpoint_tests.hdf5", immunities)
        immunities_recovered = load_immunities_from_hdf5(test_results / "checkpoint_tests.hdf5", chunk_size = 2)
        assert len(immunities) == len(immunities_recovered)
        for imm, immr in zip(immunities, immunities_recovered):
            assert imm.susceptibility_dict == immr.susceptibility_dict
