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


seed_df = pd.read_csv(raw_path / "Seeding_March_first_Try.csv", 
        index_col=0)

seed_df = seed_df[['Region', 'N_cases_1_march', 'N_deaths_24_march']]
seed_df.columns = ['region', 'n_cases', 'n_deaths']

n_cases_region = seed_df.groupby('region').sum()

n_cases_region['n_cases'].to_csv(processed_path / "n_cases_region.csv")
n_cases_region['n_deaths'].to_csv(processed_path / "n_deaths_region.csv")
