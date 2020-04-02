import pandas as pd
import numpy as np
import xarray as xr
import os


def read_home_work_areacode(DATA_DIR):
    """
    The dataframe derives from:
        TableID: WU01UK
        https://www.nomisweb.co.uk/census/2011/wu01uk
    , but is processed to be placed in a pandas.DataFrame.
    The MSOA area code is used for homes (rows) and work (columns).
    """
    flow_female_file = 'flow_female_in_msoa_wu01northeast_2011.csv'
    flow_male_file = 'flow_male_in_msoa_wu01northeast_2011.csv'
   
    flow_female_df = pd.read_csv(DATA_DIR + flow_female_file)
    flow_male_df = pd.read_csv(DATA_DIR + flow_female_file)

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
    flow_method_file = "flow_method_oa_qs701northeast_2011.csv"
    flow_method_df = pd.read_csv(
        DATA_DIR + "flow_method_oa_qs701northeast_2011.csv",
        delimiter=',',
        delim_whitespace=False,
    )
    travel_df = travel_df.rename(columns={"geography code": "residence"})
    travel_df = travel_df.set_index('residence')

    travel_df["home"] = travel_df[
        [c for c in travel_df.columns if " home;" in c]
    ].sum(axis=1)
    travel_df = travel_df.drop(
        columns=[c for c in travel_df.columns if " home;" in c]
    )

    travel_df["public"] = travel_df[
        [c for c in travel_df.columns if "metro" in c or "Train" in c or "coach" in c]
    ].sum(axis=1)
    travel_df = travel_df.drop(
        columns=[c for c in travel_df.columns if "metro" in c or "Train" in c or "coach" in c]
    )

    travel_df["private"] = travel_df[
        [c for c in travel_df.columns if "Taxi" in c or "scooter" in c or "car" in c or "Bicycle" in c or "foot" in c]
    ].sum(axis=1)
    travel_df = travel_df.drop(
        columns=[c for c in travel_df.columns if "Taxi" in c or "scooter" in c or "car" in c or "Bicycle" in c or "foot" in c]
    )

    travel_df = travel_df[["home", "public", "private"]]

    if freq:
        # Convert to ratios
        travel_df["home"] /= travel_df.sum(axis=1)
        travel_df["public"] /= travel_df.sum(axis=1)
        travel_df["private"] /= travel_df.sum(axis=1)
    return travel_df


def oa2msoa():
    return []


def create_input_dict(
    DATA_DIR: str = os.path.join(
        "..", "data", "census_data", "output_area", "NorthEast"
    )
) -> dict:
    """Reads and formats input dataframe to populate realistic households in England and Wales

    Args:
        DATA_DIR: path to dataset (csv file)

    Returns:
        dictionary with frequencies of populations 
    """
    flow_female_df, flow_male_df = read_home_work_areacode(DATA_DIR)
    commute_method_df = read_commute_method(DATA_DIR)

    # group oa to msoa
    commute_method_df = oa2msoa(commute_method_df)

    input_dict = {
        "n_home": ,
        "n_public": ,
        "n_private": , 
    }

    return input_dict


if __name__ == "__main__":

    input_dict = create_input_dict()

    print(input_dict[""])
