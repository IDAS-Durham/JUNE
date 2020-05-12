import pandas as pd
from pathlib import Path
import os

raw_path = (
    Path(os.path.abspath(__file__)).parent.parent.parent.parent
    / "data/seed/"
)
processed_path = (
    Path(os.path.abspath(__file__)).parent.parent.parent.parent
    / "data/processed/seed/"
)


seed_df = pd.read_csv(raw_path / "Seeding_March_first_Try.csv", )
print(seed_df)

n_cases_region = seed_df.groupby('Region').sum()

n_cases_region['N_cases_1_march'].to_csv(processed_path / "n_cases_region.csv")
n_cases_region['N_deaths_24_march'].to_csv(processed_path / "n_deaths_region.csv")
