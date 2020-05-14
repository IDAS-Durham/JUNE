import pandas as pd

from june import paths

raw_path = f"{paths.data_path}/census_data/output_area/"
processed_path = f"{paths.data_path}/processed/census_data/output_area/"

household_composition_people = pd.read_csv(
    raw_path / "household_composition_people.csv"
)

household_composition_people.set_index("geography", inplace=True)
household_composition_people = household_composition_people.filter(
    regex="All full-time students"
)

household_composition_people = household_composition_people.rename(
    {household_composition_people.columns[0]: "n_students"}, axis=1
)

household_composition_people.index.name = "output_area"

print(household_composition_people)
household_composition_people.to_csv(processed_path / "n_students.csv")
