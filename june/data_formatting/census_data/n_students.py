import pandas as pd
import numpy as np
from pathlib import Path
import os

raw_path = (
    Path(os.path.abspath(__file__)).parent.parent.parent.parent
    / "data/census_data/output_area/"
)
processed_path = (
    Path(os.path.abspath(__file__)).parent.parent.parent.parent
    / "data/processed/census_data/output_area/"
)

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
