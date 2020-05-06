import numpy as np
import pandas as pd

from covid.groups import Person, Box
from covid.groups.people import HealthIndex
from covid.inputs import Inputs


def get_age_brackets(nomis_age_bin):
    """Auxiliary function to get the age delimiters of a nomis bin"""
    try:
        age_1, age_2 = nomis_age_bin.split("-")
        if age_2 == "XXX":
            age_2 = 99
    except:
        age_1 = int(nomis_age_bin)
        age_2 = age_1
    return int(age_1), int(age_2)


class BoxGenerator(Box):
    def __init__(self, world=None, region=None, n_people=None):
        """Generates a simulation box where all people interact with each other.
        If you just want a box with random people with random sex (50/50) and a random
        age (uniform across 0 to 99) then just leave region as None or set it to "random".
        On the other hand, the population can be initialized from census data by 
        setting the name of the region in the region parameter.

        Parameters
        ----------
        world : 
            An instance of the World class (optional, will be passed to the created people)
        region :
            A string with the name of the region or "random".

        n_people:
            Number of people to initialize in the random mode.
        """
        super().__init__()
        self.world = world
        self.health_index_gen = HealthIndex()
        if region is not None:
            if n_people is not None:
                print(
                    "warning, specifying number of people has no effect when specifying",
                    "a region as well. Number of people will be read from census data directly."
                )
            self.create_box_from_region(region)
        if region is None or region == "random":
            if n_people is None:
                n_people = 1000
            self.create_random_box(n_people)

    def create_box_from_region(self, region):
        """
        We read from the census data the number of people, and their age and sex distributions. 
        We sample uniformly inside each age bin, and we assign a health index based on the age.
        """
        inputs = Inputs(zone=region)
        n_residents, age_freq, sex_freq = self.from_file(inputs)
        # sex numbers
        number_of_men = (
                n_residents["n_residents"].values * sex_freq["males"].values
        )
        number_of_men = int(number_of_men.sum())
        number_of_women = (
                n_residents["n_residents"].values * sex_freq["females"].values
        )
        number_of_women = int(number_of_women.sum())
        self.n_people = number_of_men + number_of_women
        # ages. since Nomis works in bins, I have to sample an age, this will be improved in the future TODO
        age_counts = age_freq
        age_bins = age_counts.columns  # get age bins from column names
        # need to add for all output areas
        age_counts_total = age_counts.values * n_residents.values
        # and sum over all areas
        age_counts_total = age_counts_total.sum(axis=0).astype(np.int)
        assert age_counts_total.sum() == self.n_people
        # we now create an array with as many ages as people
        ages_expanded = None
        for i, age_bin in enumerate(age_bins):
            # for each age bin, create n ages where n is the number of people with that age.
            age_1, age_2 = get_age_brackets(age_bin)
            if age_1 == age_2:
                age_array = age_1 * np.ones(age_counts_total[i], dtype=np.int)
            else:
                age_array = np.random.randint(age_1, age_2, age_counts_total[i])
            if ages_expanded is None:
                ages_expanded = age_array
            else:
                ages_expanded = np.concatenate((ages_expanded, age_array))
        np.random.shuffle(ages_expanded)
        assert len(ages_expanded) == self.n_people
        age_counter = 0
        # init all men
        for _ in range(number_of_men):
            sex = 0
            age = ages_expanded[age_counter]
            health_index = self.health_index_gen.get_index_for_age(age)
            person = Person(
                age=age, sex=sex, health_index=health_index
            )
            age_counter += 1
            self.people.add(person)

        for _ in range(number_of_women):
            sex = 1
            age = ages_expanded[age_counter]
            health_index = self.health_index_gen.get_index_for_age(age)
            person = Person(
                age=age, sex=sex, health_index=health_index
            )
            age_counter += 1
            self.people.add(person)

    def from_file(self, inputs):
        """
        Parameters
        ----------
        n_residents_file:
            Nr. of residents per area
        age_freq_file:
            Nr of people wihin age-range per area
        sex_freq_file:
            Nr of people per sec per area
        """
        n_residents = pd.read_csv(
            inputs.n_residents_file,
            names=["output_area", "n_residents"],
            header=0,
            index_col="output_area",
        )
        age_freq = pd.read_csv(inputs.age_freq_file, index_col="output_area")
        age_freq = age_freq.div(age_freq.sum(axis=1), axis=0)
        sex_freq = pd.read_csv(inputs.sex_freq_file, index_col="output_area")
        sex_freq = sex_freq.div(sex_freq.sum(axis=1), axis=0)
        return n_residents, age_freq, sex_freq

    def create_random_box(self, n_people):
        """
        Random box of n_people. Sex is kept 50/50, and age is uniformly sampled from 0 to 99.
        """
        self.n_people = n_people
        # Assign equal men and women. If odd, add one more woman.
        if n_people % 2 == 0:
            n_women = n_people // 2
            n_men = n_people // 2
        else:
            n_women = n_people // 2 + 1
            n_men = n_people // 2

        sex_shuffle_array = np.concatenate((np.zeros(n_men), np.ones(n_women)))
        np.random.shuffle(sex_shuffle_array)

        # If there are fewer than 100 people, then select random ages to initialize.
        possible_ages = np.arange(1, 100)
        if n_people < len(possible_ages):
            selected_ages = np.random.choice(possible_ages, n_people, replace=False)
        else:
            selected_ages = possible_ages
        people_per_age = n_people // len(selected_ages)
        people_per_age_array = people_per_age * np.ones(
            len(selected_ages), dtype=np.int
        )
        # fill remaining people in random age groups
        remaining_people = n_people % len(selected_ages)
        if remaining_people != 0:
            random_ages = np.random.choice(
                np.arange(0, len(possible_ages)), remaining_people, replace=False
            )
            people_per_age_array[random_ages] += 1

        age_shuffle_array = np.concatenate(
            [selected_ages[i] * np.ones(age_count) for i, age_count in enumerate(people_per_age_array)]
        )
        # initialize people
        assert len(age_shuffle_array) == len(sex_shuffle_array)
        for i in range(0, n_people):
            age = age_shuffle_array[i]
            sex = sex_shuffle_array[i]
            health_index = self.health_index_gen.get_index_for_age(age)
            person = Person(
                age=age,
                sex=sex,
                health_index=health_index,
            )
            self.people.add(person)
