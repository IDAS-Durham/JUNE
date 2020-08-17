import pandas as pd
from june import paths

raw_path = paths.data_path / "time_series/"
processed_path = paths.data_path / "processed/time_series/"

hosp_df = pd.read_csv(raw_path / "COVID_output_pivot_v3.csv", sep=",", skiprows=1)

hosp_df.set_index("ReportingPeriod", inplace=True)
hosp_df.index = pd.to_datetime(hosp_df.index)
hosp_df["covid_admissions"] = hosp_df[
    ["SIT008_Total", "SIT009_Total", "SIT009_Suspected"]
].sum(axis=1)
hosp_df = hosp_df.groupby([hosp_df.index, "Region_Name"]).sum()
hosp_df = hosp_df[["covid_admissions"]].reset_index()
hosp_df = hosp_df.pivot(
    index="ReportingPeriod", columns="Region_Name", values="covid_admissions"
)
hosp_df.to_csv(processed_path / "hospital_admissions_region.csv")
