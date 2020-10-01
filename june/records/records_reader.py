from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import pandas as pd
import tables


class RecordReader:
    def __init__(self, results_path=Path("results")):
        self.results_path = Path(results_path)
        self.regional_summary = self.get_regional_summary(self.results_path / "summary.csv")
        self.world_summary = self.get_world_summary()

    def get_regional_summary(self, summary_path):
        df = pd.read_csv(summary_path)
        self.aggregator = {
            col: np.mean if "current" in col else sum for col in df.columns[2:]
        }
        df = df.groupby(["time_stamp", "region"], as_index=False).agg(self.aggregator)
        df.set_index("time_stamp", inplace=True)
        df.index = pd.to_datetime(df.index)
        return df

    def get_world_summary(self):
        return (
            self.regional_summary.drop(columns="region")
            .groupby("time_stamp")
            .agg(self.aggregator)
        )

    def table_to_df(
        self, table_name: str, index: str = "id", fields: Optional[Tuple] = None
    ) -> pd.DataFrame:
        # TODO: include fields to read only certain columns
        with tables.open_file(self.results_path / "june_record.h5", mode="r") as f:
            table = getattr(f.root, table_name)
            df = pd.DataFrame.from_records(table.read(), index=index)
        str_df = df.select_dtypes([np.object])
        for col in str_df:
            df[col] = str_df[col].str.decode("utf-8")
        return df

    def get_geography_df(self,):
        areas_df = self.table_to_df("areas")
        super_areas_df = self.table_to_df("super_areas")
        regions_df = self.table_to_df("regions")

        geography_df = areas_df[["super_area_id", "name"]].merge(
            super_areas_df[["region_id", "name"]],
            how="inner",
            left_on="super_area_id",
            right_index=True,
            suffixes=("_area", "_super_area"),
        )
        geography_df = geography_df.merge(
            regions_df, how="inner", left_on="region_id", right_index=True,
        )
        return geography_df.rename(
            columns={geography_df.index.name: "area_id", "name": "name_region"}
        )

    def get_table_with_extras(
        self, table_name, index, with_people=True, with_geography=True
    ):
        df = self.table_to_df(table_name, index=index)
        if with_people:
            people_df = self.table_to_df("population", index="id")
            df = df.merge(people_df, how="inner", left_index=True, right_index=True)
            if with_geography:
                geography_df = self.get_geography_df()
                df = df.merge(geography_df.drop_duplicates(),
                        left_on="area_id", right_index=True, how='inner')
        return df
