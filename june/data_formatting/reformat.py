# Code to reformat of school, household, and social matrices
# UK data into our code's input system

import pandas as pd
import numpy as np
import os
from shutil import copyfile


def read_df(
    DATA_DIR: str, filename: str, column_names: list, usecols: list, index: str,
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

    df = pd.read_csv(
        os.path.join(DATA_DIR, filename), names=column_names, usecols=usecols, header=0,
    )
    df.set_index(index, inplace=True)
    return df


def read_population_df(OUTPUT_AREA_DIR) -> pd.DataFrame:
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
    population_usecols = [
        "geography code",
        "Variable: All usual residents; measures: Value",
        "Variable: Males; measures: Value",
        "Variable: Females; measures: Value",
    ]
    population_df = pd.read_csv(
        os.path.join(OUTPUT_AREA_DIR, population), usecols=population_usecols,
    )
    names_dict = dict(zip(population_usecols, population_column_names))
    population_df.rename(columns=names_dict, inplace=True)
    population_df.set_index("output_area", inplace=True)

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

    return population_df["n_residents"], population_df.drop(columns="n_residents")


def read_ages_df(OUTPUT_AREA_DIR: str, freq: bool = True) -> pd.DataFrame:
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

    ages_df = read_df(OUTPUT_AREA_DIR, ages, ages_names, ages_usecols, "output_area")
    return ages_df


def read_minimal_household_composition(OUTPUT_AREA_DIR):
    pass

def read_household_composition_people(OUTPUT_AREA_DIR, ages_df):
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
    comp_people_df = read_df(
        OUTPUT_AREA_DIR, household_people, column_names, usecols, "output_area"
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
        + 0.4 * comp_people_df["Other_1k"].loc[(areas_no_house_old) & (areas_with_old)]
    )

    comp_people_df = comp_people_df.drop(
        columns=[
            c
            for c in comp_people_df.columns
            if "SS" in c or "Couple" in c or "Other" in c
        ]
    )

    return comp_people_df


def read_household_df(OUTPUT_AREA_DIR: str) -> pd.DataFrame:
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

    households_df = read_df(
        OUTPUT_AREA_DIR,
        households,
        households_names,
        households_usecols,
        "output_area",
    )

    return households_df


def people_compositions2households(comp_people_df):

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
        comp_people_df["Old_Unclassified"] // 2 - comp_people_df["Old_Unclassified"] % 2
    ).apply(lambda x: max(x, 0))
    households_df[f"0 0 0 3"] = comp_people_df["Old_Unclassified"] % 2

    return households_df

def read_school_census(DATA_DIR):
    """
    Reads school location and sizes, it initializes a KD tree on a sphere,
    to query the closest schools to a given location.
    """
    school_filename = os.path.join(
        DATA_DIR, "school_data", "uk_schools_data.csv"
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



def downsample_social_matrix(matrix):
    #low_res_matrix = pd.DataFrame()

    '''
    print(matrix)

    low_res_matrix["0-4"] = matrix["0-4"]
    low_res_matrix["5-9"] = matrix["5-9"]
    low_res_matrix.loc["10-14"] = matrix.loc["10-12"] + matrix.loc["13-14"]
    low_res_matrix["10-14"] = matrix["10-12"] + matrix["13-14"]
    print(matrix.loc["10-12"])
    print(matrix.loc["13-14"])
    low_res_matrix["15-17"] = matrix["15-17"]
    low_res_matrix["18-19"] = matrix["18-19"]
    low_res_matrix["20-24"] = matrix["20-21"] + matrix["22-24"]
    low_res_matrix.loc["20-24"] = matrix.loc["20-21"] + matrix.loc["22-24"]
    low_res_matrix["25-29"] = matrix["25-29"]
    low_res_matrix["30-44"] = matrix["30-34"] + matrix["35-39"] + matrix["40-44"]
    low_res_matrix.loc["30-44"] = (
        matrix.loc["30-34"] + matrix.loc["35-39"] + matrix.loc["40-44"]
    )
    low_res_matrix["45-59"] = matrix["45-49"] + matrix["50-54"] + matrix["55-59"]
    low_res_matrix.loc["45-59"] = (
        matrix.loc["45-49"] + matrix.loc["50-54"] + matrix.loc["55-59"]
    )
    low_res_matrix["60-64"] = matrix["60-64"]
    low_res_matrix["65-74"] = matrix["65-69"] + matrix["70-74"]
    low_res_matrix.loc["65-74"] = matrix.loc["65-69"] + matrix.loc["70-74"]

    low_res_matrix.drop(
        [
            "10-12",
            "13-14",
            "20-21",
            "22-24",
            "30-34",
            "35-39",
            "40-44",
            "45-49",
            "50-54",
            "55-59",
            "65-69",
            "70-74",
        ], inplace=True
    )
    '''


    return matrix 


def reformat_social_matrices(raw_mixing_dir, processed_mixing_dir):
    social_matrices = ["all_school", "physical_school", "conversational_school"]

    reformat_social_matrices = []
    for sm in social_matrices:
        matrix = pd.read_excel(
            os.path.join(
                raw_mixing_dir, "BBC_repriprocal_matrices_by_type_context.xls"
            ),
            sheet_name=sm,
            index_col=0,
        )
        matrix.fillna(0.0, inplace=True)
        low_res_matrix = downsample_social_matrix(matrix)
        low_res_matrix.to_csv(os.path.join(processed_mixing_dir, f"{sm}.csv"))


if __name__ == "__main__":

    region = "EnglandWales"
    RAW_DATA_DIR = os.path.join("..", "data", "census_data")
    RAW_OUTPUT_AREA_DIR = os.path.join(RAW_DATA_DIR, "output_area", region)

    residents, sex_df = read_population_df(RAW_OUTPUT_AREA_DIR)
    ages_df = read_ages_df(RAW_OUTPUT_AREA_DIR)
    comp_people_df = read_household_composition_people(RAW_OUTPUT_AREA_DIR, ages_df)
    households_df = people_compositions2households(comp_people_df)
    school_df = read_school_census(RAW_DATA_DIR)

    DATA_DIR = os.path.join("..", "data", "processed", "census_data")
    OUTPUT_AREA_DIR = os.path.join(DATA_DIR, "output_area", region)
    if not os.path.exists(OUTPUT_AREA_DIR):
        os.makedirs(OUTPUT_AREA_DIR)

    residents.to_csv(os.path.join(OUTPUT_AREA_DIR, "residents.csv"))
    sex_df.to_csv(os.path.join(OUTPUT_AREA_DIR, "sex.csv"))
    ages_df.to_csv(os.path.join(OUTPUT_AREA_DIR, "age_structure.csv"))
    households_df.to_csv(os.path.join(OUTPUT_AREA_DIR, "household_composition.csv"))

    SCHOOL_DIR = os.path.join(DATA_DIR, "school_data")
    if not os.path.exists(SCHOOL_DIR):
        os.makedirs(SCHOOL_DIR)

    school_df.to_csv(os.path.join(DATA_DIR, "school_data", "uk_schools_data.csv"))

    GEO_DIR = os.path.join("..", "data", "processed", "geographical_data")

    if not os.path.exists(GEO_DIR):
        os.makedirs(GEO_DIR)
    copyfile(os.path.join("..", "data", "geographical_data", "oa_coorindates.csv"),
            os.path.join("..", "data", "processed", "geographical_data", "oa_coorindates.csv"))

    
