import pandas as pd
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

def read_household_composition_people():
    """
    TableID: QS112EW
    https://www.nomisweb.co.uk/census/2011/qs112ew
    """

def read_household_size()
"""
    https://www.nomisweb.co.uk/census/2011/qs406ew
    QS406EW
"""
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


def bedrooms2households(bedrooms_df: pd.DataFrame) -> pd.DataFrame:
    """Converts bedroom data into assumptions of how households are populated by different age groups
    
    Args: 
        bedrooms_df: number of bedrooms per different family types
    
    Returns:
        households_df: how households are populated by age group
    """

    households_df = pd.DataFrame()
    households_df["0 0 0 1"] = bedrooms_df["Person"]
    # ASSUMPTIONS
    # i) Old families are composed of couples only
    households_df["0 0 2 0"] = bedrooms_df["Old_Family"]
    # ii) Lone parents with one or two bedrooms only have one child
    households_df["1 1 0 0"] = (
        bedrooms_df["Lone_Family_1B"] + bedrooms_df["Lone_Family_2B"]
    )
    # iii) Lone parents with three or more bedrooms only have two children
    households_df["2 1 0 0"] = bedrooms_df["Lone_Family_3B"] 

    households_df["3 1 0 0"] = bedrooms_df["Lone_Family_4B"]
    # iv) Families classified as others count as young adults with no children
    households_df["0 2 0 0"] = (
        bedrooms_df["Young_Family_1B"]
        + 0.2*bedrooms_df["Young_Family_2B"]
        + bedrooms_df["Other_Family_1B"]
        + bedrooms_df["Other_Family_2B"]
    )
    households_df["1 2 0 0"] = 0.8*bedrooms_df["Young_Family_2B"] 
    households_df["2 2 0 0"] = bedrooms_df["Young_Family_3B"] 
    households_df["3 2 0 0"] = bedrooms_df["Young_Family_4B"]
    households_df["0 3 0 0"] = bedrooms_df["Other_Family_3B"]
    households_df["0 4 0 0"] = bedrooms_df["Other_Family_4B"]
    return households_df


def create_input_dict(
    DATA_DIR: str = os.path.join("..", "data", "census_data", "output_area", "NorthEast")
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
    bedrooms_df = read_bedrooms_df(DATA_DIR)
    households_df = bedrooms2households(bedrooms_df)

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

    print(input_dict["household_freq"])
