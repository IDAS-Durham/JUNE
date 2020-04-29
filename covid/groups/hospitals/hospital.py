from sklearn.neighbors import BallTree
from covid.groups import Group
import numpy as np

class Hospital(Group):
    """
    The Hospital class represents a hospital and contains information about 
    its patients and workers - the latter being the usual "people".

    TODO: we have to figure out the inheritance structure; I think it will
    be an admixture of household and company.
    I will also assume that the patients cannot infect anybody - this may
    become a real problem as it is manifestly not correct.
    """

    def __init__(self, hospital_id=1, structure=None, area=None):
        Group.__init__(self, name = "Hospital_%03d"%hospital_id, spec = "hospital") 
        self.id          = hospital_id
        self.area        = area
        self.people      = []
        self.patients    = []
        self.ICUpatients = []
        """
        I foresee that we get information about beds/ICU beds etc.
        into the composition
        """
        self.structure = structure
        print ("I am Boris - this is my virtual hospital",self.id)


    @property
    def n_beds(self):
        if "n_beds" in self.structure:
            return self.structure["n_beds"]
        return 0

    @property
    def n_ICUbeds(self):
        if "n_ICUbeds" in self.structure:
            return self.structure["n_ICUbeds"]
        return 0

    @property
    def full(self):
        return len(self.patients)>=self.n_beds
    
    @property
    def full_ICU(self):
        return len(self.ICUpatients)>=self.n_ICUbeds
    
    def set_active_members(self):
        for person in self.people:
            if person.active_group is None:
                person.active_group = "hospital"

    def add_as_patient(self,person):
        if person.health_information.tag=="intensive care":
            self.ICUpatients.append(person)
        elif person.health_information.tag=="hospitalised":
            self.patients.append(person)
        person.in_hospital = self

    def release_as_patient(self,person):
        if person in self.patients:
            self.patients.remove(person)
        elif person in self.ICUpatients:
            self.ICUpatients.remove(person)
        person.in_hospital = None
            
    @property
    def size(self):
        return len(self.people)+len(self.patients)+len(self.ICUpatients)


    def update_status_lists_for_workers(self, time=1):
        dead = []
        self.susceptible.clear()
        self.infected.clear()
        self.recovered.clear()
        for person in self.people:
            person.health_information.update_health_status()
            if person.health_information.susceptible:
                self.susceptible.append(person)
            if person.health_information.infected:
                self.infected.append(person)
            elif person.health_information.recovered:
                self.recovered.append(person)
                if person in self.infected:
                    self.infected.remove(person)
            elif person.health_information.dead:
                person.bury()
                dead.append(person)
        for person in dead:
            self.people.remove(person)


    def update_status_lists_for_patients(self, time=1):
        dead = []
        for person in self.patients:
            person.health_information.update_health_status()
            if person.health_information.susceptible:
                print ("Error: in our current setup, only infected patients in the hospital")
                self.susceptible.append(person)
            if person.health_information.infected:
                if not(person.health_information.in_hospital):
                    print ("Error: wrong tag for infected patient in hospital")
                    self.patients.remove(person)
                if person.health_information.tag=="intensive care":
                    self.ICUpatients.append(person)
                    self.patients.remove(person)
            if person.health_information.recovered:
                self.release_as_patient(person)
            if person.health_information.dead:
                person.bury()
                dead.append(person)
        for person in dead:
            self.patients.remove(person)

    def update_status_lists_for_ICUpatients(self, time=1):
        dead = []
        for person in self.ICUpatients:
            person.health_information.update_health_status()
            if person.health_information.susceptible:
                print ("Error: in our current setup, only infected patients in the hospital")
                self.susceptible.append(person)
            if person.health_information.infected:
                if not(person.health_information.in_hospital):
                    print ("Error: wrong tag for infected patient in hospital")
                    self.ICUpatients.remove(person)
                if person.health_information.tag=="hospitalised":
                    self.patients.append(person)
                    self.ICUpatients.remove(person)
            if person.health_information.recovered:
                self.release_as_patient(person)
            if person.health_information.dead:
                person.bury()
                dead.append(person)
        for person in dead:
            self.ICUpatients.remove(person)
                        
    def update_status_lists(self, time=1):
        # three copies of what happens in group for the three lists of people
        # in the hospital
        self.update_status_lists_for_workers(time)
        self.update_status_lists_for_patients(time)
        self.update_status_lists_for_ICUpatients(time)        
        print ("=== update status list for hospital with ",self.size," people ===")
        print ("=== hospital currently has ",len(self.patients)," patients",
               "and ",len(self.ICUpatients)," ICU patients")
                    
class Hospitals:
    """
    Contains all hospitals for the given area, and information about them.
    """
    def __init__(self, world, box_mode=False):
        self.world    = world
        self.box_mode = box_mode
        self.members  = []
        #self.hospital_trees = self._create_hospital_tree(hospital_df)
        if self.box_mode:
            self.members.append(Hospital(1,{ "n_beds": 10,   "n_ICUbeds": 2}))
            self.members.append(Hospital(2,{ "n_beds": 5000, "n_ICUbeds": 5000}))

    def get_nearest(self,person):
        tagICU = person.health_information.tag=="intensive care"
        tag    = person.health_information.tag=="hospitalised"
        if self.box_mode:
            for hospital in self.members:
                if tag and not(hospital.full):
                    return hospital
                if tagICU and not(hospital.full_ICU):
                    return hospital
        print ("no hospital found for patient with",person.health_information.tag)
        return None

    
        

    #def _create_hospital_tree(self,hospital_df):
    #    hospital_tree = BallTree(
    #        np.deg2rad(hospital_df[["Latitude", "Longitude"]].values), metric="haversine"
    #        )
    #    return hospital_tree

    #def get_closest_hospital(self,area,k):
    #    hospital_tree = self.hospital_trees
    #    distances,neighbours = hospital_tree.query(
    #        np.deg2rad(area.coordinates.reshape(1,-1)),k = k,sort_results=True
    #        )
    #    return neighbours
