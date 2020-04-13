import pandas as pd
import numpy as np
import os


class Inputs:
    """
    Reads in data used to populate the simulation
    """

    def __init__(
        self,
        zone="NorthEast",
        DATA_DIR: str = os.path.join("..", "data", "processed", "census_data"),
    ):
        self.zone = zone
        self.DATA_DIR = DATA_DIR
        self.OUTPUT_AREA_DIR = os.path.join(self.DATA_DIR, "output_area", zone)
        # self.MIDDLE_OUTPUT_AREA_DIR = os.path.join(self.DATA_DIR, "middle_output_area", zone)
        # oa2msoa_df = self.oa2msoa()

        # Read census data on high resolution map (OA)
        self.n_residents = pd.read_csv(
            os.path.join(self.OUTPUT_AREA_DIR, "residents.csv"),
            names=["output_area", "n_residents"],
            header=0,
            index_col="output_area",
        )

        self.age_freq, self.decoder_age = self.read("age_structure.csv")
        self.sex_freq, self.decoder_sex = self.read("sex.csv")
        self.household_composition_freq, self.decoder_household_composition = self.read(
            "household_composition.csv"
        )
        self.encoder_household_composition = {}
        for i, column in enumerate(self.household_composition_freq.columns):
            self.encoder_household_composition[column] = i
        self.school_df = pd.read_csv(os.path.join(self.DATA_DIR, 'school_data', 'uk_schools_data.csv'))
        self.hospital_df = pd.read_csv(os.path.join('..','data','census_data','hospital_data','england_hospitals.csv'))
        self.areas_coordinates_df = self.read_coordinates()
        # self.company_df = self.read_companysize_census()
        # Read census data on low resolution map (MSOA)
        # self.oa2msoa_df = self.oa2msoa()
        # self.workflow_dict = self.create_workflow_dict()
        # self.companysize_df = self.read_companysize_census()

    def read(self, filename):
        df = pd.read_csv(
            os.path.join(self.OUTPUT_AREA_DIR, filename), index_col="output_area"
        )
        freq = df.div(df.sum(axis=1), axis=0)
        decoder = {i: df.columns[i] for i in range(df.shape[-1])}
        return freq, decoder

    def read_coordinates(self):
        areas_coordinates_df_path = os.path.join(
            #os.path.dirname(os.path.realpath(filename)),
            "..",
            "data",
            "processed",
            "geographical_data",
            "oa_coorindates.csv",
        )
        areas_coordinates_df = pd.read_csv(areas_coordinates_df_path)
        areas_coordinates_df.set_index("OA11CD", inplace=True)
        return areas_coordinates_df

    def oa2msoa(self):
        """
        Creat link between OA and MSOA layers.
        """
        usecols = [0, 1]
        column_names = ["OA11CD", "MSOA11CD"]
        oa2msoa_df = self.read_df(
            os.path.join(self.DATA_DIR, "area_code_translations"),
            "oa_msoa_englandwales_2011.csv",
            column_names,
            usecols,
            "OA11CD",
        )

        return oa2msoa_df

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
        company_df = self.read_df(
            self.MIDDLE_OUTPUT_AREA_DIR,
            "business_counts_northeast_2019.csv",
            column_names,
            usecols,
            "MSOA11CD",
        )

        assert company_df.isnull().values.any() == False
        return company_df

    def read_home_work_areacode(DATA_DIR):
        """
        The dataframe derives from:
            TableID: WU01EW
            https://wicid.ukdataservice.ac.uk/cider/wicid/downloads.php
        , but is processed to be placed in a pandas.DataFrame.
        The MSOA area code is used for homes (rows) and work (columns).
        """
        flow_female_file = "flow_female_in_msoa_wu01northeast_2011.csv"
        flow_male_file = "flow_male_in_msoa_wu01northeast_2011.csv"

        flow_female_df = pd.read_csv(DATA_DIR + flow_female_file)
        flow_female_df = flow_female_df.set_index("residence")

        flow_male_df = pd.read_csv(DATA_DIR + flow_female_file)
        flow_male_df = flow_male_df.set_index("residence")

        return flow_female_df, flow_male_df

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
        dirs = "../data/census_data/area_code_translations/"
        dic = pd.read_csv(
            dirs + "./PCD11_OA11_LSOA11_MSOA11_LAD11_RGN17_FID_EW_LU.csv",
            delimiter=",",
            delim_whitespace=False,
        )

        # merge OA into MSOA
        travel_df = travel_df.merge(
            dic.drop_duplicates(subset="OA11CD").set_index("OA11CD")["MSOA11CD"],
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
        self, DATA_DIR: str = os.path.join("..", "data", "census_data", "flow/",)
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
        flow_dirname = os.path.join(self.DATA_DIR, "middle_output_area", "NorthEast")

        flow_female_df = pd.read_csv(os.path.join(flow_dirname, flow_female_file))
        flow_female_df = flow_female_df.set_index("residence")

        flow_male_df = pd.read_csv(os.path.join(flow_dirname, flow_male_file))
        flow_male_df = flow_male_df.set_index("residence")

        home_msoa = (
            flow_female_df.index
        )  # flow_female_df&flow_female_df share the same indices
        female_work_msoa_list = []
        n_female_work_msoa_list = []
        male_work_msoa_list = []
        n_male_work_msoa_list = []
        for hmsoa in home_msoa:
            # Where do woman go to work in ratios
            female_work_msoa_list.append(
                flow_female_df.loc[hmsoa]
                .dropna()[flow_female_df.loc[hmsoa] != 0.0]
                .index.values
            )
            n_female_work_msoa_list.append(
                flow_female_df.loc[hmsoa]
                .dropna()[flow_female_df.loc[hmsoa] != 0.0]
                .values
                / flow_female_df.loc[hmsoa]
                .dropna()[flow_female_df.loc[hmsoa] != 0.0]
                .values.sum()
            )
            # Where do man go to work in ratios
            male_work_msoa_list.append(
                flow_male_df.loc[hmsoa]
                .dropna()[flow_male_df.loc[hmsoa] != 0.0]
                .index.values
            )
            n_male_work_msoa_list.append(
                flow_male_df.loc[hmsoa].dropna()[flow_male_df.loc[hmsoa] != 0.0].values
                / flow_male_df.loc[hmsoa]
                .dropna()[flow_male_df.loc[hmsoa] != 0.0]
                .values.sum()
            )

        workflow_dict = {
            "home_msoa": home_msoa,
            "female_work_msoa": female_work_msoa_list,
            "n_female_work_msoa": n_female_work_msoa_list,
            "male_work_msoa": male_work_msoa_list,
            "n_male_work_msoa": n_male_work_msoa_list,
        }

        return workflow_dict


if __name__ == "__main__":

    ip = Inputs()
    print(ip.age_freq)
    print(ip.decoder_age)
    print(ip.decoder_sex)
    print(ip.decoder_household_composition)
    print(ip.areas_coordinates_df)
