vgosDBexplorer
--------------

vgosDBexplorer contains two tools to explore the data inside a vgosDB archive. 

- dbexplorer: shows the raw content of all the netcdf files whithin a vgosDB archive
- visexplorer: visual representation of all data within in a vgosDB archive which corresponds to the observations made in that particular session

Both tools are webapps based on the Python Dash framework and therefore run inside a web browser. The required packages can be installed via pip, e.g.

    python -m venv .venv
    . .venv/bin/activate    (on windows with powershell use .venv/scripts/activate.ps1)
    pip install -r requirements.txt
  
Start the web applications with:
 
    python dbexplorer.py (and point the webbrowser to http://127.0.0.1:9002)

or

    python visexplorer.py (and point the webbrowser to http://127.0.0.1:9003)

The purpose of `visexplorer.py` is to visualize observation data as a function of a station’s azimuth and elevation angles.
First, upload a vgosDB to the server, where it will be stored for future use, or select one of the vgosDB files already available on the server.

At minimum, you must select:
- a station and
- one of the session or station parameters for either the polar or the time-series plot.

You can further filter the displayed data by selecting a specific baseline and/or source using the corresponding controls. 

When you zoom into the time-series plot, the polar plot is updated automatically to display only the observations that fall within the selected time range and/or y-range.

`dbexplorer.py` is useful for browsing the structure of a vgosDB file and inspecting the contents of the NetCDF files contained within it.

 

  