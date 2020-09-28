from pathlib import Path
import pandas as pd


class RecordReader:
    def __init__(self, results_path=Path("results")):
        self.regional_summary = self.get_run_summary(results_path / "summary.csv")
        self.world_summary = self.regional_summary.drop(columns='region').groupby('time_stamp').sum()

    def get_run_summary(self, summary_path):
        df = pd.read_csv(summary_path)
        df = df.groupby(["time_stamp", "region"], as_index=False).sum()
        df.set_index("time_stamp", inplace=True)
        df.index = pd.to_datetime(df.index)
        return df
