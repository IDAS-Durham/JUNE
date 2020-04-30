from sklearn.neighbors import BallTree
from scipy import stats
from covid.groups import Group
import numpy as np


class SchoolError(BaseException):
    """Class for throwing school related errors."""

    pass


class School(Group):
    """
    """

    def __init__(
            self,
            school_id,
            coordinates,
            n_pupils,
            n_teachers_max,
            age_min,
            age_max
        ):
        super().__init__("School_%05d" % school_id, "school")
        self.id = school_id
        self.coordinates = coordinates  #[lon, lat]
        self.msoa = None
        # self.residents = group(self.id,"household")
        #TODO assumption on nr. of students per teachers
        self.n_teachers_max = n_teachers_max
        self.n_teachers = 0
        self.n_pupils_max = n_pupils
        self.n_pupils = 0
        self.age_min = age_min
        self.age_max = age_max
    

class Schools:
    def __init__(self, world, areas, school_df):
        self.world = world
        self.members = []
        self.stud_nr_per_teacher = self.world.config['schools']['student_nr_per_teacher']
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
        school_age = list(self.world.inputs.decoder_age.values())[
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
            n_teachers_max = int(row["NOR"] / self.stud_nr_per_teacher)
            school = School(
                i,
                np.array(row[["latitude", "longitude"]].values, dtype=np.float64),
                row["NOR"],
                n_teachers_max,
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


    def create_interaction_poisson_distributions(self, school_interaction_matrix):
        """
        Creates 6*5/2 = different 15 Poisson distributions, that model the
        probability of interaction between two different age groups in a school.
        """
        self.age_interaction_prob = np.empty(
            (6, 6), dtype=stats._discrete_distns.poisson_gen
        )
        for i in range(0, 6):
            for j in range(0, i):
                mu = interaction_matrix[i, j]
                poisson = stats.poisson(mu)
                self.age_interaction_prob[i, j] = poisson
                self.age_interaction_prob[j, i] = poisson

    def _linear_to_indices(self, xi):
        i = np.ceil(0.5 * (-3 + np.sqrt(9 + 8 * xi)))
        j = xi - i * i(+1) / 2
        return [i, j]

    def _indices_to_linear(self, i, j):
        xi = i * (i + 1) / 2 + j
        return xi

    def create_age_pairs_distribution(self, school_interaction_matrix):
        pairs_counts = []
        for i in range(0, 7):
            for j in range(0, i):
                pairs_counts.append(school_interaction_matrix[i, j])
        self.pairs_distribution = stats.rv_discrete(
            values=(np.arange(0, len(pairs_array)), pairs_array)
        )
