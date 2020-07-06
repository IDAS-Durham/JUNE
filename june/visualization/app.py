import os
import pathlib
import re

import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
from dash.dependencies import Input, Output, State
import cufflinks as cf

import json
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from june.visualization.plotter_clean import DashPlotter
import sys

dash_plotter = DashPlotter(sys.argv[1])

# Initialize app

app = dash.Dash(
    __name__,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
)
server = app.server

# Load data

APP_PATH = str(pathlib.Path(__file__).parent.resolve())

DEFAULT_COLORSCALE = [
    "#f2fffb",
    "#bbffeb",
    "#98ffe0",
    "#79ffd6",
    "#6df0c8",
    "#69e7c0",
    "#59dab2",
    "#45d0a5",
    "#31c194",
    "#2bb489",
    "#25a27b",
    "#1e906d",
    "#188463",
    "#157658",
    "#11684d",
    "#10523e",
]

DEFAULT_OPACITY = 0.8

mapbox_access_token = "pk.eyJ1IjoicGxvdGx5bWFwYm94IiwiYSI6ImNrOWJqb2F4djBnMjEzbG50amg0dnJieG4ifQ.Zme1-Uzoi75IaFbieBDl3A"
mapbox_style = "mapbox://styles/plotlymapbox/cjvprkf3t1kns1cqjxuxmwixz"

tabs_styles = {
    'height': '44px'
}
tab_style = {
    'borderBottom': '1px solid #d6d6d6',
    'padding': '6px',
    'backgroundColor': "#252e3f",
}

tab_selected_style = {
    'borderTop': '1px solid #d6d6d6',
    'borderBottom': '1px solid #d6d6d6',
    'backgroundColor': "#252e3f",
    'color': 'white',
    'padding': '6px'
}

# App layout

tab1 = html.Div(
    id="root-tab1",
    children=[
        html.Div(
            id="header-tab1",
            children=[
                html.H4(children="Simulated UK COVID-19 Summary Statistics"),
                html.P(
                    id="description-tab1",
                    children="Summary statistics of JUNE simualtion",
                ),
            ],
        ),
        html.Div(
            id="app-container-tab1",
            children=[
                html.Div(
                    id="graph-container-tab1-col1",
                    children=[
                        html.P(id="chart-selector-tab1-world-all", children="World Infection Curves", style={'padding':'10px'}),
                        dcc.Graph(
                            figure=dash_plotter.generate_infection_curves_callback(
                                selectedData=None, chart_type='show_SIR_curves', axis_type="Log"
                            ),
                            id="world-infection",
                        ),
                        html.P(id="chart-selector-tab1-world-age", children="Age Infection Curves", style={'padding':'10px'}),
                        dcc.Graph(
                            figure=dash_plotter.generate_infections_by_age(
                            ),
                            id="world-infection-age",
                        ),
                    ],
                ),
                html.Div(
                    id="graph-container-tab1-col2",
                    children=[
                        html.P(id="chart-selector-tab1-world-where", children="Infection locations", style={'padding':'10px'}),
                        dcc.Graph(
                            figure=dash_plotter.generate_place_of_infection(),
                            id="world-infection-where",
                        ),
                        html.P(id="chart-selector-tab1-world-r0", children="Reproduction number", style={'padding':'10px'}),
                        dcc.Graph(
                            figure=dash_plotter.generate_r0(
                            ),
                            id="world-infection-r0",
                        ),
                    ],
                ),
            ],
        ),
    ],
)

