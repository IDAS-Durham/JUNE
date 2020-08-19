import pandas as pd
from june import paths

raw_path = paths.data_path / "time_series/"
processed_path = paths.data_path / "processed/time_series/"

confirmed_cases_df = pd.read_csv(raw_path / "coronavirus-cases_latest.csv",
        index_col=0)
mask = confirmed_cases_df['Area type'] == 'Region'
confirmed_cases_df = confirmed_cases_df[mask]
confirmed_cases_df = confirmed_cases_df[['Specimen date','Daily lab-confirmed cases']]
confirmed_cases_df.reset_index(inplace=True)
confirmed_cases_df = confirmed_cases_df.set_index('Specimen date')
confirmed_cases_df = confirmed_cases_df.pivot(columns='Area name', values='Daily lab-confirmed cases')
confirmed_cases_df.to_csv(processed_path / "n_confirmed_cases.csv")


