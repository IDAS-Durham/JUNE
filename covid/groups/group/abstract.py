from abc import abstractmethod, ABC


class AbstractGroup(ABC):
    @property
    @abstractmethod
    def people(self):
        pass

    @property
    @abstractmethod
    def susceptible(self):
        pass

    @property
    @abstractmethod
    def infected(self):
        pass

    @property
    @abstractmethod
    def recovered(self):
        pass

    @property
    @abstractmethod
    def in_hospital(self):
        pass

    @property
    @abstractmethod
    def dead(self):
        pass

    @property
    def size(self):
        return len(self.people)

    @property
    def size_susceptible(self):
        return len(self.susceptible)

    @property
    def size_infected(self):
        return len(self.infected)

    @property
    def size_recovered(self):
        return len(self.recovered)
