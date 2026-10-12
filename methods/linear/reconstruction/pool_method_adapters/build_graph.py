#!/usr/bin/env python3
"""Build the full observed binary graph from native donors and their terminals.

This deliberately materializes terminal expressions. It is the input for the
complete-target-walk experiment, not the native partial HelperPool initializer.
Weights use the original native Solution addition counts, before signed aliases
are identified in the graph. Only observed productions are inserted.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import time

import lookahead as adapter

HERE = Path(__file__).resolve().parent
DEFAULT_POOL = HERE.parents[3]/'make_pool.py'


def pool_module(path):
    spec = importlib.util.spec_from_file_location('native_observed_pool', path)
    adapter.audit.require(spec is not None and spec.loader is not None, 'Exact pool module not found')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_productions(program, ids):
    n = program['inputs']
    values = [tuple(int(i == j) for j in range(n)) for i in range(n)]
    result = []
    for a, sa, b, sb in program['gates']:
        vector = tuple(sa*x+sb*y for x, y in zip(values[a], values[b]))
        values.append(vector)
        child, sc = adapter.audit.canonical(vector)
        left, sl = adapter.audit.canonical(values[a])
        right, sr = adapter.audit.canonical(values[b])
        out = ids[child]
        pair = sorted(((ids[left], sa*sl*sc), (ids[right], sb*sr*sc)))
        production = (pair[0][0], pair[0][1], pair[1][0], pair[1][1])
        if out < n or out in (production[0], production[2]):
            continue
        result.append((out, production))
    return result


def build(bank, target, core, temperature=1., epsilon=.01):
    require = adapter.audit.require
    require(math.isfinite(temperature) and temperature > 0
            and math.isfinite(epsilon) and 0 < epsilon <= 1, 'Invalid positive temperature/uniform mixture')
    n = len(target[0])
    require(bank['inputs'] == n and bank['solutions'], 'Native bank dimension mismatch or empty bank')
    circuits = []
    costs = []
    for index, raw in enumerate(bank['solutions']):
        circuit, _ = adapter.native_complete_program(dict(raw, dimension=n), target)
        circuit['name'] = raw.get('name', 'native-donor-'+str(index))
        circuits.append(circuit)
        costs.append(len(circuit['gates']))
    counts = Counter(costs)
    best = min(costs)
    raw_weights = [math.exp(-(cost-best)/temperature)/counts[cost] for cost in costs]
    total = sum(raw_weights)
    require(math.isfinite(total) and total > 0, 'Native donor weight normalization failed')
    weighted = [(1-epsilon)*weight/total+epsilon/len(costs) for weight in raw_weights]
    uniform = [1/len(costs)]*len(costs)
    relation_weights = {'weighted':defaultdict(float), 'uniform':defaultdict(float)}

    def observed(forms, roots):
        ids = {tuple(vector): index for index, vector in enumerate(forms)}
        productions = {index:set() for index in range(roots, len(forms))}
        for index, circuit in enumerate(circuits):
            for out, production in canonical_productions(circuit, ids):
                productions[out].add(production)
                relation_weights['weighted'][(out, production)] += weighted[index]
                relation_weights['uniform'][(out, production)] += uniform[index]
        return productions

    graph = core.build_pool(dict(inputs=n, circuits=circuits,
                                 name='native-donors-observed-full-terminal-expansion'),
                            production_builder=observed)
    graph['production_weights'] = {
        mode:{output:[relation_weights[mode][(int(output), tuple(production))]
                      for production in productions]
              for output, productions in graph['productions'].items()}
        for mode in relation_weights}
    graph['donor_costs'] = costs
    graph['donor_weights'] = dict(weighted=weighted, uniform=uniform)
    graph['weight_parameters'] = dict(temperature=temperature, epsilon=epsilon,
                                     reference=min(costs), count_class_balanced=True)
    graph['scope'] = 'Full binary materialization of raw terminal expressions; not native HelperPool intake'
    return graph


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bank', type=Path, required=True)
    parser.add_argument('--matrix', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--pool-module', type=Path, default=DEFAULT_POOL)
    parser.add_argument('--temperature', type=float, default=1.)
    parser.add_argument('--epsilon', type=float, default=.01)
    args = parser.parse_args()
    adapter.audit.require(not args.out.exists(), 'Refusing to replace graph output')
    start = time.monotonic()
    graph = build(json.loads(args.bank.read_text()), adapter.audit.read_matrix(args.matrix),
                  pool_module(args.pool_module), args.temperature, args.epsilon)
    graph['source_hashes'] = dict(native_bank=adapter.sha(args.bank), matrix=adapter.sha(args.matrix))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    adapter.dump(args.out, graph)
    print(json.dumps(dict(forms=len(graph['forms']),
                          observed_productions=sum(map(len, graph['productions'].values())),
                          full_binary_incumbent=len(graph['incumbent']),
                          graph_sha256=adapter.sha(args.out),
                          preparation_seconds=time.monotonic()-start, scope=graph['scope']), indent=2))


if __name__ == '__main__':
    main()
