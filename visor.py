import base64
import tempfile
from pathlib import Path
import uuid

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

import numpy as np

import dash
from dash import dcc, html, Input, Output, State, ctx
from dash.exceptions import PreventUpdate

import pandas as pd


from plotly.subplots import make_subplots
import plotly.graph_objs as go
from plotly.validator_cache import ValidatorCache
SymbolValidator = ValidatorCache.get_validator("scatter.marker", "symbol")
syms = SymbolValidator.values[2::12]
syms += SymbolValidator.values[9::12]
syms += SymbolValidator.values[4::12]
syms += SymbolValidator.values[7::12]


from vgosdb import VGOSSession

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(filename)s:%(lineno)d %(message)s'
)


UPLOAD_DIR = Path("./uploaded_vgosdb")
UPLOAD_DIR.mkdir(exist_ok=True)

loaded_sessions = {}
#initial_stored_sessions = {}

for filepath in UPLOAD_DIR.glob("*.tgz"):
    try:
        session_id = filepath.stem
        session = None
        #session = VGOSSession(filepath)

        loaded_sessions[session_id] = session

    except Exception as ex:
        print(f"Could not load {filepath}: {ex}")

def scan_sessions():
    sessions = {}

    for filepath in UPLOAD_DIR.glob("*.tgz"):
        try:
            session_id = filepath.stem

            sessions[session_id] = {
                "filename": filepath.name,
                "filepath": str(filepath)
            }
        except Exception as ex:
            print(f"Could not load {filepath}: {ex}")

    return sessions


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

app = dash.Dash(__name__)

app.layout = html.Div(
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
                            target_components={
                                    "info-session-loading": "children"
                                },
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
                            target_components={
                                    "info-file-loading": "children"
                                },
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
                                        "width": "48%"
                                    }
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
                                        "width": "48%"
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

                        # source selection
                        html.Div(
                            [
                                html.Label("Available Sources"),

                                dcc.Dropdown(
                                    id="source-dropdown",
                                    clearable=True
                                )
                            ]
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

                                html.Label("Linear plot"),

                                dcc.Dropdown(
                                    id="parameter2-dropdown",
                                    clearable=True
                                )

                            ]
                        ),


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
                        html.Div('Zooming on the data in the XY plot acts as a filter for the polar plot. Zooming is '
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


@app.callback(
    Output("stored-sessions", "data", allow_duplicate=True),
    Output("session-dropdown", "options", allow_duplicate=True),
    Output("session-dropdown", "value", allow_duplicate=True),

    Input("url", "pathname"),
    prevent_initial_call=True
)
def reload_sessions(_):
    sessions = scan_sessions()

    # optionally rebuild RAM cache
    loaded_sessions.clear()

    options = [
        {
            "label": item["filename"],
            "value": sid
        }
        for sid, item in sessions.items()
    ]

    return sessions, options, None

@app.callback(
    Output("stored-sessions", "data", allow_duplicate=True),
    Output("session-dropdown", "options", allow_duplicate=True),
    Output("session-dropdown", "value", allow_duplicate=True),
    Output("info-file-loading", "children"),

    Input("upload-vgosdb", "contents"),

    State("upload-vgosdb", "filename"),
    State("stored-sessions", "data"),
    prevent_initial_call=True
)
def upload_file(contents, filename, stored_sessions):

    if contents is None:
        raise PreventUpdate
    logging.info(f'{filename}')
    try:
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)

        session_id = str(uuid.uuid4())

        filepath = UPLOAD_DIR / filename

        with open(filepath, "wb") as f:
            f.write(decoded)

        # -------------------------------------------------------------
        # load session into memory cache
        # -------------------------------------------------------------

        session = VGOSSession(filepath)

        loaded_sessions[session_id] = session

        # -------------------------------------------------------------
        # persistent metadata
        # -------------------------------------------------------------

        stored_sessions[session_id] = {
            "filename": filename,
            "filepath": str(filepath)
        }

        options = [
            {
                "label": item["filename"],
                "value": sid
            }
            for sid, item in stored_sessions.items()
        ]

        return stored_sessions, options, session_id, html.Div(className="flash-message", children=f"Loaded {filename}")

    except Exception as ex:
        return stored_sessions, dash.no_update, dash.no_update, ""


