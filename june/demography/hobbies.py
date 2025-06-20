from june.paths import configs_path
import yaml
import random

default_config_filename = configs_path / "defaults/demography/hobbies.yaml"

class HobbyGenerator:
    """
    A class to manage hobbies, including loading data, precomputing probabilities,
    and assigning hobbies based on gender and age.
    """


    def __init__(self, yaml_file=None):
        """
        Initialize the Hobbies class by loading data from a YAML file,
        precomputing probabilities, and discarding intermediate data.

        Parameters
        ----------
        yaml_file : str, optional
            Path to the YAML file containing hobby data. If not provided, uses the default.
        """
        # Load YAML and compute precomputed_data in one method
        self.precomputed_data = self._precompute_data(default_config_filename)

    def _precompute_data(self, file_path):
        """
        Precompute normalized probabilities for all age-sex combinations
        and store them as a flat mapping for fast lookup.

        Parameters
        ----------
        file_path : str
            Path to the YAML file.

        Returns
        -------
        dict
            Precomputed normalized probabilities for hobbies.
        """
        # Load YAML data
        with open(file_path, "r") as file:
            hobby_data = yaml.safe_load(file)

        precomputed = {}
        sex_map = {"male": "m", "female": "f"}

        for details in hobby_data["hobbies"].values():
            for long_sex, short_sex in sex_map.items():
                for age_bin, category_prob in details["probability"].get(long_sex, {}).items():
                    # Calculate raw probabilities for sub-hobbies
                    sub_hobby_probs = {
                        sub_hobby: category_prob * sub_prob
                        for sub_hobby, sub_prob in details["options"].items()
                    }

                    # Normalize the probabilities
                    total_weight = sum(sub_hobby_probs.values())
                    normalized_probs = (
                        {hobby: weight / total_weight for hobby, weight in sub_hobby_probs.items()}
                        if total_weight > 0
                        else {}
                    )

                    # Store in a flat structure: {(sex, age_bin): {hobby: normalized_weight}}
                    key = (short_sex, age_bin)
                    if key not in precomputed:
                        precomputed[key] = {}
                    precomputed[key].update(normalized_probs)

        return precomputed

    def assign_hobbies(self, sex, age):
        """
        Assign hobbies to a person based on their gender and age by directly using precomputed probabilities.

        Parameters
        ----------
        sex : str
            "m" or "f".
        age : int
            Age of the person.

        Returns
        -------
        list
            A list of 1-2 unique hobbies assigned to the person.
        """
        # Determine the age bin
        age_bin = self._determine_age_bin(age)

        # Retrieve precomputed probabilities
        key = (sex, age_bin)
        sub_hobby_probs = self.precomputed_data.get(key, {})

        if not sub_hobby_probs:
            return []  # No hobbies available for this combination

        # Select 1-2 unique hobbies based on precomputed probabilities
        hobbies = list(sub_hobby_probs.keys())
        weights = list(sub_hobby_probs.values())

        # Ensure we don't select more hobbies than available
        num_hobbies = min(random.randint(1, 2), len(hobbies))

        # Use random.choices if there's only one hobby, otherwise random.sample with weights
        if num_hobbies == 1:
            return random.choices(hobbies, weights=weights, k=num_hobbies)
        else:
            selected_hobbies = random.sample(
                population=[
                    (hobby, weight) for hobby, weight in zip(hobbies, weights)
                ],
                k=num_hobbies,
            )
            return [hobby for hobby, _ in selected_hobbies]

    def _determine_age_bin(self, age):
        """
        Determine the age bin for a given age.

        Parameters
        ----------
        age : int
            The age of the person.

        Returns
        -------
        str
            The corresponding age bin as a string.
        """
        if age <= 4:
            return "0-4"
        elif age <= 9:
            return "5-9"
        elif age <= 14:
            return "10-14"
        elif age <= 19:
            return "15-19"
        elif age <= 29:
            return "20-29"
        elif age <= 39:
            return "30-39"
        elif age <= 49:
            return "40-49"
        elif age <= 59:
            return "50-59"
        else:
            return "60+"