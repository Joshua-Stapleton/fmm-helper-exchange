"""Exact stdlib circuit replay and repository discovery for pool policy studies."""
import hashlib
import importlib.util
import json
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2)+'\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def repository(explicit=None):
    candidates = [Path(explicit).resolve()] if explicit else Path(__file__).resolve().parents
    for parent in candidates:
        if (parent/'run.py').is_file() and (parent/'methods/linear/plateau.cpp').is_file():
            return parent
    raise ValueError('Place this study inside fmm-helper-exchange or pass --repo /path/to/repository')


def configure(explicit=None):
    root = repository(explicit)
    spec = importlib.util.spec_from_file_location('pool_policy_exact_core', root/'run.py')
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    return root, core


def replay(candidate, target):
    n = candidate['inputs']
    assert type(n) is int and n == len(target[0])
    values = [tuple(int(i==j) for j in range(n)) for i in range(n)]
    for gate in candidate['gates']:
        assert len(gate) == 4
        a, sa, b, sb = gate
        assert type(a) is type(b) is int and 0 <= a < len(values) and 0 <= b < len(values)
        assert type(sa) is type(sb) is int and sa in (-1,1) and sb in (-1,1)
        values.append(tuple(sa*x + sb*y for x,y in zip(values[a], values[b])))
    actual = []
    for wire, sign in candidate['outputs']:
        assert type(wire) is int and 0 <= wire < len(values)
        assert type(sign) is int and sign in (-1,1)
        actual.append([sign*x for x in values[wire]])
    assert actual == target, 'Circuit differs from exact ordered signed target'
    if 'target_matrix' in candidate:
        assert candidate['target_matrix'] == target
    return len(candidate['gates'])