@app.callback(
    Output("station1-dropdown", "options"),
    Output("station1-dropdown", "value"),
    Output("station2-dropdown", "options"),
    Output("station2-dropdown", "value"),
    Output("info-session-loading", "children"),
    Input("session-dropdown", "value"),
    State("station1-dropdown", "value"),
    State("station2-dropdown", "value"),
    State("stored-sessions", "data")
)
def select_session(session_id, st1_current, st2_current, stored_sessions):
    if not session_id:
        raise PreventUpdate
    logging.info(f'{session_id}')
    # -------------------------------------------------------------------------
    # ensure session exists in RAM cache
    # (important after server restart)
    # -------------------------------------------------------------------------

    if session_id not in loaded_sessions:
        info = stored_sessions[session_id]

        loaded_sessions[session_id] = VGOSSession(info["filepath"])

    session = loaded_sessions[session_id]

    station_options = [
        {
            "label": s,
            "value": s
        }
        for s in session.station_names
    ]

    logging.info(f'{st1_current} {session.station_names}')

    return  (
        station_options,
        st1_current if st1_current in session.station_names else None,
        station_options,
        st2_current if st2_current in session.station_names else None,
        ""
    )

@app.callback(
    Output("parameter2-dropdown", "options"),
    Output("parameter2-dropdown", "value"),
    Input("station1-dropdown", "value"),
    Input("station2-dropdown", "value"),
    Input("source-dropdown", "value"),
    State("parameter2-dropdown", "value"),
    State("session-dropdown", "value"),
)
def update_parameters2(st1, st2, source, current_parameter, session_id):
    if not session_id:
        return {}, None
    current_session = loaded_sessions[session_id]

    if current_session is None:
        return {}, None

    if st1 is None:
        return {}, None

    parameters = current_session[st1].parameters|current_session.parameters

    options = [{"label": s, "value": s} for s in parameters]

    if current_parameter in parameters:
        return options, current_parameter
    else:
        return options,None

@app.callback(
    Output("parameter-dropdown", "options"),
    Output("parameter-dropdown", "value"),
    Input("station1-dropdown", "value"),
    Input("station2-dropdown", "value"),
    Input("source-dropdown", "value"),
    State("parameter-dropdown", "value"),
    State("session-dropdown", "value"),

)
def update_parameters(st1, st2, source, current_parameter, session_id):
    if not session_id:
        return [], None
    current_session = loaded_sessions[session_id]

    if current_session is None:
        return [], None

    if st1 is None:
        return {}, None

    parameters = current_session[st1].parameters|current_session.parameters

    options = [{"label": s, "value": s} for s in parameters]

    if current_parameter in parameters:
        return options, current_parameter
    else:
        return options,None

@app.callback(
    Output("source-dropdown", "options"),
    Output("source-dropdown", "value"),
    Input("station1-dropdown", "value"),
    Input("station2-dropdown", "value"),
    State("source-dropdown", "value"),
    State("session-dropdown", "value"),

)
def update_sources(st1, st2, current_source, session_id):
    if not session_id:
        return [], None
    current_session = loaded_sessions[session_id]

    if current_session is None:
        return [], None

    df = current_session.baselines

    # optional station filtering

    mask = pd.Series(True, index=df.index)

    if st1:
        mask &= (df["st1"] == st1) | (df["st2"] == st1)

    if st2:
        mask &= (df["st1"] == st2) | (df["st2"] == st2)

    sub = df.loc[mask]

    sources = sorted(
        sub["src"].unique()
    )

    options = [{"label": s, "value": s} for s in sources]

    if current_source in sources:
        return options, current_source
    else:
        return options, None


