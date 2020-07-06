import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import timedelta, datetime
from itertools import chain

from june.logger.read_logger import ReadLogger
from june.paths import data_path

import dash_html_components as html

super_area_coordinates_filename = (
    data_path / "input/geography/super_area_coordinates.csv"
)

mapbox_access_token = "pk.eyJ1IjoiYXN0cm9ieXRlIiwiYSI6ImNrYWwxeHNxZTA3cXMyeG15dGlsbzd1aHAifQ.XvkJbn9mEZ2cuctaX1UwTw"
px.set_mapbox_access_token(mapbox_access_token)

class DashPlotter:
    def __init__(self, results_folder_path: str):
        print ('Loading logger')
        self.logger_reader = ReadLogger(results_folder_path)
        print ('Logger loaded')
        self.super_area_coordinates = pd.read_csv(super_area_coordinates_filename)
        print ('Loading area data')
        self.area_data = pd.read_csv(results_folder_path + '/super_area_summary_clean.csv')
        self.area_data['date'] = pd.to_datetime(self.area_data['date'], infer_datetime_format=True)
        print ('Area data loaded')

        print ('Loading hospital data')
        self.hospital_characteristics = (
            self.logger_reader.load_hospital_characteristics()
        )
        self.hospital_data = self.logger_reader.load_hospital_capacity()
        self.hospital_data["time_stamp"] = pd.to_datetime(
            self.hospital_data["time_stamp"]
        )
        self.hospital_data.set_index("time_stamp", inplace=True)
        self.hospital_data['date'] = self.hospital_data.index.date
        self.hospital_data = self.hospital_data.reset_index()
        dates = np.unique(self.hospital_data['date'])
        ids = np.unique(self.hospital_data['id'])
        indices = []
        for h_id in ids:
            hospital_specific_data = self.hospital_data[self.hospital_data['id'] == h_id]
            for date in dates:
                indices.append(hospital_specific_data[hospital_specific_data['date'] == date].index[-1])
        self.hospital_data = self.hospital_data.loc[indices].reset_index()
        print ('Hospital data has length = {}'.format(len(self.hospital_data)))
        print ('Hospital data loaded')

        print ('Loading age data')
        self.ages_data = self.logger_reader.age_summary(
            [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        )
        print ('Age data loaded')


    def generate_infections_by_age(self, axis_type):
        data = self.ages_data.reset_index().set_index("age_range")
        fig = go.Figure()
        for age_range in data.index.unique():
            toplot = data.loc[age_range]
            fig.add_trace(
                go.Scatter(x=toplot["time_stamp"], y=toplot["infected"], name=age_range)
            )
        fig.update_layout(paper_bgcolor="#1f2630", plot_bgcolor="#1f2630", \
                  font = {"color": "#2cfec1"},\
                  title = {"font": {"color": "#2cfec1"}},\
                  xaxis = {"tickfont": {"color":"#2cfec1"}, "gridcolor": "#5b5b5b"},\
                  yaxis = {"tickfont": {"color":"#2cfec1"}, "gridcolor": "#5b5b5b"})
        if axis_type == "Log":
                fig.update_layout(yaxis_type="log")
        return fig

    def generate_r0(self):
        r_df = self.logger_reader.get_r()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=r_df.index, y=r_df["value"].values, name="R0"))
        fig.add_trace(
            go.Scatter(x=[r_df.index[0], r_df.index[-1]], y=[1, 1], name="unity")
        )
        fig.update_layout(paper_bgcolor="#1f2630", plot_bgcolor="#1f2630", \
                  font = {"color": "#2cfec1"},\
                  title = {"font": {"color": "#2cfec1"}},\
                  xaxis = {"tickfont": {"color":"#2cfec1"}, "gridcolor": "#5b5b5b"},\
                  yaxis = {"tickfont": {"color":"#2cfec1"}, "gridcolor": "#5b5b5b"})
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
        fig.update_layout(paper_bgcolor="#1f2630", plot_bgcolor="#1f2630", \
                  font = {"color": "#2cfec1"},\
                  title = {"font": {"color": "#2cfec1"}},\
                  xaxis = {"tickfont": {"color":"#2cfec1"}, "gridcolor": "#5b5b5b"},\
                  yaxis = {"tickfont": {"color":"#2cfec1"}, "gridcolor": "#5b5b5b"})
        return fig
    

    def generate_animated_map_callback(self, day_number):
        data = self.area_data
        data = data.groupby(["date", "super_area"]).sum()
        data.reset_index(inplace=True)
        data = pd.merge(
            data, self.super_area_coordinates, left_on="super_area", right_on="super_area"
        )
        max_infected = np.max(data["infected"])
        data["infected_scaled"] = np.array(data["infected"])/max_infected
        test_date = data['date'][0] + timedelta(days=day_number)
        data_day = data[data['date'] == test_date]
        fig = px.scatter_mapbox(
            data_day,
            lat="latitude",
            lon="longitude",
            size="infected",
            color_continuous_scale=px.colors.cyclical.IceFire,
            size_max=15,
            zoom=5,
        )
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        return fig

    def running_mean(self, x, N):
        cumsum = np.cumsum(np.insert(x, 0, 0)) 
        return (cumsum[N:] - cumsum[:-N]) / float(N)

    def get_color(self, a):
        if a == 0:
            return "white"
        elif a < 0:
            return "#45df7e"
        else:
            return "#da5657"

    def get_infection_change(self, selectedData, day_number):

        area_data = pd.merge(self.area_data, self.super_area_coordinates, left_on="super_area", right_on="super_area")

        if selectedData is None:
            selected_super_areas = np.unique(area_data['super_area'])
        else:
            super_areas = []
            for point in selectedData['points']:
                super_areas.append(list(area_data['super_area'][area_data['latitude'] == point['lat']])[0])
            selected_super_areas = np.unique(super_areas)
        
        area_data = area_data[area_data['super_area'].isin(selected_super_areas)]

        area_data_grouped = area_data.groupby(['date']).sum().reset_index()

        infected = list(area_data_grouped['infected'])
        
        # Calculate 7-day rolling average
        base = np.zeros(6)
        infected_rm = self.running_mean(infected, 7)
        infected_rm = np.concatenate((base,infected_rm))


        change_2day = 0
        if day_number == 0 or day_number == 1 or infected_rm[day_number-2] == 0.:
            pass
        else:
            change_2day = int(((infected_rm[day_number] - infected_rm[day_number-2])/infected_rm[day_number-2])*100)

        return [
            html.P(
                id="geographical-infection-growth-trends-value",
                children = [
                    "{}%".format(
                        change_2day
                    ),
                ],
                style={"color": self.get_color(change_2day), "font-size": "300%"},
            ),
        ]

    def get_death_change(self, selectedData, day_number):

        area_data = pd.merge(self.area_data, self.super_area_coordinates, left_on="super_area", right_on="super_area")

        if selectedData is None:
            selected_super_areas = np.unique(area_data['super_area'])
        else:
            super_areas = []
            for point in selectedData['points']:
                super_areas.append(list(area_data['super_area'][area_data['latitude'] == point['lat']])[0])
            selected_super_areas = np.unique(super_areas)
        
        area_data = area_data[area_data['super_area'].isin(selected_super_areas)]

        area_data_grouped = area_data.groupby(['date']).sum().reset_index()

        dead = list(area_data_grouped['dead'])
        new_dead = [0]
        for idx, row in area_data_grouped.iterrows():
            if idx == 0:
                pass
            else:
                new_dead.append(row['dead'] - dead[idx-1])

        # Calculate 7-day rolling average
        base = np.zeros(6)
        dead_rm = self.running_mean(new_dead, 7)
        dead_rm = np.concatenate((base,dead_rm))

        if day_number == 0 or day_number == 1:
            return "{}%".format(0)
        else:
            change_2day = int(((dead_rm[day_number] - dead_rm[day_number-2])/dead_rm[day_number-2])*100)
            return "{}%".format(change_2day)


    def generate_infection_curves_callback(self, selectedData, chart_type, axis_type):

        area_data = pd.merge(self.area_data, self.super_area_coordinates, left_on="super_area", right_on="super_area")

        if selectedData is None:
            selected_super_areas = np.unique(area_data['super_area'])
        else:
            super_areas = []
            for point in selectedData['points']:
                super_areas.append(list(area_data['super_area'][area_data['latitude'] == point['lat']])[0])
            selected_super_areas = np.unique(super_areas)
        
        area_data = area_data[area_data['super_area'].isin(selected_super_areas)]

        area_data_grouped = area_data.groupby(['date']).sum().reset_index()

        if chart_type == 'show_SIR_curves':

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(x=area_data_grouped['date'], y=area_data_grouped['infected'], name="infected")
            )
            fig.add_trace(
                go.Scatter(x=area_data_grouped['date'], y=area_data_grouped['susceptible'], name="susceptible")
            )
            fig.add_trace(
                go.Scatter(x=area_data_grouped['date'], y=area_data_grouped['recovered'], name="recovered")
            )
            fig.update_layout(paper_bgcolor="#1f2630", plot_bgcolor="#1f2630", \
                  font = {"color": "#2cfec1"},\
                  title = {"font": {"color": "#2cfec1"}},\
                  xaxis = {"tickfont": {"color":"#2cfec1"}, "gridcolor": "#5b5b5b"},\
                  yaxis = {"tickfont": {"color":"#2cfec1"}, "gridcolor": "#5b5b5b"})
            if axis_type == "Log":
                fig.update_layout(yaxis_type="log")
            return fig


    def generate_hospital_map_callback(self, day_number):
        date = self.hospital_data['date'][0] + timedelta(days=day_number)
        hospital_data = self.hospital_data[self.hospital_data['date'] == date]
        lon = self.hospital_characteristics["longitude"].values
        lat = self.hospital_characteristics["latitude"].values
        text_list = []
        for n_patients, n_patients_icu, n_beds, n_icu_beds in zip(
            hospital_data["n_patients"].values,
            hospital_data["n_patients_icu"].values,
            self.hospital_characteristics["n_beds"].values,
            self.hospital_characteristics["n_icu_beds"].values,
        ):
            text = "Occupied {} beds of {}. Occupied {} ICU beds of {}".format(n_patients, n_beds, n_patients_icu, n_icu_beds)
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
            mapbox={
                "accesstoken": mapbox_access_token,
                "style": "light",
                "zoom": 10,
                "center": {"lat": np.mean(lat), "lon": np.mean(lon)},
            },
        )
        return fig

    def generate_hospital_curves_callback(self, selectedData, chart_type, axis_type):

        hospital_data = self.hospital_data
        hospital_characteristics = self.hospital_characteristics.reset_index()

        if selectedData is None:
            selected_hospitals = np.unique(hospital_data['id'])
        else:
            hospitals = []
            for point in selectedData['points']:
                hospitals.append(list(hospital_characteristics['index'][hospital_characteristics['latitude'] == point['lat']])[0])
            selected_hospitals = np.unique(hospitals)
        
        hospital_data = hospital_data[hospital_data['id'].isin(selected_hospitals)]

        dates = np.unique(hospital_data['date'])
        patients = []
        icu_patients = []
        for date in dates:
            patients.append(hospital_data['n_patients'][hospital_data['date'] == date].sum())
            icu_patients.append(hospital_data['n_patients_icu'][hospital_data['date'] == date].sum())

        if chart_type == 'show_hospitalisation_curves':

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(x=dates, y=np.ones(len(dates))*hospital_characteristics['n_beds'].sum(), name="total bed capacity")
            )
            fig.add_trace(
                go.Scatter(x=dates, y=patients, name="patients")
            )
            fig.add_trace(
                go.Scatter(x=dates, y=np.ones(len(dates))*hospital_characteristics['n_icu_beds'].sum(), name="ICU bed capacity")
            )
            fig.add_trace(
                go.Scatter(x=dates, y=icu_patients, name="ICU admittance")
            )
            fig.update_layout(paper_bgcolor="#1f2630", plot_bgcolor="#1f2630", \
                  font = {"color": "#2cfec1"},\
                  title = {"font": {"color": "#2cfec1"}},\
                  xaxis = {"tickfont": {"color":"#2cfec1"}, "gridcolor": "#5b5b5b"},\
                  yaxis = {"tickfont": {"color":"#2cfec1"}, "gridcolor": "#5b5b5b"})
            if axis_type == "Log":
                fig.update_layout(yaxis_type="log")
            return fig

    @property
    def dates(self):
        return self.area_data['date']

    @property
    def days(self):
        dates = np.unique(self.dates)
        if len(dates) <= 40:
            days = np.arange(0, len(dates))
        else:
            days = np.arange(0, len(dates), 3)
            dates = dates[days]

        dates_reformat = []
        for date in dates:
            dates_reformat.append(datetime.utcfromtimestamp(date.tolist()/1e9).strftime("%d/%m"))
        return dates_reformat
        
    
