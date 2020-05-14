import pandas as pd

from june import paths

raw_path = f"{paths.data_path}/census_data/output_area/"
processed_path = f"{paths.data_path}/processed/census_data/output_area/"

comunal = pd.read_csv(raw_path / "communal_people.csv")

comunal.set_index("geography", inplace=True)
all_comunal_df = comunal[[col for col in comunal.columns if "All categories" in col]]
carehome_df = comunal[[col for col in comunal.columns if "Care home" in col]]
carehome_df = carehome_df.sum(axis=1)
comunal = all_comunal_df[all_comunal_df.columns[0]] - carehome_df

assert (
        comunal.sum() + carehome_df.sum() == all_comunal_df[all_comunal_df.columns[0]].sum()
)

# comunal = comunal.rename(
#        {comunal.columns[0]: 'n_people_in_communal'},
#        axis=1
#        )

comunal.index.name = "output_area"

assert len(comunal) == 181408
comunal.to_csv(processed_path / "n_people_in_communal.csv")
