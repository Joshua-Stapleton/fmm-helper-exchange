#!/usr/bin/env python3
"""Optional rerun of exported finite model; requires matching OR-Tools."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import ortools
from google.protobuf import text_format
from ortools.sat import cp_model_pb2
from ortools.sat.python import cp_model

HERE=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bound',type=int,choices=[87,88],default=87)
    p.add_argument('--seconds',type=float,default=30);p.add_argument('--seed',type=int,default=11115001)
    a=p.parse_args();assert 0<a.seconds<=60
    path=HERE/f'bound{a.bound}.model.pb';manifest=json.loads((HERE/'MANIFEST.json').read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest['files'][path.name]
    proto=cp_model_pb2.CpModelProto();proto.ParseFromString(path.read_bytes());model=cp_model.CpModel()
    assert model.Proto().parse_text_format(text_format.MessageToString(proto))
    assert not model.validate()
    solver=cp_model.CpSolver();solver.parameters.num_search_workers=1
    solver.parameters.max_time_in_seconds=a.seconds;solver.parameters.random_seed=a.seed
    start=time.monotonic();status=solver.solve(model)
    print(json.dumps(dict(status=solver.status_name(status),bound=a.bound,workers=1,
                         ortools_version=ortools.__version__,seconds_allowance=a.seconds,
                         python_monotonic_seconds=time.monotonic()-start,solver_wall_seconds=solver.wall_time,
                         model_sha256=manifest['files'][path.name],
                         scope='This finite exported signed production model only; no global lower bound'),indent=2))


if __name__=='__main__':main()
