import pandas as pd

from june import paths

raw_path = f"{paths.data_path}/census_data/output_area/"
processed_path = f"{paths.data_path}/processed/census_data/output_area/"

carehome_df = pd.read_csv(raw_path / "communal_people.csv")
carehome_df.set_index(carehome_df["geography"], inplace=True)

carehome_df = carehome_df[[col for col in carehome_df.columns if "Care home" in col]]
all_care_homes = carehome_df.sum(axis=1)
print(all_care_homes)
assert len(all_care_homes) == 181408
all_care_homes.to_csv(processed_path / "carehomes.csv")