def parameter_list(current_session, st1, st2, source, parameter, parameter2=None):
    df = current_session.baselines

    mask = pd.Series(True, index=df.index)

    if st1:
        mask &= (df["st1"] == st1) | (df["st2"] == st1)
    if st2:
        mask &= (df["st1"] == st2) | (df["st2"] == st2)
    if source:
        mask &= df["src"] == source

    sub = df.loc[mask]

    cols = []

    if parameter is not None:
        name = parameter.split('/')[-1]
        if '|' in parameter:  # station parameters
            par = current_session[st1].parameters[parameter]
            df = current_session[st1].utc.copy()
            df[name] = par
        else: # session parameters
            par = current_session.parameters[parameter]
            df = current_session.baselines.copy()
            df[name] = par
            if st2:
                df = df.loc[df['baseline'] == '-'.join(sorted([st1, st2]))].copy()
            else:
                df = df.loc[(df.st1 == st1) | (df.st2 == st1)].copy()
        cols.append(name)

        #sub = sub.merge(df, on='utc', how='left')
        sub = sub.merge(df[[name, 'utc']], on='utc', how='left')

        if parameter2 is not None and parameter2 != parameter:
            name = parameter2.split('/')[-1]
            if '|' in parameter2:  # station parameters
                par = current_session[st1].parameters[parameter2]
                df = current_session[st1].utc.copy()
                df[name] = par
            else: # session parameters
                par = current_session.parameters[parameter2]
                df = current_session.baselines.copy()
                df[name] = par
                if st2:
                    df = df.loc[df['baseline'] == '-'.join(sorted([st1, st2]))].copy()
                else:
                    df = df.loc[(df.st1 == st1) | (df.st2 == st1)].copy()
            cols.append(name)

            sub = sub.merge(df[[name, 'utc']], on='utc', how='left')

    return sub, cols


@app.callback(
    Output("output-text", "value"),
    Input("station1-dropdown", "value"),
    Input("station2-dropdown", "value"),
    Input("source-dropdown", "value"),
    Input("parameter-dropdown", "value"),
    Input("parameter2-dropdown", "value"),
    State("session-dropdown", "value"),
)
def update_output(st1, st2, source, parameter, parameter2, session_id):
    if not session_id:
        return ""
    current_session = loaded_sessions[session_id]

    if current_session is None:
        return ""

    if st1 is None and st2 is None:
        return ""

    sub, parcols = parameter_list(current_session, st1, st2, source, parameter, parameter2)

    cols = ["utc"] + parcols + ["src", "st1", "st2", "st1az", "st1el", "st2az", "st2el"]

    return sub[cols].to_string(
        index=False
    )

def select_station_column(df, station, quantity):
    mask = df["st1"] == station

    return np.where(
        mask,
        df[f"st1{quantity}"],
        df[f"st2{quantity}"]
    )

@app.callback(
    Output("output-figxy", "figure"),
    Input("station1-dropdown", "value"),
    Input("station2-dropdown", "value"),
    Input("source-dropdown", "value"),
    Input("parameter-dropdown", "value"),
    Input("parameter2-dropdown", "value"),
    State("session-dropdown", "value"),
)
def update_plotxy(st1, st2, source, parameter, parameter2, session_id):
    if not session_id:
        return empty(200)

    current_session = loaded_sessions[session_id]

    if current_session is None or parameter2 is None:
        return empty(200)

    filtered, names = parameter_list(current_session, st1, st2, source, parameter2)

    fig = make_subplots(1, 1)
    fig.update_layout(width=1000, height=200, margin=dict(l=0, r=0, t=40, b=0))

    fig.add_trace(go.Scatter(x=filtered.utc, y=filtered[names[0]], mode='markers'), row=1, col=1)
    return fig

