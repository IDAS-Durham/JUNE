import yaml
import random
from june.paths import configs_path

default_config_filename = configs_path / "defaults/groups/leisure/leisure_priority.yaml"


class SocialNetwork:

    def __init__(self):
        """
        Initialize the SocialNetwork class by loading and precomputing preferences from a YAML file.
        """
        self.household_vs_friends_priorities = self._load_and_precompute_preferences()

    def _load_and_precompute_preferences(self):
        """
        Load and precompute preferences from the YAML file into a dictionary for fast lookup.
        Precompute using 'm' and 'f' for gender keys.
        
        Returns:
            dict: Precomputed preferences mapping (activity, sex, age) -> weights.
        """
        with open(default_config_filename, "r") as file:
            raw_preferences = yaml.safe_load(file)

        precomputed = {}
        activity_preferences = raw_preferences["preferences"]["activity"]

        for activity, sexes in activity_preferences.items():
            for sex, age_groups in sexes.items():
                # Map 'male' -> 'm' and 'female' -> 'f'
                short_sex = "m" if sex.lower() == "male" else "f"
                for age_range, probs in age_groups.items():
                    min_age, max_age = map(int, age_range.split("-"))
                    for age in range(min_age, max_age + 1):
                        key = (activity, short_sex, age)
                        precomputed[key] = (probs["household"], probs["friends"])
        return precomputed

    def decide_target_group_invitation(self, person, activity):
        """
        Decide whether a person invites their household or friends first for an activity.
        
        Parameters:
            person: A Person object with `age` and `sex` attributes.
            activity (str): The activity type (e.g., "cinemas", "groceries").
            
        Returns:
            str: "household" or "friends"
        """
        key = (activity, person.sex.lower(), person.age)
        weights = self.household_vs_friends_priorities.get(key)

        if not weights:
            raise ValueError(
                f"No preferences found for activity '{activity}', sex '{person.sex}', and age {person.age}."
            )

        # Decide based on precomputed weights
        choice = random.choices(["household", "friends"], weights=weights, k=1)[0]
        return choice
    
