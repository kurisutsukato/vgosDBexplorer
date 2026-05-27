import numpy as np
import pandas as pd

TWOPI = 2 * np.pi

def datetime64_to_jd(t):
    """
    numpy datetime64 -> Julian Date

    Parameters
    ----------
    t : np.datetime64
    """

    unix_seconds = (
        t.astype("datetime64[ns]").astype(np.int64)
        * 1e-9
    )

    return unix_seconds / 86400.0 + 2440587.5


def utc_to_gmst(utc):
    """
    Fast UTC -> GMST conversion.

    Parameters
    ----------
    utc : np.datetime64 or ndarray

    Returns
    -------
    gmst : radians in [0, 2pi)
    """

    jd = datetime64_to_jd(np.asarray(utc))

    T = (jd - 2451545.0) / 36525.0

    gmst_deg = (
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * T**2
        - T**3 / 38710000.0
    )

    gmst = np.deg2rad(gmst_deg % 360.0)

    return gmst


def radec_to_azel(
    ra,
    dec,
    utc,
    x, y, z
):
    """
    Vectorized RA/Dec -> Az/El using UTC timestamps.
    """

    ra = np.asarray(ra)
    dec = np.asarray(dec)

    gmst = utc_to_gmst(utc)

    #
    # spherical Earth lat/lon
    #

    lon = np.arctan2(y, x)

    rxy = np.hypot(x, y)

    lat = np.arctan2(z, rxy)

    #
    # local sidereal time
    #

    lst = gmst + lon

    #
    # hour angle
    #

    H = lst - ra

    sin_lat = np.sin(lat)
    cos_lat = np.cos(lat)

    sin_dec = np.sin(dec)
    cos_dec = np.cos(dec)

    sin_H = np.sin(H)
    cos_H = np.cos(H)

    #
    # ENU components
    #

    east = -cos_dec * sin_H

    north = (
        sin_dec * cos_lat
        - cos_dec * cos_H * sin_lat
    )

    up = (
        sin_dec * sin_lat
        + cos_dec * cos_H * cos_lat
    )

    az = np.arctan2(east, north)
    az = np.mod(az, TWOPI)

    el = np.arcsin(up)

    return np.array((az, el)).T*180/np.pi


def filter(current_session, st1, st2, source, parameter=None, parameter2=None):
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