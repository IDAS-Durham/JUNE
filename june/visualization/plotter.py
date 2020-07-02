import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import timedelta
from itertools import chain

from june.logger.read_logger import ReadLogger
from june.paths import data_path

sa_to_county_filename = (
    data_path / "not_used_in_code/processed/geographical_data/oa_msoa_lad.csv"
)
area_super_area_region_filename = (
    data_path / "input/geography/area_super_area_region.csv"
)
county_shapes_filename = data_path / "input/geography/lad_boundaries.geojson"
super_area_coordinates_filename = (
    data_path / "input/geography/super_area_coordinates.csv"
)
deaths_region_data = data_path / "covid_real_data/n_deaths_region.csv"
cases_region_data = data_path / "covid_real_data/n_cases_region.csv"

mapbox_access_token = "pk.eyJ1IjoiYXN0cm9ieXRlIiwiYSI6ImNrYWwxeHNxZTA3cXMyeG15dGlsbzd1aHAifQ.XvkJbn9mEZ2cuctaX1UwTw"
px.set_mapbox_access_token(mapbox_access_token)

regions_dictionary = {
    "East Of England": ["East of England"],
    "Midlands": ["East Midlands", "West Midlands"],
    "London": ["London"],
    "South West": ["South West"],
    "South East": ["South East"],
    "North East And Yorkshire": ["North East", "Yorkshire and The Humber"],
    "Wales": ["Wales"],
}


