from enum import IntEnum

import yaml
from enum import IntEnum

class SymptomTag(IntEnum):
    """
    A tag for the symptoms exhibited by a person.

    Higher numbers are more severe.
    """

    @classmethod
    def load_from_yaml(cls, yaml_path: str):
        """
        Dynamically load symptom tags from a YAML file.

        Parameters
        ----------
        yaml_path : str
            Path to the YAML file containing symptom tag definitions.

        Returns
        -------
        dict
            A dictionary mapping symptom tag names to their values.
        """
        with open(yaml_path, "r") as f:
            config = yaml.safe_load(f)

        symptom_tags = config.get("disease", {}).get("symptom_tags", [])
        if not symptom_tags:
            raise ValueError(f"No 'symptom_tags' found in YAML at {yaml_path}")

        return {tag["name"]: tag["value"] for tag in symptom_tags}

    @classmethod
    def from_string(cls, string: str, dynamic_tags: dict = None) -> "SymptomTag":
        """
        Convert a string to a SymptomTag, checking both static and dynamic tags.

        Parameters
        ----------
        string : str
            The name of the symptom tag.

        dynamic_tags : dict, optional
            A dictionary of dynamically loaded tags.

        Returns
        -------
        SymptomTag
        """


        # Check static tags first
        for item in SymptomTag:
            if item.name == string:
                return item

        # Check dynamic tags if provided
        if dynamic_tags and string in dynamic_tags:
            return dynamic_tags[string]

        raise ValueError(f"{string} is not a valid SymptomTag")

'''
class SymptomTag(IntEnum):
    """
    A tag for the symptoms exhibited by a person.

    Higher numbers are more severe.
    0 - 5 correspond to indices in the health index array.
    """

    recovered = -2
    healthy = -1
    exposed = 0
    asymptomatic = 1
    rash = 2
    hospitalised = 3
    dead_hospital = 4

    @classmethod
    def from_string(cls, string: str) -> "SymptomTag":
        for item in SymptomTag:
            if item.name == string:
                return item
        raise AssertionError(f"{string} is not the name of a SymptomTag")
'''