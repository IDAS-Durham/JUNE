import pandas as pd
import os


def read_df(
    DATA_DIR: str, filename: str, column_names: list, usecols: list, index: str
) -> pd.DataFrame:
    """Read dataframe and format

    Args:
        DATA_DIR: path to dataset folder (default should be postcode_sector folder) 
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


def read_population_df(DATA_DIR: str) -> pd.DataFrame:
    """Read population dataset downloaded from https://www.nomisweb.co.uk/census/2011/ks101ew        

    Args:
        DATA_DIR: path to dataset folder (default should be postcode_sector folder) 

    Returns:
        pandas dataframe with ratio of males and females per postcode

    """
    population = "usual_resident_population.csv"
    population_column_names = [
        "postcode_sector",
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
        "postcode_sector",
    )

    pd.testing.assert_series_equal(
        population_df["n_residents"],
        population_df["males"] + population_df["females"],
        check_names=False,
    )
    # Convert to ratios
    population_df["males"] /= population_df["n_residents"]
    population_df["females"] /= population_df["n_residents"]
    return population_df


def read_household_df(DATA_DIR: str) -> pd.DataFrame:
    """Read household dataset downloaded from https://www.nomisweb.co.uk/census/2011/ks105ew

    Args:
        DATA_DIR: path to dataset folder (default should be postcode_sector folder) 

    Returns:
        pandas dataframe with number of households per postcode sector

    """

    households = "household_composition.csv"
    households_names = [
        "postcode_sector",
        "n_households",
    ]
    households_usecols = [2, 4]

    households_df = read_df(
        DATA_DIR, households, households_names, households_usecols, "postcode_sector",
    )

    return households_df


def create_input_df(
    DATA_DIR: str = os.path.join("..", "data", "census_data", "postcode_sector")
) -> dict:
    """Reads and formats input dataframe to populate realistic households in England and Wales

    Args:
        DATA_DIR: path to dataset (csv file)

    Returns:
        dictionary with frequencies of populations 
    """
    population_df = read_population_df(DATA_DIR)
    households_df = read_household_df(DATA_DIR)
    df = population_df.join(households_df)
    return df


if __name__ == "__main__":

    print(create_input_df())
