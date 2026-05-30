from dash import dcc, html
import dash_bootstrap_components as dbc
from plotly import graph_objs as go

def empty(height=900):
    fig = go.Figure()

    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor='white',
        paper_bgcolor='white',
        annotations=[
            dict(
                text="No data available",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=20)
            )
        ],
        height=height, width=900
    )
    return  fig

visexplorer = html.Div(
    [
        dcc.Location(
            id="url",
            refresh=False
        ),

        dcc.Store(
            id="stored-sessions",
            data={} #initial_stored_sessions
        ),

        html.H1("vgosDB Explorer"),
        html.Div(
            [

                # LEFT COLUMN
                html.Div(
                    [
                        html.Label("Stored Sessions"),

                        dcc.Loading(
                            id="session-loading",
                            type="circle",
                            target_components={"info-session-loading": "children"},
                            children = [
                                dcc.Dropdown(
                                    id="session-dropdown",
                                    value=None, #next(iter(initial_stored_sessions), None),
                                    clearable=False
                                ),
                            html.Div(id="info-session-loading")
                            ]
                        ),

                        dcc.Loading(
                            id="upload-loading",
                            type="circle",
                            target_components={"info-file-loading": "children"},
                            children=[
                                dcc.Upload(
                                    id="upload-vgosdb",
                                    children=html.Div(
                                        [
                                            "Drag and Drop or ",
                                            html.A("Select VGOSDB File")
                                        ]
                                    ),
                                    style={
                                        "width": "100%",
                                        "height": "60px",
                                        "lineHeight": "60px",
                                        "borderWidth": "1px",
                                        "borderStyle": "dashed",
                                        "borderRadius": "5px",
                                        "textAlign": "center",
                                        "marginBottom": "20px",
                                        "marginTop": "10px"
                                    },
                                    multiple=False
                                ),
                                html.Div(id="info-file-loading")
                            ]
                        ),

                        html.Br(),

                        # station controls
                        html.Div(
                            [

                                html.Div(
                                    [
                                        html.Label("Station 1"),

                                        dcc.Dropdown(
                                            id="station1-dropdown",
                                            clearable=True
                                        )
                                    ],
                                    style={
                                        "width": "40%"
                                    }
                                ),

                                dbc.Button(
                                    html.I(className="bi bi-arrow-left-right"),
                                    className="align-self-center",
                                    outline=True,
                                    color="secondary",
                                    id="switch",
                                    style={'width':"10%"}
                                ),

                                html.Div(
                                    [
                                        html.Label("Station 2"),

                                        dcc.Dropdown(
                                            id="station2-dropdown",
                                            clearable=True
                                        )
                                    ],
                                    style={
                                        "width": "40%"
                                    }
                                ),
                            ],
                        style = {
                            "display": "flex",
                            "flexDirection": "row",
                            "justifyContent": "space-between",
                            "gap": "10px",
                            "marginBottom": "10px",
                            "marginTop": "10px"
                        }
                        ),

                        html.Br(),

                        # parameter selection
                        html.Div(
                            [
                                html.Label("Polar plot"),

                                dcc.Dropdown(
                                    id="parameter-dropdown",
                                    clearable=True
                                )
                            ]
                        ),

                        html.Br(),

                        html.Div(
                            [
                                html.Label("Time-series plot"),
                                dcc.Dropdown(
                                    id="parameter2-dropdown",
                                    clearable=True
                                )
                            ]
                        ),

                        html.Br(),

                        # source selection
                        html.Div(
                            [
                                html.Label("Source filter"),

                                dcc.Dropdown(
                                    id="source-dropdown",
                                    clearable=True
                                )
                            ]
                        ),

                        html.Br(),

                        # text output
                        html.H3("Matching Observations"),

                        dcc.Textarea(
                            id="output-text",
                            wrap="off",
                            style={
                                "width": "100%",
                                "height": "400px",
                                "fontFamily": "monospace",
                                "overflowX": "scroll",
                                "overflowY": "scroll"
                            }
                        )

                    ],
                    style={
                        "width": "35%",
                        "padding": "20px",
                        "boxSizing": "border-box",
                        "overflowY": "auto"
                    }
                ),

                # RIGHT COLUMN
                html.Div(
                    [
                        dcc.Graph(
                            figure=empty(500),
                            id="output-figpol",
                            #style={
                            #    "height": "65vh"
                            #}
                        ),
                        dcc.Graph(
                            figure=empty(500),
                            id="output-figxy",
                            style={
                                "margin-top": "40px"
                            }
                        ),
                        html.Div('Zooming on the data in the time-series plot acts as a filter for the polar plot. Zooming is '
                                 'possible in both, or individually along just one axis. Click and drag the time units '
                                 'near the center of the axis to move the time window. Click and drag the time units '
                                 'near the end of the axis to extend/shrink the window.',
                                 style=dict(width='800px', margin='20px')
                        )

                    ],
                    style={
                        "width": "65%",
                        "padding": "0px",
                        "boxSizing": "border-box"
                    }
                )

            ],
            style={
                "display": "flex",
                "flexDirection": "row",
                "height": "95vh"
            }
        )
    ],
    style={
        "margin": "10px"
    }
)

dbexplorer = html.Div(
    [
        dcc.Location(
            id="url",
            refresh=False
        ),

        dcc.Store(
            id="stored-sessions",
            data={} #initial_stored_sessions
        ),
        html.H1("VGOS Session Viewer"),

        html.Label("Stored Sessions"),

        dcc.Loading(
            id="session-loading",
            type="circle",
            target_components={"info-session-loading": "children"},
            children=[
                dcc.Dropdown(
                    id="session-dropdown",
                    value=None,  # next(iter(initial_stored_sessions), None),
                    clearable=False
                ),
                html.Div(id="info-session-loading")
            ]
        ),

        dcc.Loading(
            id="upload-loading",
            type="circle",
            target_components={"info-file-loading": "children"},
            children=[
                dcc.Upload(
                    id="upload-vgosdb",
                    children=html.Div(
                        [
                            "Drag and Drop or ",
                            html.A("Select VGOSDB File")
                        ]
                    ),
                    style={
                        "width": "100%",
                        "height": "60px",
                        "lineHeight": "60px",
                        "borderWidth": "1px",
                        "borderStyle": "dashed",
                        "borderRadius": "5px",
                        "textAlign": "center",
                        "marginBottom": "20px",
                        "marginTop": "10px"
                    },
                    multiple=False
                ),
                html.Div(id="info-file-loading")
            ]
        ),

        #
        # session section
        #

        html.H2("Session Variables"),

        html.Label("Dataset"),

        dcc.Dropdown(
            id="session-dataset-dropdown",
            options=[],
            value=None,
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
        ),


        html.H2("Station Variables"),

        #
        # station
        #

        html.Label("Station"),

        dcc.Dropdown(
            id="station-dropdown",
            options=[],
            value=None,
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

        html.Br(),

        dcc.Textarea(
            id="station-text",
            style={
                "width": "100%",
                "height": "300px",
                "fontFamily": "monospace"
            }
        ),

    ],
    style={
        "margin": "30px"
    }
)
