#import os
#from june import paths
#
#import numpy as np
#import pandas as pd
#
#
#class Inputs:
#    """
#    Reads in data used to populate the simulation
#    """
#
#    def __init__(
#        self,
#        zone="NorthEast",
#        DATA_DIR: str = os.path.join(
#            os.path.dirname(os.path.realpath(__file__)),
#            "..",
#            "data",
#            "processed",
#            "census_data",
#        ),
#    ):
#        self.zone = zone
#        self.DATA_DIR = DATA_DIR
#        self.OUTPUT_AREA_DIR = os.path.join(self.DATA_DIR, "output_area", zone)
#            
#        # For the new structure -----------------------------------------------
#
#        # set up main directory paths ------
#        company_data_path = (
#            Path(__file__).parent.parent / \
#            "data/processed/census_data/company_data/" \
#        )
#        # ----------------------------------
#        #self.area_mapping_file = os.path.join(
#        #    os.path.dirname(os.path.realpath(__file__)),
#        #    "../data/census_data/area_code_translations/areas_mapping.csv",
#        #)
#        self.n_residents_file = os.path.join(
#            self.OUTPUT_AREA_DIR, "residents.csv"
#        )
#        self.age_freq_file = os.path.join(
#            self.OUTPUT_AREA_DIR, "age_structure.csv"
#        )
#        self.sex_freq_file = os.path.join(self.OUTPUT_AREA_DIR, "sex.csv")
#        self.household_composition_freq_file = os.path.join(
#            self.OUTPUT_AREA_DIR, "household_composition.csv",
#        )
#        self.commute_generator_path = (
#            Path(__file__).parent.parent / "data/census_data/commute.csv"
#        )
#        self.workflow_file = (
#            Path(__file__).parent.parent / \
#            "data/processed/flow_in_msoa_wu01ew_2011.csv"
#        )
#        self.companysize_file = company_data_path / "companysize_msoa11cd_2019.csv"
#        self.company_per_sector_per_msoa_file = company_data_path / "companysector_msoa11cd_2011.csv"
#        self.sex_per_sector_per_msoa_file = company_data_path / "companysector_by_sex_cleaned.csv"
#        self.companysector_education_file = company_data_path / "education_by_sex_2011.csv"
#        self.companysector_healthcare_file = company_data_path / "healthcare_by_sex_2011.csv"
#        self.school_data_path = (
#            Path(__file__).parent.parent / \
#            "data/processed/school_data/england_schools_data.csv"
#        )
#        self.school_config_path = (
#            Path(__file__).parent.parent / \
#            "configs/defaults/groups/schools.yaml"
#        )
#        self.school_distr_config_path = (
#            Path(__file__).parent.parent / \
#            "configs/defaults/distributors/school_distributor.yaml"
#        )
#        self.hospital_data_path = (
#            Path(__file__).parent.parent / \
#            "data/processed/hospital_data/england_hospitals.csv"
#        )
#        self.hospital_config_path = (
#            Path(__file__).parent.parent / \
#            "configs/defaults/groups/hospitals.yaml"
#        )
#        # For the old structure (will be removed soon) ------------------------
#        self.n_residents = pd.read_csv(
#            os.path.join(self.OUTPUT_AREA_DIR, "residents.csv"),
#            names=["output_area", "n_residents"],
#            header=0,
#            index_col="output_area",
#        )
#        self.area_mapping_df = self.read_area_mapping()
#       
#        self.pubs_df = pd.read_csv(
#            os.path.join(
#                os.path.dirname(os.path.realpath(__file__)),
#                "..",
#                "data",
#                "geographical_data",
#                "pubs_uk24727_latlong.txt"),
#            sep=" ",
#            header=None
#        )
#        self.pubs_df.columns = ["Latitude","Longitude"]
#        pub_ids = np.arange(len(self.pubs_df["Latitude"]))
#        self.pubs_df["Ids"] = pub_ids
#        
#        
#        self.areas_coordinates_df = self.read_coordinates()
#        self.contact_matrix = np.genfromtxt(
#            os.path.join(
#                self.DATA_DIR,
#                "..",
#                "social_mixing",
#                "POLYMOD",
#                "extended_polymod_UK.csv",
#            ),
#            delimiter=",",
#        )
#
#        # Read census data on low resolution map (MSOA)
#        self.workflow_df = self.create_workflow_df(
#            self.area_mapping_df,
#            self.n_residents.index.values,
#        )
#        self.companysize_df = self.read_companysize_census(
#            self.area_mapping_df,
#            self.n_residents.index.values,
#        )
#        self.companysector_df = self.read_companysector_census(
#            self.area_mapping_df,
#            self.n_residents.index.values,
#        )
#        self.compsec_by_sex_df = self.read_compsec_by_sex(self.n_residents.index.values)
#            
#        self.household_composition_df = pd.read_csv(
#                os.path.join(
#                    self.OUTPUT_AREA_DIR,
#                    'minimum_household_composition.csv',
#                ),
#                index_col="output_area"
#        )
#        self.n_students = pd.read_csv(
#            os.path.join(
#                self.OUTPUT_AREA_DIR,
#                'n_students.csv'
#            ),
#            index_col=0
#        )
#
#        self.carehomes_df = pd.read_csv(
#               os.path.join(
#                   self.OUTPUT_AREA_DIR,
#                   'carehomes.csv'
#               ),
#               skiprows=1,
#               names=['output_area', 'N_carehome_residents'],
#               index_col=0
#               )
#
#        self.n_in_communal = pd.read_csv(
#                os.path.join(
#                    self.OUTPUT_AREA_DIR,
#                    'n_people_in_communal.csv'
#                ),
#                index_col=0
#                )
# 
#        AGE_DIFF_DIR =  os.path.join(
#            os.path.dirname(os.path.realpath(__file__)),
#            "..",
#            "data",
#            "processed",
#            "age_difference",
#            )
#
#        self.husband_wife_df = pd.read_csv(
#                os.path.join(
#                    AGE_DIFF_DIR,
#                    'husband_wife.csv'
#                ),
#                index_col=0
#                )
#        self.parent_child_df = pd.read_csv(
#                os.path.join(
#                    AGE_DIFF_DIR,
#                    'parent_child.csv'
#                ),
#                index_col=0
#                )
#
#        self.read_non_london_stat_pcs()
#        self.read_london_stat_pcs()
#        self.read_uk_pcs_coordinates()
#        self.read_msoa_coordinates()
#        self.read_msoa_oa_coordinates()
#        
#
#
#    def read(self, filename):
#        df = pd.read_csv(
#            os.path.join(self.OUTPUT_AREA_DIR, filename), index_col="output_area"
#        )
#        freq = df.div(df.sum(axis=1), axis=0)
#        decoder = {i: df.columns[i] for i in range(df.shape[-1])}
#        return freq, decoder
#
#    def read_text_coordinates(self,filename):
#        pass
#        
#    def read_coordinates(self):
#        areas_coordinates_df_path = os.path.join(
#            os.path.dirname(os.path.realpath(__file__)),
#            "..",
#            "data",
#            "processed",
#            "geographical_data",
#            "oa_coordinates.csv",
#        )
#        areas_coordinates_df = pd.read_csv(areas_coordinates_df_path)
#        areas_coordinates_df.set_index("oa", inplace=True)
#        return areas_coordinates_df
#
#    def read_hospitals(self, area_mapping, oa_in_world):
#        """
#        Read in hospital data and filter those within
#        the population region.
#        """
#        hospital_df = pd.read_csv(
#            os.path.join(
#                os.path.dirname(os.path.realpath(__file__)),
#                "..",
#                "data",
#                "census_data",
#                "hospital_data",
#                "england_hospitals.csv",
#            )
#        )
#        hospital_df = hospital_df.rename(columns={'Postcode': "PCD"})
#        hospital_df = pd.merge(hospital_df, area_mapping, how='inner', on=['PCD'])
#        pcd_in_world = np.unique(area_mapping[
#            area_mapping["OA"].isin(list(oa_in_world))
#        ]["PCD"].values)
#        self.hospital_df = hospital_df.loc[
#            hospital_df["PCD"].isin(list(pcd_in_world))
#        ]
#
#    def read_area_mapping(self):
#        """
#        Creat link between Postcode and OA layers.
#        Needed to know in which OAs which hospitals are.
#        and
#        Creat link between OA and MSOA layers.
#        Needed due work-flow data, to know where people work.
#        """
#        usecols = [0, 1, 3]
#        column_names = ["PCD", "OA", "MSOA"]
#        area_mapping_df = pd.read_csv(
#            os.path.join(
#                os.path.dirname(os.path.realpath(__file__)),
#                "..",
#                "data",
#                "census_data",
#                "area_code_translations",
#                "areas_mapping.csv",
#            ),
#            names=column_names,
#            usecols=usecols,
#        )
#        return area_mapping_df
#
#    def read_companysize_census(self, area_mapping, oa_in_world):
#        """
#        Gives nr. of companies with nr. of employees per MSOA.
#        Filter the MOSArea according to the OAreas used.
#        (
#            NOMIS: UK Business Counts - local units by industry and employment size band
#            Note: Currently the data of 2019 is used, since the 2011 data
#                  seems to be unavailable.
#        )
#        """
#        companysize_df = pd.read_csv(
#            os.path.join(
#                os.path.dirname(os.path.realpath(__file__)),
#                "..",
#                "data",
#                "processed",
#                "census_data",
#                "company_data",
#                "companysize_msoa11cd_2019.csv",
#            ),
#        )
#        companysize_df = companysize_df.set_index("MSOA")
#
#        # filter out MSOA areas that are simulated
#        msoa = np.unique(area_mapping[
#            area_mapping["OA"].isin(list(oa_in_world))
#        ]["MSOA"].values)
#        companysize_df = companysize_df.loc[msoa]
#
#        assert companysize_df.isnull().values.any() == False
#
#        return companysize_df
#
#    def read_companysector_census(self, area_mapping, oa_in_world):
#        """
#        Gives number of companies by type according to NOMIS sector data at the MSOA level
#        TableID: WD601EW
#        https://www.nomisweb.co.uk/census/2011/wd601ew
#        """
#        companysector_df = pd.read_csv(
#            os.path.join(
#                os.path.dirname(os.path.realpath(__file__)),
#                "..",
#                "data",
#                "processed",
#                "census_data",
#                "company_data",
#                "companysector_msoa11cd_2011.csv",
#            ),
#        )
#        companysector_df = companysector_df.set_index("MSOA")
#
#        # filter out MSOA areas that are simulated
#        msoa = np.unique(area_mapping[
#            area_mapping["OA"].isin(list(oa_in_world))
#        ]["MSOA"].values)
#        companysector_df = companysector_df.loc[msoa]
#
#        companysector_df = companysector_df.reset_index()
#        companysector_df = companysector_df.rename(columns={"index": "MSOA"})
#
#        return companysector_df
#
#    def read_compsec_by_sex(self, oa_in_world):
#        """
#        Gives number dict of discrete probability distributions by sex of the
#        different industry sectors at the OA level.
#        The dict is of the format: {[oa]: {[gender('m'/'f')]: [distribution]}}
#        
#        TableID: KS605EW to KS607EW
#        https://www.nomisweb.co.uk/census/2011/ks605ew
#        """
#
#        compsec_by_sex_df = pd.read_csv(
#            os.path.join(
#                os.path.dirname(os.path.realpath(__file__)),
#                "..",
#                "data",
#                "processed",
#                "census_data",
#                "company_data",
#                "companysector_by_sex_cleaned.csv",
#            ),
#            index_col=0,
#        )
#        compsec_by_sex_df = compsec_by_sex_df.drop(
#            ['date', 'geography', 'rural urban'], axis=1,
#        )
#        compsec_by_sex_df = compsec_by_sex_df.rename(
#            columns={"oareas": "OA"}
#        )
#
#        # define all columns in csv file relateing to males
#        m_columns = [col for col in compsec_by_sex_df.columns.values if "m " in col]
#        m_columns.remove('m all')
#        m_columns.remove('m R S T U')
#
#        f_columns = [col for col in compsec_by_sex_df.columns.values if "f " in col]
#        f_columns.remove('f all')
#        f_columns.remove('f R S T U')
#
#        uni_columns = [col for col in compsec_by_sex_df.columns.values if "all " in col]
#        compsec_by_sex_df = compsec_by_sex_df.drop(
#            uni_columns + ['m all', 'm R S T U', 'f all', 'f R S T U'], axis=1,
#        )
#        compsec_by_sex_df = compsec_by_sex_df[
#            compsec_by_sex_df["OA"].isin(list(oa_in_world))
#        ]
#        compsec_by_sex_df = compsec_by_sex_df.set_index('OA')
#
#        # use the counts to get key company sector ratios
#        self.read_key_compsec_by_sex(compsec_by_sex_df)
#        
#        # convert counts to ratios
#        compsec_by_sex_df.loc[:, m_columns] = compsec_by_sex_df.loc[:, m_columns].div(
#            compsec_by_sex_df[m_columns].sum(axis=1), axis=0
#        )
#        compsec_by_sex_df.loc[:, f_columns] = compsec_by_sex_df.loc[:, f_columns].div(
#            compsec_by_sex_df[f_columns].sum(axis=1), axis=0
#        )
#        return compsec_by_sex_df
#
#
#    def read_key_compsec_by_sex(self, companysector_by_sex_df):
#        """
#        Specifies the number of people in a given REGION who work in
#        a key sector such as health-care and education.
#
#        Derives from the NOMIS annual occupational survey
#        https://www.nomisweb.co.uk/query/construct/summary.asp?mode=construct&version=0&dataset=168
#        """
#
#        education_healthcare_by_sex_df = pd.read_csv(
#            os.path.join(
#                os.path.dirname(os.path.realpath(__file__)),
#                "..",
#                'data',
#                'census_data',
#                'output_area',
#                'NorthEast',
#                'health_education_by_sex_NorthEast.csv'
#            ),
#            index_col=0,
#        )
#        education_healthcare_by_sex_df = education_healthcare_by_sex_df.rename(
#            columns={"males": "male", "females": "female"}
#        )
#        education_df = education_healthcare_by_sex_df[
#            education_healthcare_by_sex_df['occupations'].str.contains('education')
#        ]
#        healthcare_df = education_healthcare_by_sex_df[
#            ~education_healthcare_by_sex_df.occupations.isin(education_df.occupations)
#        ]
#        
#        self.get_key_compsec_ratio_by_sex(
#            education_df, healthcare_df, companysector_by_sex_df
#        )
#        self.get_key_compsec_distr_by_sex(education_df, healthcare_df)
#    
#    def get_key_compsec_distr_by_sex(self, education_df, healthcare_df):
#        """
#        """
#        # Get distribution of duties within key sector
#        healthcare_distr_df = healthcare_df.loc[
#            :,["male", "female"]
#        ].div(
#            healthcare_df[["male", "female"]].sum(axis=0), axis=1
#        )
#        #healthcare_distr_df["healthcare_sector"] = healthcare_df.occupations.values
#        healthcare_distr_df["healthcare_sector_id"] = healthcare_df.occupation_codes.values
#        healthcare_distr_df["sector"] = ["healthcare"] * len(healthcare_distr_df.index.values)
#        healthcare_distr_df = healthcare_distr_df.groupby(
#            ['sector', 'healthcare_sector_id']
#        ).mean()
#        
#        education_distr_df = education_df.loc[
#            :,["male", "female"]
#        ].div(
#            education_df[["male", "female"]].sum(axis=0), axis=1
#        )
#        #education_distr_df["education_sector"] = education_df.occupations.values
#        education_distr_df["education_sector_id"] = education_df.occupation_codes.values
#        education_distr_df["sector"] = ["education"] * len(education_distr_df.index.values)
#        education_distr_df = education_distr_df.groupby(
#            ['sector', 'education_sector_id']
#        ).mean()
#        
#        compsec_specic_distr_by_sex_df = pd.concat([
#            healthcare_distr_df, education_distr_df
#        ])
#        compsec_specic_distr_by_sex_df = compsec_specic_distr_by_sex_df.sort_index()
#        del healthcare_distr_df, education_distr_df
#
#        self.key_compsec_distr_by_sex_df = compsec_specic_distr_by_sex_df
#
#    def get_key_compsec_ratio_by_sex(
#            self,
#            education_df,
#            healthcare_df,
#            companysector_by_sex_df
#        ):
#        """
#        """
#        # Get ratio of people work in any compared to the specific key sector 
#        male_healthcare_ratio = np.sum(healthcare_df["male"]) / \
#            np.sum(companysector_by_sex_df["m Q"])
#        male_education_ratio = np.sum(education_df["male"]) / \
#            np.sum(companysector_by_sex_df["m P"])
#        female_healthcare_ratio = np.sum(healthcare_df["female"]) / \
#            np.sum(companysector_by_sex_df["f Q"])
#        female_education_ratio = np.sum(education_df["female"]) / \
#            np.sum(companysector_by_sex_df["f P"])
# 
#        compsec_specic_ratio_by_sex_df = pd.DataFrame(
#            np.array([
#                [male_education_ratio, female_education_ratio],
#                [male_healthcare_ratio, female_healthcare_ratio]
#            ]),
#            index=['education', 'healthcare'],
#            columns=['male', 'female'],
#            dtype=np.float,
#        )
#        del (
#            male_healthcare_ratio, male_education_ratio,
#            female_healthcare_ratio, female_education_ratio,
#        )
#        self.key_compsec_ratio_by_sex_df = compsec_specic_ratio_by_sex_df
#
#    def read_commute_method(DATA_DIR: str, freq: bool = True) -> pd.DataFrame:
#        """
#        The dataframe derives from:
#        TableID: QS701UK
#        https://www.nomisweb.co.uk/census/2011/qs701ew
#
#        Args:
#        DATA_DIR: path to dataset folder (default should be output_area folder) 
#
#        Returns:
#        pandas dataframe with ratio of males and females per output area 
#
#        """
#        travel_df = pd.read_csv(
#            os.path.join(
#                os.path.dirname(os.path.realpath(__file__)),
#                "..",
#                "data",
#                "census_data",
#                "middle_output_area",
#                "NorthEast",
#                "flow_method_oa_qs701northeast_2011.csv",
#            ),
#            delimiter=",",
#            delim_whitespace=False,
#        )
#        travel_df = travel_df.rename(columns={"geography code": "residence"})
#        travel_df = travel_df.set_index("residence")
#
#        # re-group dataset
#        travel_df["home"] = travel_df[
#            [c for c in travel_df.columns if " home;" in c]
#        ].sum(axis=1)
#        travel_df = travel_df.drop(
#            columns=[c for c in travel_df.columns if " home;" in c]
#        )
#        travel_df["public"] = travel_df[
#            [
#                c
#                for c in travel_df.columns
#                if "metro" in c or "Train" in c or "coach" in c
#            ]
#        ].sum(axis=1)
#        travel_df = travel_df.drop(
#            columns=[
#                c
#                for c in travel_df.columns
#                if "metro" in c or "Train" in c or "coach" in c
#            ]
#        )
#        travel_df["private"] = travel_df[
#            [
#                c
#                for c in travel_df.columns
#                if "Taxi" in c
#                or "scooter" in c
#                or "car" in c
#                or "Bicycle" in c
#                or "foot" in c
#            ]
#        ].sum(axis=1)
#        travel_df = travel_df.drop(
#            columns=[
#                c
#                for c in travel_df.columns
#                if "Taxi" in c
#                or "scooter" in c
#                or "car" in c
#                or "Bicycle" in c
#                or "foot" in c
#            ]
#        )
#        travel_df = travel_df[["home", "public", "private"]]
#
#        # create dictionary to merge OA into MSOA
#        dirs = os.path.join(
#            os.path.dirname(os.path.realpath(__file__)),
#            "..",
#            "data",
#            "census_data",
#            "area_code_translations",
#        )
#        dic = pd.read_csv(
#            dirs + "./PCD11_OA11_LSOA11_MSOA11_LAD11_RGN17_FID_EW_LU.csv",
#            delimiter=",",
#            delim_whitespace=False,
#        )
#
#        # merge OA into MSOA
#        travel_df = travel_df.merge(msoa2oa_df, left_index=True, right_index=True,)
#        travel_df = travel_df.groupby(["MSOA11CD"]).sum()
#
#        if freq:
#            # Convert to ratios
#            travel_df["home"] /= travel_df.sum(axis=1)
#            travel_df["public"] /= travel_df.sum(axis=1)
#            travel_df["private"] /= travel_df.sum(axis=1)
#        return travel_df
#
#    def read_london_stat_pcs(self):
#        london_stat_pcs = pd.read_csv(
#            os.path.join(
#                os.path.dirname(os.path.realpath(__file__)),
#                "..",
#                "data",
#                "travel",
#                "London_station_coordinates.csv"
#            )
#        )
#
#        self.london_stat_pcs = london_stat_pcs
#
#    def read_non_london_stat_pcs(self):
#        non_london_stat_pcs = pd.read_csv(
#            os.path.join(
#                os.path.dirname(os.path.realpath(__file__)),
#                "..",
#                "data",
#                "travel",
#                "non_London_station_coordinates.csv"
#            )
#        )
#
#        self.non_london_stat_pcs = non_london_stat_pcs
#
#
#    def read_uk_pcs_coordinates(self):
#        uk_pcs_coordinates = pd.read_csv(
#            os.path.join(
#                os.path.dirname(os.path.realpath(__file__)),
#                "..",
#                "data",
#                "geographical_data",
#                "ukpostcodes_coordinates.csv"
#            )
#        )
#
#        self.uk_pcs_coordinates = uk_pcs_coordinates
#
#
#    def read_msoa_coordinates(self):
#        msoa_coordinates = pd.read_csv(
#            os.path.join(
#                os.path.dirname(os.path.realpath(__file__)),
#                "..",
#                "data",
#                "geographical_data",
#                "msoa_coordinates_englandwales.csv"
#            )
#        )
#
#        self.msoa_coordinates = msoa_coordinates
#
#    def read_msoa_oa_coordinates(self):
#        msoa_oa_coordinates = pd.read_csv(
#            os.path.join(
#                os.path.dirname(os.path.realpath(__file__)),
#                "..",
#                "data",
#                "geographical_data",
#                "msoa_oa.csv"
#            )
#        )
#
#        self.msoa_oa_coordinates = msoa_oa_coordinates
#    
#    def create_workflow_df(
#        self,
#        area_mapping,
#        oa_in_world,
#        DATA_DIR: str = os.path.join(
#            os.path.dirname(os.path.realpath(__file__)),
#            "..",
#            "data",
#            "census_data",
#            "flow/",
#        ),
#    ) -> dict:
#        """
#        Workout where people go to work. It is for the whole of England & Wales
#        and can easily be stripped to get single regions.
#        The dataframe from NOMIS:
#            TableID: WU01EW
#            https://wicid.ukdataservice.ac.uk/cider/wicid/downloads.php
#
#        Args:
#            DATA_DIR: path to dataset (csv file)
#
#        Returns:
#            dictionary with frequencies of populations 
#        """
#        dirs = os.path.join(
#            os.path.dirname(os.path.realpath(__file__)),
#            "..",
#            "data",
#            "processed/",
#        )
#        wf_df = pd.read_csv(
#            dirs + "flow_in_msoa_wu01ew_2011.csv",
#            delimiter=",",
#            delim_whitespace=False,
#            skiprows=1,
#            usecols=[0, 1, 3, 4],
#            names=["home_msoa11cd", "work_msoa11cd", "n_man", "n_woman"],
#        )
#        # filter out MSOA areas that are simulated
#        msoa = np.unique(area_mapping[
#            area_mapping["OA"].isin(list(oa_in_world))
#        ]["MSOA"].values)
#        wf_df = wf_df[wf_df["home_msoa11cd"].isin(list(msoa))]
#        # convert into ratios
#        wf_df = wf_df.groupby(["home_msoa11cd", "work_msoa11cd"]).agg(
#            {"n_man": "sum", "n_woman": "sum"}
#        )
#        wf_df["n_man"] = (
#            wf_df.groupby(level=0)["n_man"]
#            .apply(lambda x: x / float(x.sum(axis=0)))
#            .values
#        )
#        wf_df["n_woman"] = (
#            wf_df.groupby(level=0)["n_woman"]
#            .apply(lambda x: x / float(x.sum(axis=0)))
#            .values
#        )
#        return wf_df
#
#
#if __name__ == "__main__":
#
#    ip = Inputs()
#    print(ip.workflow_df)
#    #print("companysize_df\n", ip.companysize_df)
#    #print("compsec_by_sex_df \n", ip.compsec_by_sex_df)
#    #print(ip.areas_coordinates_df)
