import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go


sa_to_county_df = pd.read_csv(
    "/home/arnau/Downloads/Output_Area_to_LSOA_to_MSOA_to_Local_Authority_District__December_2017__Lookup_with_Area_Classifications_in_Great_Britain.csv",
    index_col=7,
)
with open(
    "/home/arnau/Downloads/Local_Authority_Districts_(December_2017)_Super_Generalised_Clipped_Boundaries_in_Great_Britain.geojson"
) as f:
    county_shapes = json.load(f)

data_to_plot = pd.read_csv(
    "/home/arnau/code/JUNE/scripts/visualization_df.csv", index_col=0
)
data_to_plot = pd.merge(
    data_to_plot, sa_to_county_df, left_on="super_area", right_on="MSOA11CD"
)
data_to_plot = data_to_plot[
    ["super_area", "infected", "recovered", "susceptible", "LAD17NM", "time"]
]
data_to_plot.drop_duplicates(inplace=True)
data_to_plot = data_to_plot.groupby(["time", "LAD17NM"]).sum()
data_to_plot.reset_index(inplace=True)
data_to_plot.set_index("time", inplace=True)

max_infected = data_to_plot["infected"].max()

def generate_infection_map(time):
    data = data_to_plot.loc[time]
    fig = px.choropleth(
        data,
        geojson=county_shapes,
        color="infected",
        locations="LAD17NM",
        featureidkey="properties.lad17nm",
        projection="mercator",
        hover_data=["infected", "susceptible", "recovered"],
        range_color=(0, max_infected),
        #animation_frame="time",
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig

######

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

df = pd.read_csv("https://plotly.github.io/datasets/country_indicators.csv")

available_indicators = ["Infection curves", "Hospitalization"] #df["Indicator Name"].unique()

app.layout = html.Div(
    [
        html.Div(
            [
                html.Div(
                    [
                        dcc.Dropdown(
                            id="crossfilter-yaxis-column",
                            options=[
                                {"label": i, "value": i} for i in available_indicators
                            ],
                            value="Infection curves",
                        ),
                        dcc.RadioItems(
                            id="crossfilter-yaxis-type",
                            options=[
                                {"label": i, "value": i} for i in ["Linear", "Log"]
                            ],
                            value="Log",
                            labelStyle={"display": "inline-block"},
                        ),
                    ],
                    style={"width": "49%", "float": "right", "display": "inline-block"},
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
                    figure = generate_infection_map(1.0),
                    id="crossfilter-indicator-map",
                )
            ],
            style={"width": "100%", "display": "inline-block", "padding": "0 20"},
        ),
        html.Div(
            dcc.Slider(
                id="crossfilter-time--slider",
                min=data_to_plot.index.min(),
                max=data_to_plot.index.max(),
                value=data_to_plot.index.min(),
                marks={str(year): str(year) for year in data_to_plot.index.unique()},
                step=None,
            ),
            style={"width": "49%", "padding": "0px 20px 20px 20px"},
        ),
    ], style = { 'columnCount': 2}
)


@app.callback(
    dash.dependencies.Output("crossfilter-indicator-map", "figure"),
    [
        dash.dependencies.Input("crossfilter-time--slider", "value"),
    ],
)
def update_map(
    time
):
    return generate_infection_map(time)

@app.callback(
    dash.dependencies.Output("y-time-series", "figure"),
    [
        dash.dependencies.Input("crossfilter-indicator-map", "hoverData"),
        dash.dependencies.Input("crossfilter-yaxis-type", "value"),
    ],
)
def update_infection_plot(hoverData, axis_type):
    county_name = hoverData["points"][0]["location"]
    data = data_to_plot[data_to_plot["LAD17NM"] == county_name]
    data.reset_index(inplace=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data["time"].values, y=data["infected"].values, name="infected"))
    fig.add_trace(go.Scatter(x=data["time"].values, y=data["recovered"].values, name="recovered"))
    fig.add_trace(go.Scatter(x=data["time"].values, y=data["susceptible"].values, name="susceptible"))
    if axis_type == "Log":
        fig.update_layout(yaxis_type="log")
    return fig

if __name__ == "__main__":
    app.run_server(debug=True)
