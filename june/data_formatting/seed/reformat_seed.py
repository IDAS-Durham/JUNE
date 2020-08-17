import pandas as pd
from june import paths

raw_path = paths.data_path / "seed/"
processed_path = paths.data_path / "processed/seed/"

seed_df = pd.read_csv(raw_path / "Seeding_March_10days.csv", 
        index_col=0)

seed_df = seed_df.drop(columns=['Trust','Code'])
seed_df = seed_df.rename(columns={'NHS England Region': 'region'})
n_cases_region = seed_df.groupby('region').sum()
n_cases_region.loc['London'] = n_cases_region.loc['London'] + n_cases_region.loc['London ']
n_cases_region = n_cases_region.drop('London ')

n_cases_region.to_csv(processed_path / "n_cases_region.csv")
