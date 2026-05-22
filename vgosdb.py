import tarfile
from io import BytesIO
from pathlib import PurePosixPath
from datetime import datetime

import numpy as np
import pandas as pd
import xarray as xr

from calc import radec_to_azel

class VGOSFile:

    def __init__(self, path, dataset):

        self.path = path
        self.name = PurePosixPath(path).stem
        self.ds = dataset

    @staticmethod
    def _decode_scalar(v):

        if isinstance(v, bytes):
            return v.decode("utf-8").strip("\x00 ").strip()

        return v

    @classmethod
    def _decode_array(cls, arr):

        return np.asarray([
            cls._decode_scalar(x)
            for x in arr.flatten()
        ])

    def value(self, variable):
        da = self.ds[variable]
        values = da.values

        if values.shape == ():
            return self._decode_scalar(values.item())

        if values.dtype.kind == "S":
            return self._decode_array(values)

        return values

    def __getitem__(self, key):

        return self.value(key)

    @property
    def variables(self):

        return list(self.ds.data_vars)

    def __repr__(self):

        return f"VGOSFile(path='{self.path}')"


class VGOSStation:

    def __init__(self, name, session):
        self.name = name
        self.session = session
        self._files = {}

    def coords(self):
        df = pd.DataFrame(data=[])
        print(self.session['Apriori/Station'].value('AprioriStationList'))
        print(self.session['Apriori/Station'].value('AprioriStationXYZ'))
        data = np.hstack((self.session['Apriori/Station'].value('AprioriStationList')[:,None],
                          self.session['Apriori/Station'].value('AprioriStationXYZ')))
        df = pd.DataFrame(data=data, columns=['station','X','Y','Z'])
        df = df[df.station == self.name]

    def add_file(self, dataset_name, path):
        self._files[dataset_name] = path

    @property
    def datasets(self):
        return sorted(self._files.keys())

    def load(self, dataset_name):
        path = self._files[dataset_name]
        return self.session._load_path(path)

    def __getitem__(self, item):
        if item in self._files:
            return self.load(item)
        raise KeyError(item)

    def __repr__(self):
        return (
            f"VGOSStation("
            f"name='{self.name}', "
            f"files={len(self._files)})"
        )