class DashPlotter:
    def __init__(self, results_folder_path: str):
        self.logger_reader = ReadLogger(results_folder_path)
        with open(county_shapes_filename, "r") as f:
            self.county_shapes = json.load(f)
        self.super_area_coordinates = pd.read_csv(super_area_coordinates_filename)
        self.world_data = self.logger_reader.world_summary()
        self.area_data = self.logger_reader.super_area_summary()
        self.area_super_area_region = pd.read_csv(area_super_area_region_filename)
        self.area_super_area_region.set_index("super_area", inplace=True)
        self.county_data = self.group_data_by_counties(self.area_data.copy())
        self.county_data['date'] = self.county_data.index.date
        self.hospital_characteristics = (
            self.logger_reader.load_hospital_characteristics()
        )
        self.hospital_data = self.logger_reader.load_hospital_capacity()
        self.hospital_data["time_stamp"] = pd.to_datetime(
            self.hospital_data["time_stamp"]
        )
        self.hospital_data.set_index("time_stamp", inplace=True)
        self.deaths_region_data = pd.read_csv(deaths_region_data, index_col=0)
        self.deaths_region_data.index = pd.to_datetime(self.deaths_region_data.index)
        self.cases_region_data = pd.read_csv(cases_region_data, index_col=0)
        self.cases_region_data.index = pd.to_datetime(self.cases_region_data.index)
        self.regions = self.deaths_region_data.columns
        self.ages_data = self.logger_reader.age_summary(
            [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        )

    def group_data_by_counties(self, area_df: pd.DataFrame):
        area_df.reset_index(inplace=True)
        sa_to_county_df = pd.read_csv(sa_to_county_filename)
        data = area_df.reset_index()
        data = pd.merge(
            area_df,
            sa_to_county_df[["MSOA11CD", "LAD17NM"]],
            left_on="super_area",
            right_on="MSOA11CD",
        )
        data.drop(columns=["MSOA11CD", "super_area"], inplace=True)
        data.drop_duplicates(inplace=True)
        data = data.groupby(["time_stamp", "LAD17NM"]).sum().reset_index()
        data.set_index("time_stamp", inplace=True)
        return data

    def generate_infection_map_by_county(self, day_number):
        date = self.county_data['date'][0] + timedelta(days=day_number)
        data = self.county_data[self.county_data['date'] == date]
        fig = px.choropleth(
            data,
            geojson=self.county_shapes,
            color="infected",
            locations="LAD17NM",
            featureidkey="properties.lad17nm",
            projection="mercator",
            hover_data=[
                "infected",
                "recovered",
                "hospitalised",
                "intensive_care",
                "dead",
            ],
            range_color=(0, self.max_infected),
        )
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        return fig

    def generate_animated_general_map(self):
        data = self.area_data.reset_index()
        data["time_stamp"] = data["time_stamp"].dt.day
        data = data.groupby(["time_stamp", "super_area"]).sum()
        data.reset_index(inplace=True)
        data = pd.merge(
            data, self.super_area_coordinates, left_on="super_area", right_on="super_area"
        )
        fig = px.scatter_mapbox(
            data,
            lat="latitude",
            lon="longitude",
            size="infected",
            color_continuous_scale=px.colors.cyclical.IceFire,
            size_max=15,
            zoom=10,
            animation_frame="time_stamp",
            height=800,
            width=2000,
        )
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        return fig

    def generate_county_infection_curves(self, county, axis_type="Linear"):
        data = self.county_data[self.county_data["LAD17NM"] == county]
        data = data.groupby(by=data.index.date).first()
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=data.index.values, y=data["infected"].values, name="infected")
        )
        fig.add_trace(
            go.Scatter(
                x=data.index.values, y=data["hospitalised"].values, name="hospitalised"
            )
        )
        fig.add_trace(
            go.Scatter(
                x=data.index.values,
                y=data["intensive_care"].values,
                name="intensive care",
            )
        )
        fig.add_trace(
            go.Scatter(x=data.index.values, y=data["dead"].values, name="dead")
        )
        fig.add_trace(
            go.Scatter(
                x=data.index.values, y=data["recovered"].values, name="recovered"
            )
        )
        fig.update_layout(template="simple_white", title="Infection curves by county")
        if axis_type == "Log":
            fig.update_layout(yaxis_type="log")
        return fig

    def generate_general_infection_curves(self, axis_type="Linear"):
        data = self.world_data
        data = data.groupby(by=data.index.date).first()
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=data.index.values, y=data["infected"].values, name="infected")
        )
        fig.add_trace(
            go.Scatter(
                x=data.index.values, y=data["hospitalised"].values, name="hospitalised"
            )
        )
        fig.add_trace(
            go.Scatter(
                x=data.index.values,
                y=data["intensive_care"].values,
                name="intensive care",
            )
        )
        fig.add_trace(
            go.Scatter(x=data.index.values, y=data["dead"].values, name="dead")
        )
        fig.add_trace(
            go.Scatter(
                x=data.index.values, y=data["recovered"].values, name="recovered"
            )
        )
        fig.update_layout(template="simple_white", title="world infection curves")
        if axis_type == "Log":
            fig.update_layout(yaxis_type="log")
        return fig

    def generate_hospital_map(self, day_number):
        date = self.hospital_data.index[0] + timedelta(days=day_number)
        hospital_data = self.hospital_data.loc[date]
        lon = self.hospital_characteristics["longitude"].values
        lat = self.hospital_characteristics["latitude"].values
        text_list = []
        for n_patients, n_patients_icu, n_beds, n_icu_beds in zip(
            hospital_data["n_patients"].values,
            hospital_data["n_patients_icu"].values,
            self.hospital_characteristics["n_beds"].values,
            self.hospital_characteristics["n_icu_beds"].values,
        ):
            text = f"Occupied {n_patients} beds of {n_beds}. \nOccupied {n_patients_icu} ICU beds of {n_icu_beds}"
            text_list.append(text)
        fig = go.Figure(
            go.Scattermapbox(
                mode="markers",
                lon=lon,
                lat=lat,
                marker={"size": 20, "symbol": ["marker"] * len(lat),},
                text=text_list,
                textposition="bottom right",
            )
        )
        fig.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            width=2000,
            height=800,
            mapbox={
                "accesstoken": mapbox_access_token,
                "style": "light",
                "zoom": 10,
                "center": {"lat": np.mean(lat), "lon": np.mean(lon)},
            },
        )
        return fig

    def generate_infections_by_age(self):
        data = self.ages_data.reset_index().set_index("age_range")
        fig = go.Figure()
        for age_range in data.index.unique():
            toplot = data.loc[age_range]
            fig.add_trace(
                go.Scatter(x=toplot["time_stamp"], y=toplot["infected"], name=age_range)
            )
        fig.update_layout(template="simple_white")
        return fig

    def generate_r0(self):
        r_df = self.logger_reader.get_r()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=r_df.index, y=r_df["value"].values, name="R0"))
        fig.add_trace(
            go.Scatter(x=[r_df.index[0], r_df.index[-1]], y=[1, 1], name="unity")
        )
        fig.update_layout(template="simple_white", title="R0")
        return fig

    def generate_place_of_infection(self):
        start_date = self.ages_data.index[0].strftime("%Y/%m/%d")
        end_date = self.ages_data.index[-1].strftime("%Y/%m/%d")
        places = self.logger_reader.get_locations_infections(
            start_date=start_date, end_date=end_date,
        )
        places = places["percentage_infections"].sort_values()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=places.index, y=places.values))
        fig.update_layout(template="simple_white", title="Places of infection")
        return fig

    def generate_symptom_trajectories(self):
        random_trajectories = self.logger_reader.draw_symptom_trajectories(
            window_length=100, n_people=5
        )
        fig = go.Figure()
        for df_person in random_trajectories:
            fig.add_trace(go.Scatter(x=df_person.index, y=df_person["symptoms"]))
        symptoms_names = [
            "recovered",
            "healthy",
            "exposed",
            "asymptomatic",
            "influenza",
            "pneumonia",
            "hospitalised",
            "intensive_care",
            "dead",
        ]
        fig.update_layout(
            template="simple_white",
            title="Symptoms trajectories",
            yaxis=dict(
                tickmode="array", tickvals=np.arange(-3, 6), ticktext=symptoms_names,
            ),
            xaxis_title="Date",
            yaxis_title="Symptoms",
        )
        return fig

    def generate_data_comparison(self, region):
        region_names = regions_dictionary[region]
        deaths_real_data = self.deaths_region_data[region]
        super_areas = self.area_super_area_region[
            self.area_super_area_region.region.isin(region_names)
        ].index.values
        june_data = self.area_data.loc[self.area_data.super_area.isin(super_areas)]
        june_data = june_data.groupby(june_data.index).sum()
        fig = make_subplots(rows=1, cols=1)
        fig.add_trace(
            go.Scatter(
                x=deaths_real_data.index.date,
                y=deaths_real_data.values.cumsum(),
                name="data",
                line=dict(color="rgb(231,107,243)", width=4, dash="dash"),
            ),
            row=1,
            col=1,
        )
        if len(june_data) != 0:
            fig.add_trace(
                go.Scatter(
                    x=june_data.index.date,
                    y=june_data["dead"].values.cumsum(),
                    name="prediction",
                    line=dict(color="royalblue", width=4),
                ),
                row=1,
                col=1,
            )
        fig.update_layout(template="simple_white",)
        fig.update_xaxes(title_text="Date", row=1, col=1)
        fig.update_yaxes(title_text="Deaths", row=1, col=1)
        return fig

    @property
    def max_infected(self):
        return self.county_data["infected"].max()

    @property
    def dates(self):
        return self.county_data.index.date

    @property
    def days(self):
        dates = np.unique(self.dates)
        days = [date.day for date in dates]
        days_rebase =np.arange(len(days))
        return days_rebase
