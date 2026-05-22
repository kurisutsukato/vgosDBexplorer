from pathlib import Path

import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import numpy as np

from vgosdb import VGOSSession

session = VGOSSession("R11001.tgz")

app = dash.Dash(__name__)


#
# helpers
#

def station_dataset_options(station_name):
    if not station_name:
        return []

    return [
        {
            "label": ds,
            "value": ds
        }
        for ds in session[station_name].datasets
    ]


def station_variable_options(
    station_name,
    dataset_name
):

    if not station_name or not dataset_name:
        return []

    ds = session[station_name][dataset_name]

    return [
        {
            "label": var,
            "value": var
        }
        for var in ds.variables
    ]


def session_variable_options(dataset_name):
    if not dataset_name:
        return []

    ds = session[dataset_name]

    return [
        {
            "label": var,
            "value": var
        }
        for var in ds.variables
    ]


def format_value(values):
    if np.isscalar(values):
        return str(values)

    arr = np.asarray(values)

    return f'array of shape: {arr.shape}\n{str(arr)}'

app.layout = html.Div(
    [

        html.H1("VGOS Session Viewer"),

        #
        # station section
        #

        html.H2("Station Variables"),

        html.Div(
            [

                #
                # station
                #

                html.Label("Station"),

                dcc.Dropdown(
                    id="station-dropdown",
                    options=[
                        {
                            "label": s,
                            "value": s
                        }
                        for s in session.station_names
                    ],
                    value=session.station_names[0],
                    clearable=False,
                    style={"width": "400px"}
                ),

                html.Br(),

                #
                # dataset
                #

                html.Label("Dataset"),

                dcc.Dropdown(
                    id="station-dataset-dropdown",
                    clearable=False,
                    style={"width": "400px"}
                ),

                html.Br(),

                #
                # variable
                #

                html.Label("Variable"),

                dcc.Dropdown(
                    id="station-variable-dropdown",
                    clearable=False,
                    style={"width": "400px"}
                ),

            ]
        ),

        html.Br(),

        dcc.Textarea(
            id="station-text",
            style={
                "width": "100%",
                "height": "300px",
                "fontFamily": "monospace"
            }
        ),

        html.Hr(),

        #
        # session section
        #

        html.H2("Session Variables"),

        html.Label("Dataset"),

        dcc.Dropdown(
            id="session-dataset-dropdown",
            options=[
                {
                    "label": ds,
                    "value": ds
                }
                for ds in session.dataset_names
            ],
            value=session.dataset_names[0],
            clearable=False,
            style={"width": "400px"}
        ),

        html.Br(),

        #
        # session variable
        #

        html.Label("Variable"),

        dcc.Dropdown(
            id="session-variable-dropdown",
            clearable=False,
            style={"width": "400px"}
        ),

        html.Br(),

        dcc.Textarea(
            id="session-text",
            style={
                "width": "100%",
                "height": "300px",
                "fontFamily": "monospace"
            }
        )

    ],
    style={
        "margin": "30px"
    }
)


#
# station dataset callback
#

@app.callback(
    Output("station-dataset-dropdown", "options"),
    Output("station-dataset-dropdown", "value"),
    Input("station-dropdown", "value")
)
def update_station_datasets(station_name):

    options = station_dataset_options(
        station_name
    )

    value = None

    if options:
        value = options[0]["value"]

    return options, value


#
# station variable callback
#

@app.callback(
    Output("station-variable-dropdown", "options"),
    Output("station-variable-dropdown", "value"),
    Input("station-dropdown", "value"),
    Input("station-dataset-dropdown", "value")
)
def update_station_variables(
    station_name,
    dataset_name
):

    options = station_variable_options(
        station_name,
        dataset_name
    )

    value = None

    if options:
        value = options[0]["value"]

    return options, value


#
# station display callback
#

@app.callback(
    Output("station-text", "value"),
    Input("station-dropdown", "value"),
    Input("station-dataset-dropdown", "value"),
    Input("station-variable-dropdown", "value")
)
def update_station_text(
    station_name,
    dataset_name,
    variable_name
):

    if (
        not station_name
        or not dataset_name
        or not variable_name
    ):

        return ""

    ds = session[station_name][dataset_name]

    values = ds[variable_name]

    return format_value(values)


#
# session variable callback
#

@app.callback(
    Output("session-variable-dropdown", "options"),
    Output("session-variable-dropdown", "value"),
    Input("session-dataset-dropdown", "value")
)
def update_session_variables(dataset_name):

    options = session_variable_options(
        dataset_name
    )

    value = None

    if options:
        value = options[0]["value"]

    return options, value


#
# session display callback
#

@app.callback(
    Output("session-text", "value"),
    Input("session-dataset-dropdown", "value"),
    Input("session-variable-dropdown", "value")
)
def update_session_text(
    dataset_name,
    variable_name
):

    if (
        not dataset_name
        or not variable_name
    ):

        return ""

    ds = session[dataset_name]

    values = ds[variable_name]

    return format_value(values)


#
# main
#

if __name__ == "__main__":

    app.run(debug=True)