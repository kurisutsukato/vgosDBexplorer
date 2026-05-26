import base64
import tempfile
from pathlib import Path
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

import numpy as np

import dash
from dash import dcc, html, Input, Output, State
from plotly.subplots import make_subplots
import plotly.graph_objs as go
from plotly.validator_cache import ValidatorCache
SymbolValidator = ValidatorCache.get_validator("scatter.marker", "symbol")
syms = SymbolValidator.values[2::12]
syms += SymbolValidator.values[9::12]
syms += SymbolValidator.values[4::12]
syms += SymbolValidator.values[7::12]

import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)

from vgosdb import VGOSSession

current_session = None


def empty():
    fig = make_subplots(1, 1)
    fig.update_layout(width=900, height=200,
                      margin=dict(l=0, r=0, t=0, b=0))

    return fig

app = dash.Dash(__name__)

app.layout = html.Div(
    [

        html.H1("vgosDB Explorer"),
        html.Div(
            [

                #
                # LEFT COLUMN
                #

                html.Div(
                    [

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
                            },
                            multiple=False
                        ),

                        dcc.Loading(
                            id="upload-loading",
                            type="circle",
                            children=html.Div(
                                id="upload-status"
                            )
                        ),

                        html.Hr(),

                        #
                        # station controls
                        #

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
                            "marginBottom": "20px"
                        }
                        ),

                        html.Br(),

                        #
                        # source selection
                        #

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

                        #
                        # parameter selection
                        #

                        html.Div(
                            [

                                html.Label("Parameters"),

                                dcc.Dropdown(
                                    id="parameter-dropdown",
                                    clearable=True
                                )

                            ]
                        ),

                        html.Div(
                            [

                                html.Label("Parameters 2"),

                                dcc.Dropdown(
                                    id="parameter2-dropdown",
                                    clearable=True
                                )

                            ]
                        ),

                        html.Hr(),

                        #
                        # text output
                        #

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
                            figure=empty(),
                            id="output-figpol",
                            style={
                                "height": "65vh"
                            }
                        ),
                        dcc.Graph(
                            figure=empty(),
                            id="output-figxy",
                            style={
                                "height": "30vh"
                            }
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
    Output("upload-status", "children"),
    Output("station1-dropdown", "options"),
    Output("station1-dropdown", "value"),
    Output("station2-dropdown", "options"),
    Output("station2-dropdown", "value"),
    Input("upload-vgosdb", "contents"),
    State("upload-vgosdb", "filename")
)
def upload_file(contents, filename):

    global current_session

    if contents is None:

        return "", [], None, [], None

    try:
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)

        tmp = tempfile.NamedTemporaryFile(
            suffix=".tgz",
            delete=False
        )

        tmp.write(decoded)
        tmp.close()

        current_session = VGOSSession(tmp.name)

        stations = current_session.station_names

        options = [
            {
                "label": s,
                "value": s
            }
            for s in stations
        ]

        return (
            f"Loaded: {filename}",
            options,
            None, #stations[0] if stations else None,
            options,
            None, #stations[1] if len(stations) > 1 else None
        )

    except Exception as ex:

        return (
            f"Error: {ex}",
            [],
            None,
            [],
            None
        )

@app.callback(
    Output("parameter2-dropdown", "options"),
    Output("parameter2-dropdown", "value"),
    Input("station1-dropdown", "value"),
    Input("station2-dropdown", "value"),
    Input("source-dropdown", "value"),
    State("parameter2-dropdown", "value")
)
def update_parameters2(st1, st2, source, current_parameter):
    global current_session

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
    State("parameter-dropdown", "value")
)
def update_parameters(st1, st2, source, current_parameter):
    global current_session

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
    State("source-dropdown", "value")
)
def update_sources(st1, st2, current_source):

    global current_session

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