tab2 = html.Div(
    id="root-tab2",
    children=[
        html.Div(
            id="header-tab2",
            children=[
                #html.Img(id="logo", src=app.get_asset_url("IDAS.png")),
                html.H4(children="Geographical statistics"),
                html.P(
                    id="description-tab2",
                    children="Infection statistics broken down by geographical regions over time",
                ),
            ],
        ),
        html.Div(
            id="app-container",
            children=[
                html.Div(
                    id="left-column",
                    children=[
                        html.Div(
                            id="slider-container",
                            children=[
                                html.P(
                                    id="slider-text",
                                    children="Drag the slider to change day after start of simualtion:",
                                    style={'padding':'10px'},
                                ),
                                dcc.Slider(
                                    id="day-slider",
                                    min=0,
                                    max=len(dash_plotter.days) - 1,
                                    value=0,
                                    marks={i: str(day) for i, day in enumerate(dash_plotter.days)}
                                ),
                            ],
                        ),
                        html.Div(
                            id="heatmap-container",
                            children=[
                                html.P(
                                    "Heatmap of infections at day: {0}".format(
                                        0
                                    ),
                                    style={'padding':'10px'},
                                    id="infected-map-title",
                                ),
                                dcc.Graph(
                                    figure=dash_plotter.generate_animated_map_callback(
                                        day_number=0
                                    ),
                                    id="infected-map",
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    id="graph-container-tab2",
                    children=[
                        html.P(id="chart-selector-tab2", children="Select chart:", style={'padding':'10px'}),
                        dcc.Dropdown(
                            options=[
                                {
                                    "label": "Infection curves",
                                    "value": "show_SIR_curves",
                                }
                            ],
                            value="show_SIR_curves",
                            id="chart-dropdown",
                        ),

                        dcc.RadioItems(
                            id='crossfilter-yaxis-type',
                            options=[
                                {"label": i, "value": i}
                                for i in ["Linear", "Log"]
                            ],
                            value="Linear",
                        ),
                        
                        dcc.Graph(
                            figure=dash_plotter.generate_infection_curves_callback(
                                selectedData=None, chart_type='show_SIR_curves', axis_type="Log"
                            ),
                            id="selected-data",
                        ),
                    ],
                ),
            ],
        ),
    ],
)

tab3 = html.Div(
    id="root-tab3",
    children=[
        html.Div(
            id="header-tab3",
            children=[
                html.H4(children="Hospitalisation statistics"),
                html.P(
                    id="description-tab3",
                    children="Hospitalisation statistics broken down by geographical regions over time",
                ),
            ],
        ),
        html.Div(
            id="app-container-tab3",
            children=[
                html.Div(
                    id="left-column-tab3",
                    children=[
                        html.Div(
                            id="slider-container-tab3",
                            children=[
                                html.P(
                                    id="slider-text-tab3",
                                    children="Drag the slider to change day after start of simualtion:",
                                    style={'padding':'10px'},
                                ),
                                dcc.Slider(
                                    id="hospitalisation-day-slider",
                                    min=0,
                                    max=len(dash_plotter.days) - 1,
                                    value=0,
                                    marks={i: str(day) for i, day in enumerate(dash_plotter.days)}
                                ),
                            ],
                        ),
                        html.Div(
                            id="heatmap-container-tab3",
                            children=[
                                html.P(
                                    "Heatmap of hospitalisation at day: {0}".format(
                                        0
                                    ),
                                    style={'padding':'10px'},
                                    id="hospitalisation-map-title",
                                ),
                                dcc.Graph(
                                    figure=dash_plotter.generate_hospital_map_callback(
                                        day_number=0
                                    ),
                                    id="hospitalisation-map",
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    id="graph-container-tab3",
                    children=[
                        html.P(id="chart-selector-tab3", children="Select chart:", style={'padding':'10px'}),
                        dcc.Dropdown(
                            options=[
                                {
                                    "label": "Hospitalisation curves",
                                    "value": "show_hospitalisation_curves",
                                }
                            ],
                            value="show_hospitalisation_curves",
                            id="hospitalisation-chart-dropdown",
                        ),

                        dcc.RadioItems(
                            id='hospitalisation-crossfilter-yaxis-type',
                            options=[
                                {"label": i, "value": i}
                                for i in ["Linear", "Log"]
                            ],
                            value="Linear",
                        ),
                        
                        dcc.Graph(
                            figure=dash_plotter.generate_hospital_curves_callback(
                                selectedData=None, chart_type='show_hospitalisation_curves', axis_type="Log"
                            ),
                            id="hospitalisation-selected-data",
                        ),
                    ],
                ),
            ],
        ),
    ],
)

app.layout = html.Div([
    html.H4('JUNE: an open-source individual-based epidemiology simulation', style={'padding': '20px'}),
    dcc.Tabs(id="tabs-example", value='tab-1-example', children=[
        dcc.Tab(id="tab-1", label='Summary statistics', value='tab-1', style=tab_style, selected_style=tab_selected_style),
        dcc.Tab(id="tab-2", label='Geographical data', value='tab-2', style=tab_style, selected_style=tab_selected_style),
        dcc.Tab(id="tab-3", label='Hospitalisation data', value='tab-3', style=tab_style, selected_style=tab_selected_style),
    ]),
    html.Div(id='tabs-content-example',
             children = [tab1, tab2, tab3]
    ),
    html.Div(
        id='root-tab',
        children=[
            html.Div(
                id="header-tab",
                children=[
                    #html.Img(id="logo", src=app.get_asset_url("IDAS.png")),
                    html.H4(children="JUNE"),
                    html.P(
                        id="description-tab-p1",
                        children="""
                        JUNE is a modular multi-agent simualtion designed and build by researchers at Durham University and University College London and named after June Almeida, the Scottish virologist who first identified the coronavirus group of viruses. The simualtion has been designed in response to the call for better and more detailed modelling of the spread of COVID-19 in the United Kingdom. The simulation is modular meaning that different sections can be turned on and off depending on the detail required and the computational resources available. Our model is generalisable to other infectious diseases.
                        """,
                    ),
                    html.P(
                        id="description-tab-p2",
                        children="""
                        Authors:
                        Christoph Becker,
                        Joseph Bullock,
                        Richard Bower,
                        Tristan Caulfield,
                        Aoife Curran,
                        Carolina Cuesta-Lazaro,
                        Edward Elliott,
                        Kevin Fong,
                        Richard Hayes,
                        Miguel Icaza-Lizaola,
                        Frank Krauss,
                        James Nightingale,
                        Arnau Quera-Bofarull,
                        Aidan Sedgewick,
                        Henry Truong,
                        Julian Willams
                        """,
                    ),
                ],
            ),
        ],
    )
])


@app.callback(Output('tabs-content-example', 'children'),
             [Input('tabs-example', 'value')])
def render_content(tab):
    if tab == 'tab-1':
        return tab1
    elif tab == 'tab-2':
        return tab2
    elif tab == 'tab-3':
        return tab3

    
@app.callback(
    Output("infected-map", "figure"),
    [Input("day-slider", "value")],
)
def update_map(value):
    return dash_plotter.generate_animated_map_callback(day_number=value)



@app.callback(Output("infected-map-title", "children"), [Input("day-slider", "value")])
def update_map_title(day):
    return "Heatmap of infections at day: {0}".format(
        day
    )


@app.callback(
    Output("selected-data", "figure"),
    [
        Input("infected-map", "selectedData"),
        Input("chart-dropdown", "value"),
        Input("crossfilter-yaxis-type", "value"),
    ],
)
def update_infection_curves(selectedData, chart, crossfilter):
    return dash_plotter.generate_infection_curves_callback(selectedData, chart, crossfilter)


@app.callback(Output("hospitalisation-map-title", "children"), [Input("hospitalisation-day-slider", "value")])
def update_map_title(day):
    return "Heatmap of hospitalisation at day: {0}".format(
        day
    )


@app.callback(Output("hospitalisation-map", "figure"),
              [Input("hospitalisation-day-slider", "value")]
)
def update_hospiptalisation_map(value):
    return dash_plotter.generate_hospital_map_callback(day_number=value)


@app.callback(Output("hospitalisation-selected-data", "figure"),
              [
                  Input("hospitalisation-map", "selectedData"),
                  Input("hospitalisation-chart-dropdown", "value"),
                  Input("hospitalisation-crossfilter-yaxis-type"),
              ],
)
def update_hospitalisation_curves(selectedData, chart, crossfilter):
    return dash_plotter.generate_hospital_curves_callback(selectedData, chart_type, axis_type)

if __name__ == "__main__":
    app.run_server(debug=True)
