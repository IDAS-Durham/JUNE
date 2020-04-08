from sklearn.neighbors import BallTree
from covid.groups import Group
import numpy as np

class SchoolError(BaseException):
    """Class for throwing school related errors."""
    pass

class School(Group):
    """
    The School class represents a household and contains information about 
    its pupils (6 - 14 years old).
    """

    def __init__(self, school_id, coordinates, n_pupils, age_min, age_max):
        super().__init__("School_%05d"%school_id, "School")
        self.id = school_id
        self.people = []
        self.coordinates = coordinates
        #self.residents = group(self.id,"household")
        self.n_pupils_max = n_pupils
        self.n_pupils = 0
        self.age_min = age_min
        self.age_max = age_max

class Schools:

    def __init__(self, world, areas, school_df):
        self.world = world
        self.members = {}
        self.init_schools(school_df)

    def _compute_age_group_mean(self, agegroup):
        """
        Given a NOMIS age group, calculates the mean age.
        """
        try:
            age_1, age_2 = agegroup.split("-")
            if age_2 == "XXX":
                agemean = 90
            else:
                age_1 = float(age_1)
                age_2 = float(age_2)
                agemean = (age_2 + age_1) / 2.0
        except:
            agemean = int(agegroup)
        return agemean

    def init_schools(self, school_df):
        """
        Initializes schools.
        """
        SCHOOL_AGE_THRESHOLD = [1, 7]
        schools = []
        school_age = list(self.world.decoder_age.values())[
            SCHOOL_AGE_THRESHOLD[0] : SCHOOL_AGE_THRESHOLD[1]
        ]
        school_trees = {}
        school_agegroup_to_global_indices = (
            {}
        )  # stores for each age group the index to the school
        # create school neighbour trees
        for agegroup in school_age:
            school_agegroup_to_global_indices[
                agegroup
            ] = {}  # this will be used to track school universally
            mean = self._compute_age_group_mean(agegroup)
            _school_df_agegroup = school_df[
                (school_df["age_min"] <= mean) & (school_df["age_max"] >= mean)
            ]
            school_trees[agegroup] = self._create_school_tree(_school_df_agegroup)
        # create schools and put them in the right age group
        for i, (index, row) in enumerate(school_df.iterrows()):
            school = School(
                i,
                np.array(row[["latitude", "longitude"]].values, dtype=np.float64),
                row["NOR"],
                row["age_min"],
                row["age_max"],
            )
            # to which age group does this school belong to?
            for agegroup in school_age:
                agemean = self._compute_age_group_mean(agegroup)
                if school.age_min <= agemean and school.age_max >= agemean:
                    school_agegroup_to_global_indices[agegroup][
                        len(school_agegroup_to_global_indices[agegroup])
                    ] = i
            schools.append(school)
        # store variables to class
        self.members = schools
        self.school_trees = school_trees
        self.school_agegroup_to_global_indices = school_agegroup_to_global_indices
        return None

    def get_closest_schools(self, age, area, k):
        """
        Returns the k schools closest to the output area centroid.
        """
        school_tree = self.school_trees[age]
        distances, neighbours = school_tree.query(
            np.deg2rad(area.coordinates.reshape(1, -1)), k=k, sort_results=True,
        )
        return neighbours[0]

    def _create_school_tree(self, school_df):
        """
        Reads school location and sizes, it initializes a KD tree on a sphere,
        to query the closest schools to a given location.
        """
        school_tree = BallTree(
            np.deg2rad(school_df[["latitude", "longitude"]].values), metric="haversine"
        )
        return school_tree

    def set_active_members(self):
        for school in self.members:
            for person in school.people:
                if person.active_group != None:
                    raise SchoolError("Trying to set an already active person")
                else:
                    person.active_group = "school"
