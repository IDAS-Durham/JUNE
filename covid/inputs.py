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
        DATA_DIR: str = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "data", "processed", "census_data"),
    ):
        self.zone = zone
        self.DATA_DIR = DATA_DIR
        self.OUTPUT_AREA_DIR = os.path.join(self.DATA_DIR, "output_area", zone)

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
        
        self.school_df = pd.read_csv(
            os.path.join(self.DATA_DIR, 'school_data', 'uk_schools_data.csv')
        )
        self.hospital_df = pd.read_csv(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), '..','data','census_data','hospital_data','england_hospitals.csv')
        )
        self.areas_coordinates_df = self.read_coordinates()
        self.contact_matrix = np.genfromtxt(
            os.path.join(
                self.DATA_DIR, "..", "social_mixing", "POLYMOD", "extended_polymod_UK.csv"
            ),
            delimiter =',',
        )

        # Read census data on low resolution map (MSOA)
        self.oa2msoa_df = self.oa2msoa(self.n_residents.index.values)
        self.workflow_df = self.create_workflow_df(self.oa2msoa_df["MSOA11CD"].values)
        self.companysize_df = self.read_companysize_census()
        self.companysector_df = self.read_companysector_census()
        self.companysector_by_sex_df = self.read_companysector_by_sex_census()
        self.companysector_specific_by_sex_df = self.read_companysector_specifc_by_sex()


    def read(self, filename):
        df = pd.read_csv(
            os.path.join(self.OUTPUT_AREA_DIR, filename), index_col="output_area"
        )
        freq = df.div(df.sum(axis=1), axis=0)
        decoder = {i: df.columns[i] for i in range(df.shape[-1])}
        return freq, decoder


    def read_coordinates(self):
        areas_coordinates_df_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "..",
            "data",
            "processed",
            "geographical_data",
            "oa_coorindates.csv",
        )
        areas_coordinates_df = pd.read_csv(areas_coordinates_df_path)
        areas_coordinates_df.set_index("OA11CD", inplace=True)
        return areas_coordinates_df


    def oa2msoa(self, oa_id):
        """
        Creat link between OA and MSOA layers.
        """
        usecols = [0, 1]
        column_names = ["OA11CD", "MSOA11CD"]
        oa2msoa_df = pd.read_csv(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "..",
                "data",
                "census_data",
                "area_code_translations",
                "oa_msoa_englandwales_2011.csv",
                )
            ,
            names=column_names,
            usecols=usecols,
        )
        oa2msoa_df = oa2msoa_df.set_index("OA11CD")
        # filter out OA areas that are simulated
        oa2msoa_df = oa2msoa_df[oa2msoa_df.index.isin(list(oa_id))]
        
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
        companysize_df = pd.read_csv(
                os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "..",
                "data",
                "census_data",
                "middle_output_area",
                "NorthEast",
                "business_counts_northeast_2019.csv"
                ),
            names=column_names,
            usecols=usecols,
        )
        companysize_df = companysize_df.set_index("MSOA11CD")

        assert companysize_df.isnull().values.any() == False

        return companysize_df

    def read_companysector_census(self):
        """
        Gives number of companies by type according to NOMIS sector data at the MSOA level
        TableID: WD601EW
        https://www.nomisweb.co.uk/census/2011/wd601ew
        """

        companysector_df = pd.read_csv(
                os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                '..',
                'data',
                'census_data',
                'middle_output_area',
                'NorthEast',
                'company_sector_cleaned_msoa.csv',
                ),
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

        industry_by_sex_df = pd.read_csv(
                os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    '..',
                    'data',
                    'census_data',
                    'output_area',
                    'NorthEast',
                    'industry_by_sex_cleaned.csv'
                    )
        )

        # define all columns in csv file relateing to males
        # here each letter corresponds to the industry sector (see metadata)
        m_columns = ['m A', 'm B', 'm C', 'm D', 'm E', 'm F', 'm G', 'm H', 'm I', 'm J',
                     'm K', 'm L', 'm M', 'm N', 'm O', 'm P', 'm Q', 'm R', 'm S', 'm T', 'm U']

        m_distributions = []
        for oa in range(len(industry_by_sex_df['oareas'])):
            total = float(industry_by_sex_df['m all'][oa])
            
            distribution = []
            for column in m_columns:
                distribution.append(float(industry_by_sex_df[column][oa])/total)
                
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

    def read_companysector_specific_by_sex(self):
        """
        Specifies the number of people in a given REGION who work in specific hospital roles 
        and educational roles

        Derives from the NOMIS annual occupational survey
        https://www.nomisweb.co.uk/query/construct/summary.asp?mode=construct&version=0&dataset=168
        """

        industrysector_specic_by_sex_df = pd.read_csv(
            "../data/census_data/output_area/NorthEast/health_education_by_sex_NorthEast.csv"
        )

        return industrysector_specic_by_sex_df
    
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
                os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    '..',
                    'data',
                    'census_data',
                    'middle_output_area',
                    'NorthEast',
                    'flow_method_oa_qs701northeast_2011.csv',
                ),
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
        dirs = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..","data","census_data","area_code_translations")
        dic = pd.read_csv(
            dirs + "./PCD11_OA11_LSOA11_MSOA11_LAD11_RGN17_FID_EW_LU.csv",
            delimiter=",",
            delim_whitespace=False,
        )

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


    def create_workflow_df(
        self, msoa, DATA_DIR: str = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "data", "census_data", "flow/")
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
        dirs = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", 'data', 'census_data', 'middle_output_area', 'EnglandWales/')
        wf_df = pd.read_csv(
            dirs + "flow_in_msoa_wu01ew_2011.csv",
            delimiter=',',
            delim_whitespace=False,
            skiprows=1,
            usecols=[0,1,3,4],
            names=["home_msoa11cd", "work_msoa11cd", "n_man", "n_woman"],
        )
        # filter out MSOA areas that are simulated
        wf_df = wf_df[wf_df["home_msoa11cd"].isin(list(msoa))]
        # convert into ratios
        wf_df = wf_df.groupby(
            ['home_msoa11cd', 'work_msoa11cd']
        ).agg({'n_man': 'sum', 'n_woman': 'sum'})
        
        wf_df['n_man'] = wf_df.groupby(level=0)['n_man'].apply(
            lambda x: x / float(x.sum(axis=0))
        ).values
        wf_df['n_woman'] = wf_df.groupby(level=0)['n_woman'].apply(
            lambda x: x / float(x.sum(axis=0))
        ).values

        return wf_df


if __name__ == "__main__":

    ip = Inputs()
    print(ip.contact_matrix.shape)
    print(ip.age_freq)
    print(ip.decoder_age)
    print(ip.decoder_sex)
    print(ip.decoder_household_composition)
    print(ip.areas_coordinates_df)
