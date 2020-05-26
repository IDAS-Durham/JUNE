import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import json
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from june.visualization.plotter import DashPlotter
import sys

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

available_indicators = [
    "Infection curves",
]

dash_plotter = DashPlotter(sys.argv[1])

app.layout = html.Div(
    [
        dcc.Tabs(
            id="tabs-example",
            value="tab-1",
            children=[
                dcc.Tab(label="County data", value="tab-1"),
                dcc.Tab(label="Animated global map", value="tab-2"),
                dcc.Tab(label="Hospitals", value="tab-3"),
            ],
        ),
        html.Div(id="tabs-example-content"),
    ]
)

@app.callback(
    dash.dependencies.Output("tabs-example-content", "children"),
    [dash.dependencies.Input("tabs-example", "value")],
)
def render_content(tab):
    if tab == "tab-1":
        content = html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                dcc.Dropdown(
                                    id="crossfilter-yaxis-column",
                                    options=[
                                        {"label": i, "value": i}
                                        for i in available_indicators
                                    ],
                                    value="Infection curves",
                                ),
                                dcc.RadioItems(
                                    id="crossfilter-yaxis-type",
                                    options=[
                                        {"label": i, "value": i}
                                        for i in ["Linear", "Log"]
                                    ],
                                    value="Linear",
                                    labelStyle={"display": "inline-block"},
                                ),
                            ],
                            style={
                                "width": "49%",
                                "float": "right",
                                "display": "inline-block",
                            },
                        ),
                    ],
                    style={
                        "borderBottom": "thin lightgrey solid",
                        "backgroundColor": "rgb(250, 250, 250)",
                        "padding": "10px 5px",
                    },
                ),
                html.Div(
                    dcc.Graph(id="y-time-series"),
                    style={"display": "inline-block", "width": "100%"},
                ),
                html.Div(
                    [
                        dcc.Graph(
                            figure=dash_plotter.generate_infection_map_by_county(
                                day_number=0
                            ),
                            id="crossfilter-indicator-map",
                        )
                    ],
                    style={
                        "width": "90%",
                        "display": "inline-block",
                        "padding": "0 20",
                    },
                ),
                html.Div(
                    dcc.Slider(
                        id="crossfilter-time--slider",
                        min=0,
                        max=len(dash_plotter.day_timestamps_marks) - 1,
                        value=0,
                        marks={
                            i: str(day)
                            for i, day in enumerate(dash_plotter.day_timestamps_marks)
                        },
                        step=None,
                    ),
                    style={"width": "49%", "padding": "0px 20px 20px 20px"},
                ),
                html.Div(
                    dcc.Graph(figure=dash_plotter.generate_infections_by_age()),
                    style={"display": "inline-block", "width": "100%"},
                ),
                html.Div(
                    dcc.Graph(figure=dash_plotter.generate_general_infection_curves()),
                    style={"display": "inline-block", "width": "100%"},
                ),
            ],
            style={"columnCount": 2},
        )
        return content
    elif tab == "tab-2":
        return html.Div(
            [
                html.H3("Animated map"),
                html.Div(
                    dcc.Graph(figure=dash_plotter.generate_animated_general_map()),
                    style = {"display": "inline-block", "height" : "400%", "width" : "100%"},
                ),
            ],
            style = {"display": "inline-block", "height" : "400%", "width" : "100%"},
        )
    elif tab == "tab-3":
        return html.Div(
            [
                html.Div(
                    dcc.Graph(figure=dash_plotter.generate_hospital_map()),
                    style = {"display": "inline-block", "height" : "400%", "width" : "100%"},
                ),
            ],
            style = {"display": "inline-block", "height" : "400%", "width" : "100%"},
        )


@app.callback(
    dash.dependencies.Output("crossfilter-indicator-map", "figure"),
    [dash.dependencies.Input("crossfilter-time--slider", "value"),],
)
def update_map(day_number):
    return dash_plotter.generate_infection_map_by_county(day_number=day_number)


@app.callback(
    dash.dependencies.Output("y-time-series", "figure"),
    [
        dash.dependencies.Input("crossfilter-indicator-map", "hoverData"),
        dash.dependencies.Input("crossfilter-yaxis-type", "value"),
    ],
)
def update_infection_plot(hoverData, axis_type):
    county_name = hoverData["points"][0]["location"]
    return dash_plotter.generate_county_infection_curves(county_name, axis_type)


if __name__ == "__main__":
    app.run_server(debug=False)
