import pandas as pd
import numpy as np
import os


def read_df(
    DATA_DIR: str, filename: str, column_names: list, usecols: list, index: str
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


def read_household_composition_people(DATA_DIR, ages_df):
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
        DATA_DIR, household_people, column_names, usecols, "output_area"
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

    comp_people_df["Family_0k"][
        ~((areas_no_house_old) & (areas_with_old))
    ] += comp_people_df["Other"][~((areas_no_house_old) & (areas_with_old))]
    comp_people_df["Old_Family"][
        (areas_no_house_old) & (areas_with_old)
    ] += comp_people_df["Other"][(areas_no_house_old) & (areas_with_old)]
    comp_people_df = comp_people_df.drop(
        columns=[
            c
            for c in comp_people_df.columns
            if "SS" in c or "Couple" in c or "Other" in c
        ]
    )

    return comp_people_df


def read_population_df(DATA_DIR: str, freq: bool = True) -> pd.DataFrame:
    """Read population dataset downloaded from https://www.nomisweb.co.uk/census/2011/ks101ew        

    Args:
        DATA_DIR: path to dataset folder (default should be output_area folder) 

    Returns:
        pandas dataframe with ratio of males and females per output area 

    """
    population = "usual_resident_population.csv"
    population_column_names = [
        "output_area",
        "n_residents",
        "males",
        "females",
    ]
    population_usecols = [2, 4, 5, 6]
    population_df = read_df(
        DATA_DIR,
        population,
        population_column_names,
        population_usecols,
        "output_area",
    )

    pd.testing.assert_series_equal(
        population_df["n_residents"],
        population_df["males"] + population_df["females"],
        check_names=False,
    )
    if freq:
        # Convert to ratios
        population_df["males"] /= population_df["n_residents"]
        population_df["females"] /= population_df["n_residents"]
    return population_df


def read_household_df(DATA_DIR: str, freq: bool = True) -> pd.DataFrame:
    """Read household dataset downloaded from https://www.nomisweb.co.uk/census/2011/ks105ew

    Args:
        DATA_DIR: path to dataset folder (default should be output_area folder) 

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
        DATA_DIR, households, households_names, households_usecols, "output_area",
    )

    return households_df


def read_ages_df(DATA_DIR: str, freq: bool = True) -> pd.DataFrame:
    """Read ages dataset downloaded from https://www.nomisweb.co.uk/census/2011/ks102ew

    Args:
        DATA_DIR: path to dataset folder (default should be output_area folder) 

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

    ages_df = read_df(DATA_DIR, ages, ages_names, ages_usecols, "output_area")
    if freq:
        ages_df = ages_df.div(ages_df.sum(axis=1), axis=0)
    return ages_df


def read_bedrooms_df(DATA_DIR: str, freq: bool = True) -> pd.DataFrame:
    """Read household dataset downloaded from https://www.nomisweb.co.uk/census/2011/lc1402ew
    Args:
        DATA_DIR: path to dataset folder (default should be output_area folder) 

    Returns:
        pandas dataframe with number of bedrooms per household type per output area 

    """
    bedrooms = "household_compositon_by_bedrooms.csv"
    bedrooms_usecols = (
        [2, 8, 18] + list(range(24, 28)) + list(range(29, 33)) + list(range(34, 38))
    )

    bedrooms_names = [
        "output_area",
        "Person",  # regardless of bedrooms (only one person)
        "Old_Family",  # assumed to be 2 always
        "Young_Family_1B",
        "Young_Family_2B",
        "Young_Family_3B",
        "Young_Family_4B",
        "Lone_Family_1B",
        "Lone_Family_2B",
        "Lone_Family_3B",
        "Lone_Family_4B",
        "Other_Family_1B",
        "Other_Family_2B",
        "Other_Family_3B",
        "Other_Family_4B",
    ]

    bedrooms_df = read_df(
        DATA_DIR, bedrooms, bedrooms_names, bedrooms_usecols, "output_area"
    )
    if freq:
        bedrooms_df = bedrooms_df.div(bedrooms_df.sum(axis=1), axis=0)
    return bedrooms_df


def people_compositions2households(comp_people_df, freq=True):

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

    if freq:
        return households_df.div(households_df.sum(axis=1), axis=0)
    else:
        return households_df


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
    population_df = read_population_df(DATA_DIR)
    n_households_df = read_household_df(DATA_DIR)
    ages_df = read_ages_df(DATA_DIR)
    comp_people_df = read_household_composition_people(DATA_DIR, ages_df)
    households_df = people_compositions2households(comp_people_df)
    # bedrooms_df = read_bedrooms_df(DATA_DIR)
    # households_df = bedrooms2households(bedrooms_df)

    input_dict = {
        "n_residents": population_df["n_residents"],
        "n_households": n_households_df["n_households"],
        "age_freq": ages_df,
        "sex_freq": population_df[["males", "females"]],
        "household_composition_freq": households_df,
    }

    return input_dict


if __name__ == "__main__":

    input_dict = create_input_dict()

    print(input_dict["household_composition_freq"])
