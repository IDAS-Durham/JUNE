import pandas as pd
from june import paths
from datetime import datetime
import os

raw_path = paths.data_path / "time_series/"
processed_path = paths.data_path / "processed/time_series/"

deaths_df = pd.read_csv(raw_path / "March&April_Deaths.csv",
        index_col=0)
deaths_df = deaths_df.rename(columns={'NHS England Region': 'region'})
deaths_df = deaths_df.drop(columns=['Trust','Code'])
n_deaths_region = deaths_df.groupby('region').sum()
n_deaths_region.loc['London'] = n_deaths_region.loc['London'] + n_deaths_region.loc['London ']
n_deaths_region = n_deaths_region.drop('London ')
n_deaths_region = n_deaths_region.T
n_deaths_region.to_csv(processed_path / "n_deaths_region.csv")

estimated_cases_df = pd.read_csv(raw_path / "March_Predicted_Cases.csv",
        index_col=0)
estimated_cases_df = estimated_cases_df.rename(columns={'NHS England Region': 'region'})
estimated_cases_df = estimated_cases_df.drop(columns=['Trust','Code'])
n_cases_region = estimated_cases_df.groupby('region').sum()
n_cases_region.loc['London'] = n_cases_region.loc['London'] + n_cases_region.loc['London ']
n_cases_region = n_cases_region.drop('London ')
n_cases_region = n_cases_region.T
n_cases_region.to_csv(processed_path / "n_cases_region.csv")

