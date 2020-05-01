import numpy as np
from sklearn.neighbors._ball_tree import BallTree

from covid.groups import Group


class Hospital(Group):
    """
    The Hospital class represents a hospital and contains information about 
    its patients and workers - the latter being the usual "people".

    TODO: we have to figure out the inheritance structure; I think it will
    be an admixture of household and company.
    I will also assume that the patients cannot infect anybody - this may
    become a real problem as it is manifestly not correct.
    """

    def __init__(self, hospital_id=1, structure=None, postcode=None):
        super().__init__("Hospital_%03d" % hospital_id, "hospital")
        self.id = hospital_id
        self.postcode = postcode
        self.people = []
        self.patients = []
        self.ICUpatients = []
        """
        I foresee that we get information about beds/ICU beds etc.
        into the composition
        """
        self.structure = structure

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
        return len(self.patients) >= self.n_beds

    @property
    def full_ICU(self):
        return len(self.ICUpatients) >= self.n_ICUbeds

    def set_active_members(self):
        for person in self.people:
            if person.active_group is None:
                person.active_group = "hospital"

    def add_as_patient(self, person):
        if person.health_information.tag == "intensive care":
            self.ICUpatients.append(person)
        elif person.health_information.tag == "hospitalised":
            self.patients.append(person)
        person.in_hospital = self

    def release_as_patient(self, person):
        if person in self.patients:
            self.patients.remove(person)
        elif person in self.ICUpatients:
            self.ICUpatients.remove(person)
        person.in_hospital = None

    @property
    def size(self):
        return len(self.people) + len(self.patients) + len(self.ICUpatients)

    def update_status_lists_for_patients(self):
        dead = []
        for person in self.patients:
            person.health_information.update_health_status()
            if person.health_information.susceptible:
                print("Error: in our current setup, only infected patients in the hospital")
                self.susceptible.append(person)
            if person.health_information.infected:
                if not (person.health_information.in_hospital):
                    print("Error: wrong tag for infected patient in hospital")
                    self.patients.remove(person)
                if person.health_information.tag == "intensive care":
                    self.ICUpatients.append(person)
                    self.patients.remove(person)
            if person.health_information.recovered:
                self.release_as_patient(person)
            if person.health_information.dead:
                person.bury()
                dead.append(person)
        for person in dead:
            self.patients.remove(person)

    def update_status_lists_for_ICUpatients(self):
        dead = []
        for person in self.ICUpatients:
            person.health_information.update_health_status()
            if person.health_information.susceptible:
                print("Error: in our current setup, only infected patients in the hospital")
                self.susceptible.append(person)
            if person.health_information.infected:
                if not (person.health_information.in_hospital):
                    print("Error: wrong tag for infected patient in hospital")
                    self.ICUpatients.remove(person)
                if person.health_information.tag == "hospitalised":
                    self.patients.append(person)
                    self.ICUpatients.remove(person)
            if person.health_information.recovered:
                self.release_as_patient(person)
            if person.health_information.dead:
                person.bury()
                dead.append(person)
        for person in dead:
            self.ICUpatients.remove(person)

    def update_status_lists(self):
        # three copies of what happens in group for the three lists of people
        # in the hospital
        super().update_status_lists()
        self.update_status_lists_for_patients()
        self.update_status_lists_for_ICUpatients()
        print("=== update status list for hospital with ", self.size, " people ===")
        print("=== hospital currently has ", len(self.patients), " patients",
              "and ", len(self.ICUpatients), " ICU patients")


class Hospitals:
    """
    Contains all hospitals for the given area, and information about them.
    """

    def __init__(self, world, hospital_df=None, box_mode=False):
        self.world = world
        self.box_mode = box_mode
        self.members = []
        # translate identifier from csv to position in members
        self.finder = {}
        # maximal distance of patient to receiving hospital - parameter needs to be fixed/adjusted
        self.max_distance = 100.
        # number of ICU beds per hospital from simple fraction, numbers
        # taken from https://www.kingsfund.org.uk/publications/nhs-hospital-bed-numbers
        self.icu_fraction = 5900. / 141000.
        if not self.box_mode:
            print("Init hospitals from data file")
            self.hospital_trees = self.create_hospital_trees(hospital_df)
        else:
            self.members.append(Hospital(1, {"n_beds": 10, "n_ICUbeds": 2}))
            self.members.append(Hospital(2, {"n_beds": 5000, "n_ICUbeds": 5000}))

    def create_hospital_trees(self, hospital_df):
        hospital_tree = BallTree(
            np.deg2rad(hospital_df[["Latitude", "Longitude"]].values), metric="haversine"
        )
        for row in range(hospital_df.shape[0]):
            n_beds = hospital_df.iloc[row]["beds"]
            n_icu_beds = round(self.icu_fraction * n_beds)
            n_beds -= n_icu_beds
            self.members.append(Hospital(hospital_df.iloc[row]["Unnamed: 0"],
                                         {"n_beds": int(n_beds), "n_ICUbeds": int(n_icu_beds)},
                                         hospital_df.iloc[row]["Postcode"]))
            self.finder[hospital_df.iloc[row]["Unnamed: 0"]] = len(self.members) - 1
            # print ("--- Hospital[",hospital_df.iloc[row]["Unnamed: 0"],
            #       "<-->",len(self.members)-1,"]: ",
            #       n_beds," beds and ",n_ICUbeds," n_ICUbeds.")
        return hospital_tree

    def get_nearest(self, person):
        tagICU = person.health_information.tag == "intensive care"
        tag = person.health_information.tag == "hospitalised"
        if self.box_mode:
            for hospital in self.members:
                if tag and not (hospital.full):
                    return hospital
                if tagICU and not (hospital.full_ICU):
                    return hospital
        else:
            winner = None
            windist = 1.e12
            angles, hospitals = self.get_closest_hospital(person.area, 100)
            for angle, hospitaltag in zip(angles[0], hospitals[0]):
                hospital = self.members[self.finder[hospitaltag]]
                distance = angle * 6371.
                if distance > self.max_distance:
                    break
                if ((tag and not (hospital.full)) or
                        (tagICU and not (hospital.full_ICU))):
                    winner = hospital
                    windist = distance
                    break
            if winner != None:
                print("Receiving hospital for patient with ", person.health_information.tag, ": ",
                      winner.structure, " distance = ", windist, " km at ", winner.postcode)
                return winner
        print("no hospital found for patient with", person.health_information.tag,
              "in distance < ", self.maxdistance, " km.")
        return None

    def get_closest_hospital(self, area, k):
        hospital_tree = self.hospital_trees
        return hospital_tree.query(
            np.deg2rad(area.coordinates.reshape(1, -1)), k=k, sort_results=True
        )