@app.callback(
    Output("output-figpol", "figure"),
    Input("station1-dropdown", "value"),
    Input("station2-dropdown", "value"),
    Input("source-dropdown", "value"),
    Input("parameter-dropdown", "value"),
    Input("output-figxy", "relayoutData"),
    State("parameter2-dropdown", "value"),
    State("session-dropdown", "value"),
)
def update_plotpol(st1, st2, source, parameter, relayout, parameter2, session_id):
    if not session_id:
        return empty(550)
    current_session = loaded_sessions[session_id]

    if current_session is None or parameter is None:
        return empty(550)

    filtered, names = parameter_list(current_session, st1, st2, source, parameter, parameter2)

    mi = filtered[names[0]].min()
    ma = filtered[names[0]].max()

    logging.info(f'{ctx.triggered_id} {relayout}')

    if ctx.triggered_id == 'output-figxy' and relayout:
        if "xaxis.range[0]" in relayout:
            xmin = pd.to_datetime(relayout["xaxis.range[0]"])
            xmax = pd.to_datetime(relayout["xaxis.range[1]"])

            filtered = filtered.loc[(filtered["utc"] >= xmin) & (filtered["utc"] <= xmax)]
        if "yaxis.range[0]" in relayout:
            ymin = float(relayout["yaxis.range[0]"])
            ymax = float(relayout["yaxis.range[1]"])
            name = parameter2.split('/')[-1]
            filtered = filtered.loc[(filtered[name] >= ymin) & (filtered[name] <= ymax)]


    kwargs = dict(marker_colorbar_thickness=24, marker_cmax=mi, marker_cmin=ma,
                  mode='markers',
                  marker={'opacity': .7, 'colorscale': 'plasma', 'size': 12, 'symbol': syms[0],
                          'coloraxis':'coloraxis','cmin':mi,'cmax':ma,
                          'line': dict(width=1, color='DarkSlateGrey'),
                          }
                  )

    fig = make_subplots(1, 1, specs=[[{"type": "polar"}]])
    fig.update_layout(width=1000, height=550, margin=dict(l=0, r=0, t=0, b=0))

    if source is None:
        for n, (source, df_source) in enumerate(filtered.groupby('src')):
            kwargs['marker']['symbol'] = syms[n]

            df_source["staz"] = select_station_column(df_source, st1, 'az')
            df_source["stel"] = select_station_column(df_source, st1, 'el')

            fig.add_trace(go.Scatterpolar(
                r=df_source['stel'], #.apply(lambda q: q[q['stel']], axis=1),
                theta=df_source['staz'], #.apply(lambda q: q[q['staz']], axis=1),
                marker_color=df_source[names[0]].to_list(),
                showlegend=True,
                name=source,
                hovertemplate='source: <b>{}</b>'.format(
                    source) + f'<extra></extra><br>{str(names[0])}: '+'%{text}<br>Time: %{customdata}',
                text=[f'{q:.2g}' for q in df_source[names[0]].values],
                customdata=[q.strftime('%H:%M') for q in df_source.utc],
                **kwargs
            ),row=1, col=1)
    else:
        for n,(bl, df_bl) in enumerate(filtered.groupby('baseline')):
            kwargs['marker']['symbol'] = syms[n]

            df_bl["staz"] = select_station_column(df_bl, st1, 'az')
            df_bl["stel"] = select_station_column(df_bl, st1, 'el')

            fig.add_trace(go.Scatterpolar(
                r=df_bl['stel'],
                theta=df_bl['staz'],
                marker_color=df_bl[names[0]].to_list(),
                showlegend=True,
                name=bl,
                hovertemplate='baseline: <b>{}</b>'.format(bl)+f'<extra></extra><br>{names[0]}:'+'%{text}<br>Time: %{customdata}',
                customdata=[q.strftime('%H:%M') for q in df_bl.utc],
                text=[f'{q:.2g}' for q in df_bl[names[0]].values],
                **kwargs
            ),row=1, col=1)


    fig.update_layout(
        coloraxis=dict(
            colorscale="Jet",
            cmin=mi,
            cmax=ma,
            colorbar=dict(
                title=names[0],
                yanchor="middle"
            )
        )
    )

    fig.update_layout(
        legend=dict(
            yanchor="top",
            y=1,
            xanchor="left",
            x=-.4,
            itemsizing='constant'
        )
    )
    fig.update_polars(radialaxis_autorange=False, radialaxis_range=[90,0], angularaxis_direction='clockwise')

    return fig


if __name__ == "__main__":
    app.run(debug=True, port=9003)
