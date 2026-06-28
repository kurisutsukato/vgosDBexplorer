import tarfile
from functools import cached_property
from io import BytesIO
from pathlib import PurePosixPath, Path
from datetime import datetime
from time import perf_counter
import shutil

import numpy as np
import pandas as pd
import xarray as xr

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from misc import radec_to_azel

class VGOSFile:

    def __init__(self, path, dataset, numobs):

        self.path = path
        self.name = PurePosixPath(path).stem
        self.ds = dataset
        self.numobs = numobs

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

        if variable == 'QualityCode':
            res =  np.frombuffer(values, dtype='S1').astype('U')
            out = np.empty(res.shape, dtype=int)
            is_digit = np.char.isdigit(res)
            out[is_digit] = res[is_digit].astype(int)
            out[~is_digit] = -(np.char.lower(res[~is_digit]).view("U1").astype("U1").view(np.uint32) - ord("a") +1)
            return out

        if values.dtype.kind == "S":
            return self._decode_array(values)

        if values.shape == ():
            return self._decode_scalar(values.item())

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

    def init(self):
        hm = np.asarray(self['TimeUTC'].value('YMDHM'))
        if hm[:,0].max() < 2000:
            hm += [2000,0,0,0,0]
        s = np.asarray(self['TimeUTC'].value('Second'), dtype=int)

        hms = np.hstack((hm, s[:,None]))
        dt = [datetime(*q) for q in hms]

        df = pd.DataFrame({'utc':dt})
        df["utc"] = pd.to_datetime(df["utc"]).astype("datetime64[us]")
        self.utc = df

    @cached_property
    def parameters(self):
        parameters = {}
        for dsname in self.datasets:

            ds = self[dsname]

            for var in ds.variables:
                t1 = perf_counter()
                tmp = ds.value(var)

                if not np.isscalar(tmp) and tmp.shape[0] == len(self.utc):
                    if tmp.ndim > 1:
                        for n in range(tmp.shape[1]):
                            if tmp.ndim > 2:
                                for q in range(tmp.shape[2]):
                                    parameters[f'STATION|{dsname}/{var}-{n}_{q}'] = tmp[:, n, q]
                            else:
                                parameters[f'STATION|{dsname}/{var}-{n}'] = tmp[:,n]
                    else:
                        parameters[f'STATION|{dsname}/{var}'] = tmp
        return parameters
        
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

        self.archive_path = Path(archive_path)
        self.extract_dir = self._extract_archive(self.archive_path)

        self._members = {}
        self._cache = {}

        self.datasets = {}
        self.stations = {}

        self.root_folder = None

        self._scan_archive()

        head_path = self._find_head()
        self.Head = self._load_head(head_path)

        self._detect_stations()
        self._find_parameters()

    @staticmethod
    def _extract_archive(archive_path):
        """
        Extract a .tgz/.tar.gz archive into a sibling directory.

        The archive must contain exactly one top-level folder, which is
        stripped during extraction.

        Example:

            session.tgz
                session_root/
                    Head.nc
                    Observables/
                    Wettzell/

        becomes

            session/
                Head.nc
                Observables/
                Wettzell/

        Returns
        -------
        Path
            Path to the extracted directory.
        """

        archive_path = Path(archive_path)

        if archive_path.name.endswith(".tar.gz"):
            extract_dir = archive_path.parent / archive_path.name[:-7]
        elif archive_path.suffix == ".tgz":
            extract_dir = archive_path.with_suffix("")
        else:
            raise ValueError(f"Unsupported archive: {archive_path}")

        marker = extract_dir / ".complete"

        #
        # already extracted
        #
        if marker.exists():
            return extract_dir

        #
        # previous extraction failed
        #
        if extract_dir.exists():
            shutil.rmtree(extract_dir)

        extract_dir.mkdir(parents=True)

        try:
            with tarfile.open(archive_path, "r:gz") as tar:

                members = tar.getmembers()

                roots = {
                    Path(m.name).parts[0]
                    for m in members
                    if m.name
                }

                if len(roots) != 1:
                    raise RuntimeError(
                        "Archive must contain exactly one top-level folder"
                    )

                root = roots.pop()

                for member in members:

                    p = Path(member.name)

                    #
                    # skip root directory itself
                    #
                    if len(p.parts) == 1:
                        continue

                    #
                    # remove leading root folder
                    #
                    rel = Path(*p.parts[1:])

                    #
                    # sanity check
                    #
                    if ".." in rel.parts or rel.is_absolute():
                        raise RuntimeError(
                            f"Unsafe archive member: {member.name}"
                        )

                    target = extract_dir / rel

                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue

                    target.parent.mkdir(parents=True, exist_ok=True)

                    with tar.extractfile(member) as src:
                        with open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)

            marker.touch()

        except Exception:
            shutil.rmtree(extract_dir, ignore_errors=True)
            raise

        return extract_dir

    def _scan_archive(self):
        self._members = {}

        for path in self.extract_dir.rglob("*.nc"):
            rel = path.relative_to(self.extract_dir)
            self._members[str(rel.as_posix())] = path
        return

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

    def _load_head(self, path):
        if path in self._cache:
            return self._cache[path]

        ds = xr.open_dataset(self._members[path])
        self.numobs = ds['NumObs'].values[0]

        wrapped = VGOSFile(path, ds, self.numobs)
        self._cache[path] = wrapped

        return wrapped

    def _load_path(self, path):
        if path in self._cache:
            return self._cache[path]

        ds = xr.open_dataset(self._members[path])

        wrapped = VGOSFile(path, ds, self.numobs)
        self._cache[path] = wrapped
        return wrapped

        if path in self._cache:
            return self._cache[path]

        with tarfile.open(self.archive_path, "r:gz") as tar:
            member = self._members[path]
            raw = tar.extractfile(member).read()

        ds = xr.open_dataset(BytesIO(raw))

        wrapped = VGOSFile(path, ds, self.numobs)
        self._cache[path] = wrapped

        return wrapped

    def _find_parameters(self):
        self.parameters = {}
        for dsname in self.datasets:
            ds = self[dsname]
            for var in ds.variables:
                tmp = ds.value(var)
                if not np.isscalar(tmp) and tmp.shape[0] == len(self.baselines):
                    if tmp.ndim > 1:
                        for n in range(tmp.shape[1]):
                            if tmp.ndim > 2:
                                for q in range(tmp.shape[2]):
                                    self.parameters[f'{dsname}/{var}-{n}_{q}'] = tmp[:,n,q]
                            else:
                                self.parameters[f'{dsname}/{var}-{n}'] = tmp[:,n]
                    else:
                        self.parameters[f'{dsname}/{var}'] = tmp

    def _find_baselines(self):
        hm = np.asarray(self['Observables/TimeUTC'].value('YMDHM'))
        
        if hm[:, 0].max() < 2000:
            hm += [2000, 0, 0, 0, 0]

        s = np.asarray(self['Observables/TimeUTC'].value('Second'), dtype=int)
        src = np.asarray(self['Observables/Source'].value('Source'))

        hms = np.hstack((hm, s[:,None]))
        dt = [datetime(*q) for q in hms]
        self.utc = dt

        bl = np.asarray(self['Observables/Baseline'].value('Baseline')).reshape(-1,2)

        apsrc = self['Apriori/Source']
        srclist = pd.DataFrame(np.hstack((apsrc.value('AprioriSourceList')[:,None], apsrc.value('AprioriSource2000RaDec'))),
                                    columns=['src','ra','dec']).astype({'src':str, 'ra': float, 'dec': float})
        df = pd.DataFrame(data=np.vstack((dt, bl.T, src[None,:])).T, columns=['utc','st1','st2','src'])

        df = df.merge(srclist, on='src')

        apst = self['Apriori/Station']
        stlist = pd.DataFrame(np.hstack((apst.value('AprioriStationList')[:,None], apst.value('AprioriStationXYZ'))),
                              columns=['station','x','y','z']).astype({'x': float, 'y': float, 'z': float})

        df = df.merge(stlist, left_on='st1', right_on='station', suffixes=('1', '2')).drop('station', axis=1)
        df = df.merge(stlist, left_on='st2', right_on='station', suffixes=('1', '2')).drop('station', axis=1)

        df[['st1az','st1el']] = radec_to_azel(*[df[q].to_numpy() for q in ['ra','dec','utc','x1','y1','z1']])
        df[['st2az','st2el']] = radec_to_azel(*[df[q].to_numpy() for q in ['ra','dec','utc','x2','y2','z2']])
        df["baseline"] = df.apply(
            lambda r: '-'.join(sorted([r["st1"], r["st2"]])),
            axis=1
        )
        df["utc"] = pd.to_datetime(df["utc"]).astype("datetime64[us]")
        self.baselines = df

    def _find_head(self):

        for path in self._members:

            p = Path(path)
            if len(p.parts) == 1 and p.name == "Head.nc":
                return path

        raise RuntimeError("Head.nc not found")

    def _detect_stations(self):
        station_names = set(self.Head["StationList"])

        for path in self._members:
            rel = PurePosixPath(path)
            parts = rel.parts

            filename = rel.stem

            if len(parts) == 1: # head.nc
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

        for s in self.stations.values():
            s.init()

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

    session = VGOSSession("./20210531-r11001.tgz")

    #print(len(session['Observables/TimeUTC'].value('YMDHM')))
    #print(len(session['AGGO']['TimeUTC'].value('YMDHM')))

    #print(session.stations)
    #df = pd.DataFrame({'utc':session.utc, 'qual':session.parameters['Observables/QualityCode_bX/QualityCode']})
    #print(session['AGGO'].utc.merge(df, left_on='utc', right_on='utc', how='inner'))
    #print(session['AGGO'].parameters.keys())
    print(session.baselines)

    print(session.parameters.keys())