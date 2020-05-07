import numpy as np
from collections import OrderedDict
from covid.groups import CareHome
from covid.groups import Area


class CareHomeError(BaseException):
    pass


class CareHomeDistributor:
    def __init__(self, min_age_in_carehome: int = 65):
        """
        Tool to distribute people from a certain area into a carehome, if there is one.

        Parameters
        ----------
        min_age_in_carehome
            minimum age to put people in carehome.
        """
        self.min_age_in_carehome = min_age_in_carehome

    def create_carehome_in_area(self, area: Area, carehome_residents_number: int):
        """
        Crates carehome in area, if there needs to be one, and fills it with the
        oldest people in that area.

        Parameters
        ----------
        area:
            area in which to create the carehome
        carehome_residents_number:
            number of people to put in the carehome.
        """
        if carehome_residents_number == 0:
            raise CareHomeError("No carehome residents in this area.")
        carehome = CareHome(area, carehome_residents_number)
        area.carehome = carehome
        self._put_people_to_carehome(carehome, area.men_by_age, area.women_by_age)
        return carehome

    def _get_person_of_age(self, people_dict: dict, age: int):
        person = people_dict[age].pop()
        if len(people_dict[age]) == 0:  # delete age key if empty list
            del people_dict[age]
        return person

    def _put_people_to_carehome(
        self, carehome: CareHome, men_by_age: OrderedDict, women_by_age: OrderedDict
    ):
        """
        Takes the oldest men and women from men_by_age and women_by_age dictionaries,
        and puts them into the care home until max capacity is reached.

        Parameters
        ----------
        carehome:
            carehome where to put people
        men_by_age:
            dictionary containing age as keys and lists of men as values.
        women_by_age:
            dictionary containing age as keys and lists of women as values.
        """
        current_age_to_fill = max(
            np.max(list(men_by_age.keys())), np.max(list(women_by_age.keys()))
        )
        people_counter = 0
        while people_counter < carehome.n_residents:
            # fill until no old people or care home full
            next_age = True
            for people_dict in [men_by_age, women_by_age]:
                if current_age_to_fill in people_dict.keys():
                    person = self._get_person_of_age(people_dict, current_age_to_fill)
                    person.carehome = carehome
                    carehome.people.add(person)
                    people_counter += 1
                    if people_counter == carehome.n_residents:
                        break
                    next_age = next_age and False
                else:
                    next_age = (
                        next_age and True
                    )  # only decrease age if there are no man nor women left

            if next_age:
                current_age_to_fill -= 1
                if current_age_to_fill < self.min_age_in_carehome:
                    break
