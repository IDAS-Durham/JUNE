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
    travel_df["home"] = travel_df[[c for c in travel_df.columns if " home;" in c]].sum(
        axis=1
    )
    travel_df = travel_df.drop(columns=[c for c in travel_df.columns if " home;" in c])
    travel_df["public"] = travel_df[
        [c for c in travel_df.columns if "metro" in c or "Train" in c or "coach" in c]
    ].sum(axis=1)
    travel_df = travel_df.drop(
        columns=[
            c for c in travel_df.columns if "metro" in c or "Train" in c or "coach" in c
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
    dirs = "/home/christovis/PhD/5_COVID_19/data/census_data/area_code_translations/"
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


def read_workplace_size(DATA_DIR: str, freq: bool = True) -> pd.DataFrame:
    """
    The dataframe derives from:
        Dataset: UK Business Counts - local units by industry and employment size band
        https://www.nomisweb.co.uk/query/construct/components/stdListComponent.asp?menuopt=12&subcomp=100

    Args:
    Returns:
    """
    workplc_df = pd.read_csv(
        DATA_DIR+"business_counts_northeast_2019.csv",
        skiprows=7,
        skipfooter=21,
        delimiter=',',
        delim_whitespace=False,
    )
    workplc_df = workplc_df.set_index('mnemonic')


def align_dfs():

    return


def create_input_dict(
    DATA_DIR: str = os.path.join("..", "data", "census_data", "flow/",)
) -> dict:
    """Reads and formats input dataframe to populate realistic households in England and Wales

    Args:
        DATA_DIR: path to dataset (csv file)

    Returns:
        dictionary with frequencies of populations 
    """
    flow_female_df, flow_male_df = read_home_work_areacode(DATA_DIR)
    commute_method_df = read_commute_method(DATA_DIR)
    workplace_size_df = read_workplace_size(DATA_DIR)

    home_msoa = (
        flow_female_df.index
    )  # flow_female_df&flow_female_df share the same indices
    female_work_msoa_list = []
    n_female_work_msoa_list = []
    male_work_msoa_list = []
    n_male_work_msoa_list = []
    for hmsoa in home_msoa:
        female_work_msoa_list.append(
            flow_female_df.loc[hmsoa]
            .dropna()[flow_female_df.loc[hmsoa] != 0.0]
            .index.values
        )
        # Convert to ratios
        n_female_work_msoa_list.append(
            flow_female_df.loc[hmsoa].dropna()[flow_female_df.loc[hmsoa] != 0.0].values
            / flow_female_df.loc[hmsoa]
            .dropna()[flow_female_df.loc[hmsoa] != 0.0]
            .values.sum()
        )
        male_work_msoa_list.append(
            flow_male_df.loc[hmsoa]
            .dropna()[flow_male_df.loc[hmsoa] != 0.0]
            .index.values
        )
        # Convert to ratios
        n_male_work_msoa_list.append(
            flow_male_df.loc[hmsoa].dropna()[flow_male_df.loc[hmsoa] != 0.0].values
            / flow_male_df.loc[hmsoa]
            .dropna()[flow_male_df.loc[hmsoa] != 0.0]
            .values.sum()
        )

    [] = align_dfs()
    input_dict = {
        "home_msoa": home_msoa,
        "female_work_msoa": female_work_msoa_list,
        "n_female_work_msoa": n_female_work_msoa_list,
        "male_work_msoa": male_work_msoa_list,
        "n_male_work_msoa": n_male_work_msoa_list,
        "n_home": commute_method_df["home"],
        "n_public": commute_method_df["public"],
        "n_private": commute_method_df["private"],
    }

    return input_dict


if __name__ == "__main__":

    input_dict = create_input_dict()

    print(input_dict)