def parameter_list(st1, st2, source, parameter, parameter2=None):
    global current_session
    df = current_session.baselines

    mask = pd.Series(True, index=df.index)

    if st1:
        mask &= (df["st1"] == st1) | (df["st2"] == st1)
    if st2:
        mask &= (df["st1"] == st2) | (df["st2"] == st2)
    if source:
        mask &= df["src"] == source

    sub = df.loc[mask]

    logging.info(f'len sub: {len(sub)}')

    cols = []

    if parameter is not None:
        name = parameter.split('/')[-1]
        logging.info('parameter1')
        if '|' in parameter:  # station parameters
            par = current_session[st1].parameters[parameter]
            df = current_session[st1].utc.copy()
            df[name] = par
        else: # session parameters
            par = current_session.parameters[parameter]
            df = current_session.baselines.copy()
            df[name] = par
            df = df.loc[df['baseline'] == '-'.join(sorted([st1, st2]))]
        cols.append(name)

        logging.info(f'len df: {len(df)} {df.columns}')

        #sub = sub.merge(df, on='utc', how='left')
        sub = sub.merge(df, on='utc', how='left')
        logging.info(f'len sub: {len(sub)} {sub.columns}')

        if parameter2 is not None:
            logging.info('parameter2')
            if '|' in parameter2:  # station parameters
                par = current_session[st1].parameters[parameter2]
                df = current_session[st1].utc.copy()
            else: # session parameters
                par = current_session.parameters[parameter2]
                df = current_session.baselines[['utc']].copy()

            name = parameter2.split('/')[-1]
            df[name] = par
            cols.append(name)

            logging.info(f'len df: {len(df)} {df.columns}')

            sub = df.merge(sub, on='utc', how='left')
            logging.info(f'len sub: {len(sub)} {sub.columns}')

    return sub, cols


@app.callback(
    Output("output-text", "value"),
    Input("station1-dropdown", "value"),
    Input("station2-dropdown", "value"),
    Input("source-dropdown", "value"),
    Input("parameter-dropdown", "value")
)
def update_output(st1, st2, source, parameter):
    global current_session

    if current_session is None:
        return ""

    if st1 is None and st2 is None:
        return ""

    sub, parcols = parameter_list(st1, st2, source, parameter)

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
    Input("parameter2-dropdown", "value"),
)
def update_plotxy(
    st1,
    st2,
    source,
    parameter2,
):
    global current_session

    if current_session is None:
        return empty()

    if parameter2 is None:
        return empty()

    filtered, names = parameter_list(st1, st2, source, parameter2)
    logging.info(f'plotxy {len(filtered)} {names}   ')


    fig = make_subplots(1, 1)
    fig.update_layout(width=1000, height=200, margin=dict(l=0, r=0, t=0, b=0))

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
)
def update_plotpol(
    st1,
    st2,
    source,
    parameter,
    relayout,
    parameter2
):
    global current_session

    if current_session is None:
        return empty()

    if parameter is None:
        return empty()

    filtered, names = parameter_list(st1, st2, source, parameter, parameter2)
    logging.info(f'plotpol {len(filtered)} {names}   ')

    if relayout:
        if "xaxis.range[0]" in relayout:
            xmin = pd.to_datetime(relayout["xaxis.range[0]"])
            xmax = pd.to_datetime(relayout["xaxis.range[1]"])

            filtered = filtered.loc[(filtered["utc"] >= xmin) & (filtered["utc"] <= xmax)]
        if "yaxis.range[0]" in relayout:
            ymin = float(relayout["yaxis.range[0]"])
            ymax = float(relayout["yaxis.range[1]"])
            name = parameter2.split('/')[-1]
            filtered = filtered.loc[(filtered[name] >= ymin) & (filtered[name] <= ymax)]

    mi = filtered[names[0]].min()
    ma = filtered[names[0]].max()

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
            st = 'st1' if st1 in df_bl['st1'].values else 'st2'

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
                y=0.65,  # center
                len=0.7,  # height
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
    app.run(debug=True)
