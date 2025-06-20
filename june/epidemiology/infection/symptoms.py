from random import random
from typing import Optional

import yaml
from june import paths
import numpy as np

from june.epidemiology.infection.disease_config import DiseaseConfig
from .symptom_tag import SymptomTag
from .trajectory_maker import TrajectoryMakers

#dead_tags = SymptomTag.dead_hospital


class Symptoms:
    __slots__ = (
        "disease_config",
        "tag",
        "max_tag",
        "max_severity",
        "trajectory",
        "stage",
        "time_of_symptoms_onset",
    )
    """
    Class to represent the symptoms of a person. The symptoms class composes the
    ``Infection`` class alongside the ``Transmission`` class. Once infected,
    a person is assigned a symptoms trajectory according to a health index generated
    by the ``HealthIndexGenerator``. A trajectory is a collection of symptom tags with
    characteristic timings.
    """

    def __init__(self, disease_config: DiseaseConfig, health_index=None):
        """
        Initialize the Symptoms class.

        Parameters
        ----------
        disease_config : DiseaseConfig
            Configuration object for the disease.
        health_index : np.ndarray, optional
            Health index to determine symptom trajectory.
        """
        self.disease_config = disease_config  # Store the DiseaseConfig instance
        self.max_tag = None
        self.tag = SymptomTag.from_string("exposed", disease_config.symptom_manager.symptom_tags)
        self.max_severity = random()
        self.trajectory = self._make_symptom_trajectory(
            disease_config, health_index
        )  # this also sets max_tag
        self.stage = 0
        self.time_of_symptoms_onset = self._compute_time_from_infection_to_symptoms(disease_config)


    def _compute_time_from_infection_to_symptoms(self, disease_config: DiseaseConfig) -> Optional[int]:
        """
        Compute the time from infection to the onset of visible symptoms.

        Parameters
        ----------
        disease_config : DiseaseConfig
            Preloaded DiseaseConfig object for the disease.

        Returns
        -------
        int or None
            The time (in days) from infection to symptom onset, or None if asymptomatic.
        """
        # Debug: Starting method

        # Extract relevant configuration data
        default_lowest_stage_value = disease_config.symptom_manager.default_lowest_stage
        dynamic_tags = disease_config.symptom_manager.symptom_tags
        asymptomatic_value = dynamic_tags.get("asymptomatic", None)

        # Iterate through the trajectory to calculate symptom onset time
        symptoms_onset = 0
        for completion_time, tag in self.trajectory:
            symptoms_onset += completion_time

            if tag == default_lowest_stage_value:
                # Stop at the stage defined as the default lowest stage for symptoms
                break
            elif tag == asymptomatic_value:
                # If the tag is asymptomatic, there is no visible symptom onset
                return None

        return symptoms_onset

    def _make_symptom_trajectory(self, disease_config: DiseaseConfig, health_index):
        """
        Generate the symptom trajectory dynamically based on the disease configuration.

        Parameters
        ----------
        disease_config : DiseaseConfig
            Preloaded configuration for the disease.
        health_index : ndarray
            The health index used to map individuals to symptom tags.

        Returns
        -------
        list
            A trajectory of symptom stages with timing information.
        """        
        # Use preloaded trajectory maker
        trajectory_maker = TrajectoryMakers.from_disease_config(disease_config)

        # Map health_index to probabilities using max_severity
        probability_index = np.searchsorted(health_index, self.max_severity)


        # Dynamically resolve the symptom tag using the probability index
        # Use a fallback tag if the index is out of range
        tag_name = next(
            (name for name, value in disease_config.symptom_manager.symptom_tags.items() if value == probability_index),
            disease_config.symptom_manager.default_lowest_stage,
        )

        self.max_tag = disease_config.symptom_manager.symptom_tags.get(tag_name, disease_config.symptom_manager.default_lowest_stage)

        # Retrieve the trajectory for the resolved symptom tag
        available_trajectories = trajectory_maker.trajectories

        if self.max_tag in available_trajectories:
            trajectory = available_trajectories[self.max_tag].generate_trajectory()
            return trajectory

        # Handle unexpected cases
        error_message = f"No trajectory found for symptom tag: {self.max_tag}"
        raise KeyError(error_message)
        
    
    '''def _make_symptom_trajectory(self, health_index):
        if health_index is None:
            return [(0, SymptomTag(0))]
        trajectory_maker = TrajectoryMakers.from_file()
        index_max_symptoms_tag = np.searchsorted(health_index, self.max_severity)
        self.max_tag = SymptomTag(index_max_symptoms_tag)
        return trajectory_maker[self.max_tag]'''

    def update_trajectory_stage(self, time_from_infection):
        """
        Updates the current symptom tag from the symptoms trajectory,
        given how much time has passed since the person was infected.

        Parameters
        ----------
        time_from_infection: float
            Time in days since the person got infected.
        """
        if time_from_infection > self.trajectory[self.stage + 1][0]:
            self.stage += 1
            self.tag = self.trajectory[self.stage][1]

    @property
    def time_exposed(self):
        return self.trajectory[1][0]

    @property
    def recovered(self):
        """
        Dynamically determine if the current symptom tag corresponds to any "recovered" stage.

        Returns
        -------
        bool
            True if the current symptom tag is a "recovered" stage, otherwise False.
        """
        # Retrieve the "recovered_stage" tags from the DiseaseConfig
        recovered_tags = self.disease_config.symptom_manager._resolve_tags("recovered_stage")
        return self.tag in recovered_tags

    @property
    def dead(self):
        """
        Dynamically determine if the current symptom tag corresponds to any "fatality" stage.
        """
        dead_tags = self.disease_config.symptom_manager._resolve_tags("fatality_stage")
        return self.tag in dead_tags
