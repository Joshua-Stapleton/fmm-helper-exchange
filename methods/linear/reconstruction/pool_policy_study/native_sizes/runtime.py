"""Resolve existing public helper sources; clone upstream only on native run."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def public_root():
    explicit=os.environ.get('FMM_HELPER_REPO')
    options=[Path(explicit).resolve()] if explicit else []
    options.extend(Path(__file__).resolve().parents)
    for path in options:
        if (path/'run.py').is_file() and (path/'methods/linear/fast_pool.py').is_file():
            return path
    raise ValueError('Put this package under fmm-helper-exchange, or set FMM_HELPER_REPO to that checkout.')


def vector_targets():
    return public_root()/'methods/linear/reconstruction/vector_targets'


def native_adapter():
    return module('portable_native_adapter',vector_targets()/'toolchain/adapter.py')


def native_binary(out,provided=None):
    out=Path(out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    if provided:
        binary=Path(provided).resolve()
        if not binary.is_file():
            raise ValueError('Native driver does not exist')
        metadata=binary.with_suffix('.build.json')
        meta=json.loads(metadata.read_text()) if metadata.exists() else dict(provenance='Caller supplied driver; source pin not attested by this wrapper.')
        meta['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
        return binary,meta
    adapter=native_adapter()
    source=out/'upstream'
    subprocess.run(['git','clone','--no-checkout','https://github.com/dronperminov/linear-expressions-optimization.git',str(source)],check=True)
    subprocess.run(['git','-C',str(source),'checkout','--detach',adapter.PIN],check=True)
    adapter.UPSTREAM=source
    binary=out/'native_driver_v2'
    return binary,adapter.build(binary)


def build_pool_engines(out):
    out=Path(out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    compiler=shutil.which('c++')
    if not compiler:
        raise ValueError('C++ compiler required for an optional pool search')
    result={}
    for label,name in [('relations','pool_relations.cpp'),('plateau','plateau.cpp')]:
        snapshot=out/name
        shutil.copyfile(public_root()/'methods/linear'/name,snapshot)
        binary=out/label
        subprocess.run([compiler,'-std=c++17','-O3',str(snapshot),'-o',str(binary)],check=True)
        result[label]=binary
    return result
