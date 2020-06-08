import os

import numpy as np
import pandas as pd

from june import paths

raw_path = f"{paths.data_path}/census_data/output_area/"
processed_path = f"{paths.data_path}/processed/census_data/output_area/"


def filter_and_sum(df, in_column):
    if len(in_column) > 1:
        df = df.filter(regex="|".join(in_column))
    else:
        df = df.filter(regex=in_column[0])
    return df.sum(axis=1)


df = pd.read_csv(raw_path / "household_houses.csv", index_col=0)

# All England and Wales data
assert len(df) == 181408

df.set_index("geography", inplace=True)
df.drop(columns=["date", "geography code", ], inplace=True)

df = df[
    [col for col in df.columns if "Total" not in col and "All categories" not in col]
]

encoding_households = pd.DataFrame()

encoding_households["0 0 0 0 1"] = filter_and_sum(df, ["One person household: Aged 65"])
encoding_households["0 0 0 1 0"] = filter_and_sum(df, ["One person household: Other"])
encoding_households["0 0 0 0 2"] = filter_and_sum(
    df, ["One family only: All aged 65 and over"]
)
encoding_households["0 0 0 2 0"] = filter_and_sum(df, ["No children"])

encoding_households["1 0 >=0 2 0"] = filter_and_sum(
    df,
    ["Married couple: One dependent child", "Cohabiting couple: One dependent child"],
)

encoding_households[">=2 0 >=0 2 0"] = filter_and_sum(
    df,
    [
        "Married couple: Two or more dependent",
        "Cohabiting couple: Two or more dependent",
    ],
)
encoding_households["0 0 >=1 2 0"] = filter_and_sum(
    df,
    [
        "Married couple: All children non-dependent",
        "Cohabiting couple: All children non-dependent",
    ],
)
encoding_households["1 0 >=0 1 0"] = filter_and_sum(
    df, ["Lone parent: One dependent child"]
)
encoding_households[">=2 0 >=0 1 0"] = filter_and_sum(
    df, ["Lone parent: Two or more dependent children"]
)
encoding_households["0 0 >=1 1 0"] = filter_and_sum(
    df, ["Lone parent: All children non-dependent"]
)

encoding_households["1 0 >=0 >=1 >=0"] = filter_and_sum(
    df, ["Other household types: With one dependent child"]
)
encoding_households[">=2 0 >=0 >=1 >=0"] = filter_and_sum(
    df, ["Other household types: With two"]
)
encoding_households["0 >=1 0 0 0"] = filter_and_sum(df, ["All full-time students"])
encoding_households["0 0 0 0 >=2"] = filter_and_sum(
    df, ["Other household types: All aged 65 and over"]
)
encoding_households["0 0 >=0 >=0 >=0"] = filter_and_sum(
    df, ["Other household types: Other"]
)

encoding_households.index.name = "output_area"

np.testing.assert_array_equal(
    encoding_households.sum(axis=1).values, df.sum(axis=1).values
)
# comunal establishments
comunal_df = pd.read_csv(os.path.join(raw_path, "communal_houses.csv"))
comunal_df.set_index(comunal_df["geography"], inplace=True)

all_comunal_df = comunal_df[
    [col for col in comunal_df.columns if "All categories" in col]
]
carehome_df = comunal_df[[col for col in comunal_df.columns if "Care home" in col]]
carehome_df = carehome_df.sum(axis=1)
comunal_not_carehome_df = all_comunal_df[all_comunal_df.columns[0]] - carehome_df

assert (
        comunal_not_carehome_df.sum() + carehome_df.sum()
        == all_comunal_df[all_comunal_df.columns[0]].sum()
)

encoding_households[">=0 >=0 >=0 >=0 >=0"] = comunal_not_carehome_df
encoding_households.to_csv(
    os.path.join(processed_path, "minimum_household_composition.csv")
)