class VGOSSession:

    def __init__(self, archive_path):

        self.archive_path = archive_path

        self._members = {}
        self._cache = {}

        self.datasets = {}
        self.stations = {}

        self.root_folder = None

        self._scan_archive()
        self._detect_stations()

    def _scan_archive(self):

        with tarfile.open(self.archive_path, "r:gz") as tar:

            for member in tar.getmembers():

                if member.isfile() and member.name.endswith(".nc"):

                    self._members[member.name] = member

        #
        # determine common root folder
        #

        roots = {
            PurePosixPath(path).parts[0]
            for path in self._members
        }

        if len(roots) != 1:

            raise RuntimeError(
                "Archive must contain exactly one top-level folder"
            )

        self.root_folder = roots.pop()

    def _load_path(self, path):

        if path in self._cache:
            return self._cache[path]

        with tarfile.open(self.archive_path, "r:gz") as tar:
            member = self._members[path]
            raw = tar.extractfile(member).read()

        ds = xr.open_dataset(BytesIO(raw))
        wrapped = VGOSFile(path, ds)
        self._cache[path] = wrapped

        return wrapped

    def _find_baselines(self):
        bl = np.asarray(self['Observables/Baseline'].value('Baseline')).reshape(-1,2)
        hm = np.asarray(self['Observables/TimeUTC'].value('YMDHM'))+[2000,0,0,0,0]
        s = np.asarray(self['Observables/TimeUTC'].value('Second'), dtype=int)
        src = np.asarray(self['Observables/Source'].value('Source'))

        hms = np.hstack((hm, s[:,None]))
        dt = [datetime(*q) for q in hms]

        apsrc = self['Apriori/Source']
        srclist = pd.DataFrame(np.hstack((apsrc.value('AprioriSourceList')[:,None], apsrc.value('AprioriSource2000RaDec'))),
                                    columns=['src','ra','dec']).astype({'src':str, 'ra': float, 'dec': float})
        df = pd.DataFrame(data=np.vstack((dt, bl.T, src[None,:])).T, columns=['dt','st1','st2','src'])
        df = df.merge(srclist, on='src')

        apst = self['Apriori/Station']
        stlist = pd.DataFrame(np.hstack((apst.value('AprioriStationList')[:,None], apst.value('AprioriStationXYZ'))),
                              columns=['station','x','y','z']).astype({'x': float, 'y': float, 'z': float})

        df = df.merge(stlist, left_on='st1', right_on='station', suffixes=('1', '2')).drop('station', axis=1)
        df = df.merge(stlist, left_on='st2', right_on='station', suffixes=('1', '2')).drop('station', axis=1)

        df[['az1','el1']] = radec_to_azel(*[df[q].to_numpy() for q in ['ra','dec','dt','x1','y1','z1']])
        df[['az2','el2']] = radec_to_azel(*[df[q].to_numpy() for q in ['ra','dec','dt','x2','y2','z2']])

        self.baselines = df

        df[['ra','dec','dt',]]
        #print(df.to_numpy().T)

    def _find_head(self):

        for path in self._members:

            p = PurePosixPath(path)
            if len(p.parts) == 2 and p.name == "Head.nc":
                return path

        raise RuntimeError("Head.nc not found")

    def _detect_stations(self):
        head_path = self._find_head()
        self.Head = self._load_path(head_path)
        station_names = set(self.Head["StationList"])

        for path in self._members:

            p = PurePosixPath(path)

            rel = PurePosixPath(*p.parts[1:])
            parts = rel.parts
            filename = rel.stem

            if len(parts) == 1:
                self.datasets[str(rel)] = path
                continue

            top_folder = parts[0]

            # station datasets
            if top_folder in station_names:

                if top_folder not in self.stations:
                    self.stations[top_folder] = (
                        VGOSStation(top_folder, self)
                    )

                self.stations[top_folder].add_file(
                    filename,
                    path
                )

            else:
                key = str(rel.with_suffix(""))
                self.datasets[key] = path

        self._find_baselines()


    @property
    def station_names(self):

        return sorted(self.stations.keys())

    @property
    def dataset_names(self):

        return sorted(self.datasets.keys())

    def load_dataset(self, name):

        path = self.datasets[name]

        return self._load_path(path)

    def station_parameter(
        self,
        dataset_name,
        parameter,
        default=None,
        decode_strings=True
    ):

        result = {}

        for station_name, station in self.stations.items():

            #
            # dataset missing
            #

            if dataset_name not in station.files:

                result[station_name] = default
                continue

            try:

                ds = station.load(dataset_name)

                if parameter not in ds.variables:

                    result[station_name] = default
                    continue

                values = ds.ds[parameter].values

                #
                # decode strings
                #

                if (
                    decode_strings
                    and hasattr(values, "dtype")
                    and values.dtype.kind == "S"
                ):

                    values = ds._decode_array(values)

                result[station_name] = values

            except Exception as ex:

                result[station_name] = ex

        return result

    def station_parameter_df(
        self,
        dataset_name,
        parameter,
        value_name="value"
    ):
        """
        Return station parameter values as pandas DataFrame.

        Columns:
            station
            index (optional)
            value
        """

        data = self.station_parameter(
            dataset_name,
            parameter
        )

        rows = []

        for station, values in data.items():

            #
            # errors / missing values
            #

            if values is None:

                rows.append({
                    "station": station,
                    value_name: None
                })

                continue

            #
            # scalar
            #

            if np.isscalar(values):

                rows.append({
                    "station": station,
                    value_name: values
                })

                continue

            #
            # arrays
            #

            arr = np.asarray(values)

            for i, value in enumerate(arr.flatten()):

                rows.append({
                    "station": station,
                    "index": i,
                    value_name: value
                })

        return pd.DataFrame(rows)

    def __getitem__(self, item):
        # top-level datasets
        if item in self.datasets:
            return self.load_dataset(item)

        # stations
        if item in self.stations:
            return self.stations[item]
        raise KeyError(item)

    def __repr__(self):

        return (
            f"VGOSSession("
            f"root='{self.root_folder}', "
            f"datasets={len(self.datasets)}, "
            f"stations={len(self.stations)})"
        )

if __name__ == '__main__':
    pd.set_option('display.max_columns', None)

    session = VGOSSession("./R11001.tgz")
    #print(session.dataset_names)
    #print(session.station_names)
    #for f in session.HART15M.files:
    #    print(f, session.HART15M[f].variables)
    #print(session.Head.value('NumScan'))
    #print(session.Head.value('NumObs'))
    #print(session.HART15M.files)
    #print(len(session['HART15M']['Part-ZenithPathTropWet_kNMF'].value('Part-ZenithPathTropWet')))

    #print(len(session['Observables/TimeUTC'].value('YMDHM')))
    #print(session['Observables/TimeUTC'].value('YMDHM'))

    #print(session.stations)
    #print(session.datasets)
    print(session.baselines)
    print(session.baselines.memory_usage(deep=True).sum())
