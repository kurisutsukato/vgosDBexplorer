from pathlib import Path
import uuid, base64

import dash
from dash import dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate
import pandas as pd
import plotly.express as px
import numpy as np
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from vgosdb import VGOSSession
from applayout import dbexplorer as layout


UPLOAD_DIR = Path("./uploaded_vgosdb")
UPLOAD_DIR.mkdir(exist_ok=True)

loaded_sessions = {}

for filepath in UPLOAD_DIR.glob("*.tgz"):
    try:
        session_id = filepath.stem

        loaded_sessions[session_id] = None

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


app = dash.Dash(__name__)
app.layout = layout
app.title = 'vgosDB explorer'

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

    options = [{"label": item["filename"], "value": sid } for sid, item in sessions.items()]

    return sessions, options, None


def format_value(values):
    if np.isscalar(values):
        return str(values)

    arr = np.asarray(values)

    return f'array of shape: {arr.shape}\n{str(arr)}'

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

    try:
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)

        session_id = str(uuid.uuid4())

        filepath = UPLOAD_DIR / filename

        with open(filepath, "wb") as f:
            f.write(decoded)

        session = VGOSSession(filepath)
        loaded_sessions[session_id] = session

        stored_sessions[session_id] = {
            "filename": filename,
            "filepath": str(filepath)
        }

        options = [{"label": item["filename"], "value": sid} for sid, item in stored_sessions.items()]

        return stored_sessions, options, session_id, html.Div(className="flash-message", children=f"Loaded {filename}")

    except Exception as ex:
        return stored_sessions, dash.no_update, dash.no_update, ""


@app.callback(
    Output("station-dropdown", "options"),
    Output("station-dropdown", "value"),
    Output("info-session-loading", "children"),
    Output("session-dataset-dropdown", "options"),
    Output("session-dataset-dropdown", "value"),
    Input("session-dropdown", "value"),
    State("station-dropdown", "value"),
    State("session-dataset-dropdown", "value"),
    State("stored-sessions", "data")
)
def select_session(session_id, st_current, ds_current, stored_sessions):
    if not session_id:
        raise PreventUpdate

    if session_id not in loaded_sessions:
        info = stored_sessions[session_id]

        loaded_sessions[session_id] = VGOSSession(info["filepath"])

    session = loaded_sessions[session_id]

    station_options = [{"label": s, "value": s} for s in session.station_names]
    session_dataset_options = [{"label": s, "value": s} for s in session.dataset_names]

    return  (
        station_options,
        st_current if st_current in session.station_names else None,
        "",
        session_dataset_options,
        ds_current if ds_current in session.dataset_names else None
    )


@app.callback(
    Output("station-dataset-dropdown", "options"),
    Output("station-dataset-dropdown", "value"),
    Input("station-dropdown", "value"),
    State("station-dataset-dropdown", "value"),
    State("session-dropdown", "value"),
)
def update_station_datasets(station_name, ds_current, session_id):
    if not session_id or not station_name:
        return {}, None
    session = loaded_sessions[session_id]

    if session is None:
        return {}, None

    options = [{"label": s, "value": s} for s in session[station_name].datasets]

    return options, ds_current if ds_current in session[station_name].datasets else None

@app.callback(
    Output("station-variable-dropdown", "options"),
    Output("station-variable-dropdown", "value"),
    Input("station-dropdown", "value"),
    Input("station-dataset-dropdown", "value"),
    State("station-variable-dropdown", "value"),
    State("session-dropdown", "value"),
)
def update_station_variables(station_name, dataset_name, par_current, session_id):
    if not session_id or not station_name or not dataset_name:
        return {}, None
    session = loaded_sessions[session_id]

    if session is None:
        return {}, None

    options = [{"label": s, "value": s} for s in session[station_name][dataset_name].variables]

    return options, par_current if par_current in session[station_name][dataset_name].variables else None

@app.callback(
    Output("station-text", "value"),
    Input("station-dropdown", "value"),
    Input("station-dataset-dropdown", "value"),
    Input("station-variable-dropdown", "value"),
    State("session-dropdown", "value"),
)
def update_station_text(station_name, dataset_name, variable_name, session_id):
    if not session_id or not station_name or not dataset_name or not variable_name:
        return ""
    session = loaded_sessions[session_id]

    if session is None:
        return ""

    ds = session[station_name][dataset_name]
    values = ds[variable_name]

    return format_value(values)

@app.callback(
    Output("session-variable-dropdown", "options"),
    Output("session-variable-dropdown", "value"),
    Input("session-dataset-dropdown", "value"),
    State("session-variable-dropdown", "value"),
    State("session-dropdown", "value"),
)
def update_session_variables(dataset_name, par_current, session_id):
    if not session_id or not dataset_name:
        return {}, None
    session = loaded_sessions[session_id]

    if session is None:
        return {}, None

    options = [{"label": s, "value": s} for s in session[dataset_name].variables]

    return options, par_current if par_current in session[dataset_name].variables else None

@app.callback(
    Output("session-text", "value"),
    Input("session-dataset-dropdown", "value"),
    Input("session-variable-dropdown", "value"),
    State("session-dropdown","value")
)
def update_session_text(dataset_name, variable_name, session_id):
    if not session_id or not dataset_name or not variable_name:
        return ""
    session = loaded_sessions[session_id]

    if session is None:
        return ""

    ds = session[dataset_name]
    values = ds[variable_name]

    return format_value(values)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=9002)