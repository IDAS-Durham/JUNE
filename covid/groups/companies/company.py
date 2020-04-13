class CompanyError(BaseException):
    """Class for throwing company related errors."""
    pass

class Company:
    """
    The Company class represents a company that contains information about 
    its workers (19 - 74 years old).
    """

    def __init__(self, company_id, msoa, n_employees):
        self.id = company_id
        self.people = []
        self.msoa = msoa
        self.n_employees_max = n_employees
        self.n_pupils = 0

class Companies:
    def __init__(self, world, msoareas, companysize_dict):
        self.world = world
        self.members = {}
        self.init_companies(companysize_dict)


    def init_companies(self, companysize_dict):
        """
        Initializes Companies.
        """
        COMPANY_AGE_THRESHOLD = [8, 13]
        companies = []
        copmany_age = list(self.world.decoder_age.values())[
            0] : COMPANY_AGE_THRESHOLD[1]
        ]
        copmany_trees = {}
        copmany_agegroup_to_global_indices = (
            {}
        )  # stores for each gender-ratio group the index to the school
        # create company neighbour trees
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


