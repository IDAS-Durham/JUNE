import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
import os


class Inputs:
    """
    Reads in data used to populate the simulation
    """

    def __init__(
        self,
        zone="NorthEast",
        DATA_DIR: str = os.path.join("..", "data", "census_data"),
    ):
        self.zone = zone
        self.DATA_DIR = DATA_DIR
        self.OUTPUT_AREA_DIR = os.path.join(self.DATA_DIR, "output_area", zone)
        self.MIDDLE_OUTPUT_AREA_DIR = os.path.join(self.DATA_DIR, "middle_output_area", zone)
        oa2msoa_df = self.oa2msoa()
        
        # Read census data on high resolution map (OA)
        population_df = self.read_population_df()
        # n_households_df = self.read_household_df()
        ages_df = self.read_ages_df()
        comp_people_df = self.read_household_composition_people(ages_df)
        households_df = self.people_compositions2households(comp_people_df)

        self.household_dict = {
            "n_residents": population_df["n_residents"],
            # "n_households": n_households_df["n_households"],
            "age_freq": ages_df,
            "sex_freq": population_df[["males", "females"]],
            "household_composition_freq": households_df,
        }
        self.school_df = self.read_school_census()
        #self.company_df = self.read_companyize_census()
        # Read census data on low resolution map (MSOA)
        self.oa2msoa_df = self.oa2msoa()
        self.workflow_dict = self.create_workflow_dict()
        self.companysize_df = self.read_companysize_census()
        self.companysector_df = self.read_companysector_census()
        self.companysector_by_sex_df = self.read_companysector_by_sex_census()
   

    def read_df(
        self,
        DATA_DIR: str,
        filename: str,
        column_names: list,
        usecols: list,
        index: str,
    ) -> pd.DataFrame:
        """Read dataframe and format

        Args:
            DATA_DIR: path to dataset folder (default should be output_area folder) 
            filename:
            column_names: names of columns for output dataframe 
            usecols: ids of columns to read
            index: index of output dataframe

        Returns:
            df: formatted df

        """

        #df = pd.read_csv(os.path.join(DATA_DIR, filename), header=0,)
        df = pd.read_csv(
            os.path.join(DATA_DIR, filename),
            names=column_names,
            usecols=usecols,
            header=0,
        )
        df.set_index(index, inplace=True)
        return df

    def oa2msoa(self):
        """
        Creat link between OA and MSOA layers.
        """
        usecols = [0, 1]
        column_names = ["OA11CD", "MSOA11CD"]
        oa2msoa_df = self.read_df(
            os.path.join(self.DATA_DIR, "area_code_translations"),
            "oa_msoa_englandwales_2011.csv",
            column_names, usecols, "OA11CD"
        )

        return oa2msoa_df

    def read_household_composition_people(self, ages_df):
        """
        TableID: QS112EW
        https://www.nomisweb.co.uk/census/2011/qs112ew

        """
        household_people = "household_composition_people.csv"
        usecols = [
            2,
            6,
            7,
            9,
            11,
            12,
            13,
            14,
            16,
            17,
            18,
            19,
            21,
            22,
            23,
            24,
            26,
            27,
            28,
            30,
            31,
            32,
            33,
            34,
        ]
        column_names = [
            "output_area",
            "Person_old",
            "Person",
            "Old_Family",
            "Family_0k",
            "Family_1k",
            "Family_2k",
            "Family_adult_children",
            "SS_Family_0k",
            "SS_Family_1k",
            "SS_Family_2k",
            "SS_Family_adult_children",
            "Couple_Family_0k",
            "Couple_Family_1k",
            "Couple_Family_2k",
            "Couple_Family_adult_children",
            "Lone_1k",
            "Lone_2k",
            "Lone_adult_children",
            "Other_1k",
            "Other_2k",
            "Students",
            "Old_Unclassified",
            "Other",
        ]
        OLD_THRESHOLD = 12
        comp_people_df = self.read_df(
            self.OUTPUT_AREA_DIR, household_people, column_names, usecols, "output_area"
        )

        # Combine equivalent fields
        comp_people_df["Family_0k"] += (
            comp_people_df["SS_Family_0k"] + comp_people_df["Couple_Family_0k"]
        )
        comp_people_df["Family_1k"] += (
            comp_people_df["SS_Family_1k"]
            + comp_people_df["Couple_Family_1k"]
            + comp_people_df["Other_1k"]
        )
        comp_people_df["Family_2k"] += (
            comp_people_df["SS_Family_2k"]
            + comp_people_df["Couple_Family_2k"]
            + comp_people_df["Other_2k"]
        )
        comp_people_df["Family_adult_children"] += (
            comp_people_df["SS_Family_adult_children"]
            + comp_people_df["Couple_Family_adult_children"]
        )

        # Since other contains some old, give it some probability when there are old people in the area
        areas_with_old = ages_df[ages_df.columns[OLD_THRESHOLD:]].sum(axis=1) > 0
        areas_no_house_old = (
            comp_people_df["Person_old"]
            + comp_people_df["Old_Family"]
            + comp_people_df["Old_Unclassified"]
            == 0
        )

        comp_people_df["Family_0k"].loc[
            ~((areas_no_house_old) & (areas_with_old))
        ] += comp_people_df["Other"].loc[~((areas_no_house_old) & (areas_with_old))]

        comp_people_df["Old_Family"].loc[(areas_no_house_old) & (areas_with_old)] += (
            comp_people_df["Other"].loc[(areas_no_house_old) & (areas_with_old)]
            + 0.4
            * comp_people_df["Other_1k"].loc[(areas_no_house_old) & (areas_with_old)]
        )

        comp_people_df = comp_people_df.drop(
            columns=[
                c
                for c in comp_people_df.columns
                if "SS" in c or "Couple" in c or "Other" in c
            ]
        )

        return comp_people_df

    def read_population_df(self, freq: bool = True) -> pd.DataFrame:
        """Read population dataset downloaded from https://www.nomisweb.co.uk/census/2011/ks101ew        

        Args:

        Returns:
            pandas dataframe with ratio of males and females per output area 

        """
        # TODO: column names need to be more general for other datasets.
        population = "usual_resident_population.csv"
        population_column_names = [
            "output_area",
            "n_residents",
            "males",
            "females",
        ]
        # population_usecols = [2, 5, 6, 7]
        population_usecols = [
            "geography code",
            "Variable: All usual residents; measures: Value",
            "Variable: Males; measures: Value",
            "Variable: Females; measures: Value",
        ]
        population_df = pd.read_csv(
            os.path.join(self.OUTPUT_AREA_DIR, population), usecols=population_usecols,
        )
        names_dict = dict(zip(population_usecols, population_column_names))
        population_df.rename(columns=names_dict, inplace=True)
        population_df.set_index("output_area", inplace=True)

        # population_df = self.read_df(
        #    self.OUTPUT_AREA_DIR,
        #    population,
        #    population_column_names,
        #    population_usecols,
        #    "output_area",
        # )
        try:
            pd.testing.assert_series_equal(
                population_df["n_residents"],
                population_df["males"] + population_df["females"],
                check_names=False,
            )
        except AssertionError:
            print("males: ", len(population_df["males"]))
            print("females: ", len(population_df["females"]))
            raise AssertionError
        if freq:
            # Convert to ratios
            population_df["males"] /= population_df["n_residents"]
            population_df["females"] /= population_df["n_residents"]
        return population_df

    def read_household_df(self, freq: bool = True) -> pd.DataFrame:
        """Read household dataset downloaded from https://www.nomisweb.co.uk/census/2011/ks105ew

        Args:

        Returns:
            pandas dataframe with number of households per output area 

        """

        households = "household_composition.csv"
        households_names = [
            "output_area",
            "n_households",
        ]
        households_usecols = [2, 4]

        households_df = self.read_df(
            self.OUTPUT_AREA_DIR,
            households,
            households_names,
            households_usecols,
            "output_area",
        )

        return households_df

    def read_ages_df(self, freq: bool = True) -> pd.DataFrame:
        """Read ages dataset downloaded from https://www.nomisweb.co.uk/census/2011/ks102ew

        Args:

        Returns:
            pandas dataframe with age profiles per output area 

        """
        ages = "age_structure.csv"
        ages_names = [
            "output_area",
            "0-4",
            "5-7",
            "8-9",
            "10-14",
            "15",
            "16-17",
            "18-19",
            "20-24",
            "25-29",
            "30-44",
            "45-59",
            "60-64",
            "65-74",
            "75-84",
            "85-89",
            "90-XXX",
        ]

        ages_usecols = [2,] + list(range(5, 21))

        ages_df = self.read_df(
            self.OUTPUT_AREA_DIR, ages, ages_names, ages_usecols, "output_area"
        )
        if freq:
            ages_df = ages_df.div(ages_df.sum(axis=1), axis=0)
        return ages_df

    def people_compositions2households(self, comp_people_df, freq=True):

        households_df = pd.DataFrame()

        # SINGLES
        households_df["0 0 0 1"] = comp_people_df["Person_old"]
        households_df["0 0 1 0"] = comp_people_df["Person"]

        # COUPLES NO KIDS
        households_df["0 0 0 2"] = comp_people_df["Old_Family"] // 2
        households_df["0 0 2 0"] = comp_people_df["Family_0k"] // 2

        # COUPLES 1 DEPENDENT KID
        households_df["1 0 2 0"] = (
            comp_people_df["Family_1k"] // 3 - comp_people_df["Family_1k"] % 3
        ).apply(lambda x: max(x, 0))
        # i) Assumption: there can be only one independent child, and is a young adult
        households_df["1 1 2 0"] = comp_people_df["Family_1k"] % 3

        # COUPLES >2 DEPENDENT KIDS
        households_df["2 0 2 0"] = (
            comp_people_df["Family_2k"] // 4 - comp_people_df["Family_2k"] % 4
        ).apply(lambda x: max(x, 0))
        # ii) Assumption: the maximum number of children is 3, it could be a young adult or a kid
        households_df["3 0 2 0"] = 0.5 * (comp_people_df["Family_2k"] % 4)
        households_df["2 1 2 0"] = 0.5 * (comp_people_df["Family_2k"] % 4)

        # COUPLES WITH ONLY INDEPENDENT CHILDREN
        # iii) Assumption: either one or two children (no more than two)
        households_df["0 1 2 0"] = (
            comp_people_df["Family_adult_children"] // 3
            - comp_people_df["Family_adult_children"] % 3
        ).apply(lambda x: max(x, 0))
        households_df["0 2 2 0"] = comp_people_df["Family_adult_children"] % 3

        # LONE PARENTS 1 DEPENDENT KID
        households_df["1 0 1 0"] = (
            comp_people_df["Lone_1k"] // 2 - comp_people_df["Lone_1k"] % 2
        ).apply(lambda x: max(x, 0))
        # i) Assumption: there can be only one independent child, and is a young adult
        households_df["1 1 1 0"] = comp_people_df["Lone_1k"] % 2

        households_df["2 0 1 0"] = (
            comp_people_df["Lone_2k"] // 3 - comp_people_df["Lone_2k"] % 3
        ).apply(lambda x: max(x, 0))
        # ii) Assumption: the maximum number of children is 3, it could be a young adult or a kid
        households_df["3 0 1 0"] = 0.5 * (comp_people_df["Lone_2k"] % 3)
        households_df["2 1 1 0"] = 0.5 * (comp_people_df["Lone_2k"] % 3)

        # STUDENTS
        # iv) Students live in houses of 3 or 4
        households_df[f"0 3 0 0"] = (
            comp_people_df["Students"] // 3 - comp_people_df["Students"] % 3
        ).apply(lambda x: max(x, 0))

        households_df[f"0 4 0 0"] = comp_people_df["Students"] % 3

        # OLD OTHER
        # v) old other live in houses of 2 or 3
        households_df[f"0 0 0 2"] += (
            comp_people_df["Old_Unclassified"] // 2
            - comp_people_df["Old_Unclassified"] % 2
        ).apply(lambda x: max(x, 0))
        households_df[f"0 0 0 3"] = comp_people_df["Old_Unclassified"] % 2

        if freq:
            return households_df.div(households_df.sum(axis=1), axis=0)
        else:
            return households_df

    def read_school_census(self):
        """
        Reads school location and sizes, it initializes a KD tree on a sphere,
        to query the closest schools to a given location.
        """
        school_filename = os.path.join(
            self.DATA_DIR, "school_data", "uk_schools_data.csv"
        )
        school_df = pd.read_csv(school_filename, index_col=0)
        school_df.dropna(inplace=True)
        school_df["age_min"].replace(to_replace=np.arange(0, 4), value=4, inplace=True)

        school_df["age_max"].replace(
            to_replace=np.arange(20, 50), value=19, inplace=True
        )

        assert school_df["age_min"].min() <= 4
        assert school_df["age_max"].max() < 20
        return school_df


    def read_companysize_census(self):
        """
        Gives nr. of companies with nr. of employees per MSOA
        (NOMIS: UK Business Counts - local units by industry and employment size band)
        """
        usecols = [1, 3, 4, 5, 6, 7, 8, 9, 10]
        column_names = [
            "MSOA11CD",
            "0-9",
            "10-19",
            "20-49",
            "50-99",
            "100-249",
            "250-499",
            "500-999",
            "1000-xxx",
        ]
        companysize_df = self.read_df(
            self.MIDDLE_OUTPUT_AREA_DIR, "business_counts_northeast_2019.csv",
            column_names, usecols, "MSOA11CD"
        )

        assert companysize_df.isnull().values.any() == False

        return companysize_df

    def read_companysector_census(self):
        """
        Gives number of companies by type according to NOMIS sector data at the MSOA level
        TableID: WD601EW
        https://www.nomisweb.co.uk/census/2011/wd601ew
        """

        companysector_df = pd.read_csv(
            self.MIDDLE_OUTPUT_AREA_DIR + '/company_sector_cleaned_msoa.csv',
            index_col=0,
        )
        
        return companysector_df

    def read_companysector_by_sex_census(self):
        """
        Gives number dict of discrete probability distributions by sex of the different industry sectors at the OA level
        The dict is of the format: {[oa]: {[gender('m'/'f')]: [distribution]}}
        
        TableID: KS605EW to KS607EW
        https://www.nomisweb.co.uk/census/2011/ks605ew
        """

        industry_by_sex_df = pd.read_csv(self.OUTPUT_AREA_DIR + '/industry_by_sex_cleaned.csv')

        # define all columns in csv file relateing to males
        # here each letter corresponds to the industry sector (see metadata)
        m_columns = ['m A', 'm B', 'm C', 'm D', 'm E', 'm F', 'm G', 'm H', 'm I', 'm J',
                     'm K', 'm L', 'm M', 'm N', 'm O', 'm P', 'm Q', 'm R', 'm S', 'm T', 'm U']

        m_distributions = []
        for oa in range(len(industry_by_sex_df['oareas'])):
            total = int(industry_by_sex_df['m all'][oa])
            
            distribution = []
            for column in m_columns:
                distribution.append(int(industry_by_sex_df[column][oa])/total)
                
            m_distributions.append(distribution)

        # define all columns in csv file relateing to males
        f_columns = ['f A', 'f B', 'f C', 'f D', 'f E', 'f F', 'f G', 'f H', 'f I', 'f J',
                             'f K', 'f L', 'f M', 'f N', 'f O', 'f P', 'f Q', 'f R', 'f S', 'f T', 'f U']
                
        f_distributions = []
        for oa in range(len(industry_by_sex_df['oareas'])):
            total = int(industry_by_sex_df['f all'][oa])
            
            distribution = []
            for column in f_columns:
                distribution.append(int(industry_by_sex_df[column][oa])/total)

            f_distributions.append(distribution)
    
        industry_by_sex_dict = {}
        for idx, oa in enumerate(industry_by_sex_df['oareas']):
            industry_by_sex_dict[oa] = {'m': m_distributions[idx], 'f': f_distributions[idx]}

        return industry_by_sex_dict
    
    def read_commute_method(DATA_DIR: str, freq: bool = True) -> pd.DataFrame:
        """
        The dataframe derives from:
        TableID: QS701UK
        https://www.nomisweb.co.uk/census/2011/qs701ew

        Args:
        DATA_DIR: path to dataset folder (default should be output_area folder) 

        Returns:
        pandas dataframe with ratio of males and females per output area 

        """
        travel_df = pd.read_csv(
            DATA_DIR + "flow_method_oa_qs701northeast_2011.csv",
            delimiter=",",
            delim_whitespace=False,
        )
        travel_df = travel_df.rename(columns={"geography code": "residence"})
        travel_df = travel_df.set_index("residence")

        # re-group dataset
        travel_df["home"] = travel_df[
            [c for c in travel_df.columns if " home;" in c]
        ].sum(axis=1)
        travel_df = travel_df.drop(
            columns=[c for c in travel_df.columns if " home;" in c]
        )
        travel_df["public"] = travel_df[
            [
                c
                for c in travel_df.columns
                if "metro" in c or "Train" in c or "coach" in c
            ]
        ].sum(axis=1)
        travel_df = travel_df.drop(
            columns=[
                c
                for c in travel_df.columns
                if "metro" in c or "Train" in c or "coach" in c
            ]
        )
        travel_df["private"] = travel_df[
            [
                c
                for c in travel_df.columns
                if "Taxi" in c
                or "scooter" in c
                or "car" in c
                or "Bicycle" in c
                or "foot" in c
            ]
        ].sum(axis=1)
        travel_df = travel_df.drop(
            columns=[
                c
                for c in travel_df.columns
                if "Taxi" in c
                or "scooter" in c
                or "car" in c
                or "Bicycle" in c
                or "foot" in c
            ]
        )
        travel_df = travel_df[["home", "public", "private"]]

        # create dictionary to merge OA into MSOA
        oa2msoa_df = self.oa2msoa()

        # merge OA into MSOA
        travel_df = travel_df.merge(
            msoa2oa_df,
            left_index=True,
            right_index=True,
        )
        travel_df = travel_df.groupby(["MSOA11CD"]).sum()

        if freq:
            # Convert to ratios
            travel_df["home"] /= travel_df.sum(axis=1)
            travel_df["public"] /= travel_df.sum(axis=1)
            travel_df["private"] /= travel_df.sum(axis=1)
        return travel_df
    
    def create_workflow_dict(
        self,
        DATA_DIR: str = os.path.join("..", "data", "census_data", "flow/",)
    ) -> dict:
        """
        Workout where people go to work.
        The MSOA area code is used for homes (rows) and work (columns).
        The dataframe from NOMIS:
            TableID: WU01EW
            https://wicid.ukdataservice.ac.uk/cider/wicid/downloads.php
        , but is processed to be placed in a pandas.DataFrame.

        Args:
            DATA_DIR: path to dataset (csv file)

        Returns:
            dictionary with frequencies of populations 
        """
        flow_female_file = "flow_female_in_msoa_wu01northeast_2011.csv"
        flow_male_file = "flow_male_in_msoa_wu01northeast_2011.csv"
        flow_dirname = os.path.join(
            self.DATA_DIR, "middle_output_area", self.zone
        )

        flow_female_df = pd.read_csv(os.path.join(flow_dirname, flow_female_file))
        flow_female_df = flow_female_df.set_index("residence")

        flow_male_df = pd.read_csv(os.path.join(flow_dirname, flow_male_file))
        flow_male_df = flow_male_df.set_index("residence")
        
        home_msoa = (
            flow_female_df.index.values
        )  # the same for female & male
        female_work_msoa_list = []
        female_work_msoa_dist_list = []
        male_work_msoa_list = []
        male_work_msoa_dist_list = []
        for hmsoa in home_msoa:
            # Where do woman go to work in ratios
            female_work_msoa = flow_female_df.loc[hmsoa].dropna()[flow_female_df.loc[hmsoa] != 0.0]
            female_work_msoa_list.append(female_work_msoa.index.values)
            female_work_msoa_dist_list.append(
                female_work_msoa.values / female_work_msoa.values.sum()
            )
            # Where do man go to work in ratios
            male_work_msoa = flow_male_df.loc[hmsoa].dropna()[flow_male_df.loc[hmsoa] != 0.0]
            male_work_msoa_list.append(male_work_msoa.index.values)
            male_work_msoa_dist_list.append(
                male_work_msoa.values / male_work_msoa.values.sum()
            )

        workflow_dict = {
            "home_msoa": home_msoa,
            "female_work_msoa": female_work_msoa_list,
            "female_work_dist": female_work_msoa_dist_list,
            "male_work_msoa": male_work_msoa_list,
            "male_work_dist": male_work_msoa_dist_list,
        }

        return workflow_dict


if __name__ == "__main__":

    ip = Inputs()
    print(ip.companysize_df)
