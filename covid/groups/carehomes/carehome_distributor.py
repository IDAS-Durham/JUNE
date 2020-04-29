import numpy as np
from collections import OrderedDict
from covid.groups.carehomes import CareHome

class CareHomeDistributor:
    def __init__(self, min_age_in_carehome=65):
        self.min_age_in_carehome = min_age_in_carehome
        self.carehome_counter = 0
        pass

    def create_carehome_in_area(self, area, carehome_residents_number):
        """
        Crates carehome in area, if there needs to be one, and fills it with the
        oldest people.
        """
        if carehome_residents_number == 0:
            return None
        carehome = CareHome(self.carehome_counter, area, carehome_residents_number)
        area.carehome = carehome
        self.carehome_counter += 1
        self._put_people_to_carehome(carehome, area.men_by_age, area.women_by_age)
        return carehome

    def _put_people_to_carehome(
        self, carehome: CareHome, men_by_age: OrderedDict, women_by_age: OrderedDict
    ):
        """
        Takes the oldest men and women from men_by_age and women_by_age dictionaries,
        and puts them into the care home until max capacity is reached.
        """
        current_age_to_fill = max(
            np.max(list(men_by_age.keys())), np.max(list(women_by_age.keys()))
        )
        people_counter = 0
        while people_counter < carehome.n_residents:
            # fill until no old people or care home full
            if current_age_to_fill in men_by_age:
                man_to_fill = men_by_age[current_age_to_fill].pop()
                if (
                    len(men_by_age[current_age_to_fill]) == 0
                ):  # delete age key if empty list
                    del men_by_age[current_age_to_fill]
                man_to_fill.carehome = carehome
                carehome.people.append(man_to_fill)
            elif current_age_to_fill in women_by_age:
                woman_to_fill = women_by_age[current_age_to_fill].pop()
                if len(women_by_age[current_age_to_fill]) == 0:
                    del women_by_age[current_age_to_fill]
                carehome.people.append(woman_to_fill)
                woman_to_fill.carehome = carehome
            else:
                current_age_to_fill -= 1

            if current_age_to_fill <= self.min_age_in_carehome:
                break
