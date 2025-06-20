from june.epidemiology.infection.disease_config import DiseaseConfig
from june.groups import Supergroup, Group


class Cemetery(Group):
    def add(self, person):
        self[0].people.append(person)


class Cemeteries(Supergroup):
    def __init__(self):
        """
        Initializes Cemeteries with a single Cemetery object.

        Parameters
        ----------
        disease_config : DiseaseConfig
            The disease-specific configuration object.
        """
        super().__init__([Cemetery()])

    def get_nearest(self, person):
        return self.members[0]
