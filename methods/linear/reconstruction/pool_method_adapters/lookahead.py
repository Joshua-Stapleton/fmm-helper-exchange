#!/usr/bin/env python3
"""Select one of K prefixes from the unchanged upstream HelperPool sampler.

This wrapper does not alter the upstream production ordering. It scores whole
paid prefixes, then completes only the selected prefix with the same driver.
The L1 score is a heuristic, not a minimum circuit distance or a lower bound.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import time

try:
    import numpy as np
except ImportError:
    np = None

HERE = Path(__file__).resolve().parent
PIN = '21906e043ab0d652b588864893a07199b915a8e7'
spec = importlib.util.spec_from_file_location('lookahead_paid', HERE/'paid.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2)+'\n')


def driver_module(path):
    """Use the sibling thin adapter by default; never discover workspace code."""
    spec = importlib.util.spec_from_file_location('lookahead_native_driver', path)
    audit.require(spec is not None and spec.loader is not None, 'Driver module not found')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    audit.require(module.PIN == PIN, 'Driver adapter has the wrong upstream pin')
    return module


def prefix_program(raw):
    """Keep every upstream sampled substitution as a paid binary gate."""
    n = raw['dimension']
    audit.require(type(n) is int and n > 0, 'Invalid native prefix dimension')
    audit.require(raw.get('expressions', []) == [], 'Sampled prefix has terminal expressions')
    substitutions = raw['substitutions']
    audit.require(isinstance(substitutions, list), 'Substitution array required')
    gates = [[s['i'], s['ai'], s['j'], s['aj']] for s in substitutions]
    if 'additions' in raw:
        audit.require(raw['additions'] == len(gates), 'Native prefix count differs from paid gates')
    return dict(inputs=n, gates=gates)


def expanded_values(program):
    # Independent replay is required before numpy sees coefficients. Python
    # integers prevent overflow in this admission check and in gate expansion.
    audit.replay(program)
    n = program['inputs']
    values = [tuple(int(i == j) for j in range(n)) for i in range(n)]
    for left, sl, right, sr in program['gates']:
        values.append(tuple(sl*x+sr*y for x, y in zip(values[left], values[right])))
    return values


def score_prefix(program, target, gate_limit=None):
    report = audit.replay(program, target=target, budget=gate_limit)
    values = expanded_values(program)
    n = program['inputs']
    audit.require(target and all(len(row) == n for row in target), 'Target dimension mismatch')
    audit.require(all(type(x) is int for row in target for x in row), 'Integer target required')
    unique_targets = sorted({audit.canonical(row)[0] for row in target})
    bound = max(abs(x) for row in list(target)+values for x in row)
    # Each signed difference is at most 2*bound. A whole ordered-target sum
    # contains at most target_rows*n such differences. Stay well inside int64.
    audit.require(2*bound*n*len(target) <= (1 << 62), 'L1 score would exceed safe int64 range')
    if np is None:
        raise ImportError('NumPy is required for lookahead scoring; target walks and paid replay use only the standard library')
    computed = np.asarray(values, dtype=np.int64)
    ordered = np.asarray(target, dtype=np.int64)
    dminus = np.abs(ordered[:, None, :]-computed[None, :, :]).sum(axis=2)
    dplus = np.abs(ordered[:, None, :]+computed[None, :, :]).sum(axis=2)
    nearest = np.minimum(dminus, dplus).min(axis=1)
    unique = np.asarray(unique_targets, dtype=np.int64)
    uminus = np.abs(unique[:, None, :]-computed[None, :, :]).sum(axis=2)
    uplus = np.abs(unique[:, None, :]+computed[None, :, :]).sum(axis=2)
    unearest = np.minimum(uminus, uplus).min(axis=1)
    l1 = int(nearest.sum())
    unique_l1 = int(unearest.sum())
    covered = report['covered_target_unique_signed_forms']
    gates = len(program['gates'])
    return dict(**report, closest_signed_l1_ordered_sum=l1,
                closest_signed_l1_unique_sum=unique_l1,
                selection_key=[l1, -covered, gates],
                l1_per_paid_gate=None if not gates else l1/gates,
                range_guard_bound=bound,
                score_scope='whole sampled prefix; ordered targets; heuristic signed L1')


def write_prefix(path, raw):
    p = prefix_program(raw)
    expanded_values(p)
    lines = [f"{p['inputs']} {len(p['gates'])}"]
    lines.extend(f'{a} {b} {sa} {sb}' for a, sa, b, sb in p['gates'])
    Path(path).write_text('\n'.join(lines)+'\n')


def native_complete_program(raw, target):
    """Expand terminals without normalization; charge every upstream operation."""
    n = len(target[0])
    audit.require(raw['dimension'] == n, 'Native completion dimension changed')
    gates = [[s['i'], s['ai'], s['j'], s['aj']] for s in raw['substitutions']]
    p = dict(inputs=n, gates=gates)
    # A solver may retain signed aliases; they remain paid here.
    audit.replay(p, require_unique=False)
    outputs = []
    for expression in raw['expressions']:
        audit.require(expression, 'Empty terminal expression')
        terms = []
        for term in expression:
            w, sign = term['index'], term['value']
            audit.require(type(w) is int and 0 <= w < n+len(raw['substitutions']), 'Invalid terminal wire')
            audit.require(type(sign) is int and sign in (-1, 1), 'Terminal has a free nonunit scalar')
            terms.append((w, sign))
        w, sign = terms[0]
        for other, other_sign in terms[1:]:
            gates.append([w, sign, other, other_sign])
            w, sign = n+len(gates)-1, 1
        outputs.append([w, sign])
    result = dict(inputs=n, gates=gates, outputs=outputs)
    check = audit.replay(result, target, require_unique=False)
    audit.require(len(gates) == raw['additions'], 'Expanded terminal count differs from native additions')
    return result, check


def write_input(path, raw_bank, target, incumbent):
    """Preserve the native internal-substitution/terminal boundary verbatim."""
    n = len(target[0])
    safe_coefficient = ((1 << 31)-1)//2
    audit.require(all(abs(x) <= safe_coefficient for row in target for x in row),
                  'Target coefficient lacks safe upstream int32 headroom')
    audit.require(raw_bank['inputs'] == n, 'Native bank dimension mismatch')
    solutions = raw_bank['solutions']
    audit.require(solutions, 'Empty native bank')
    audit.require(type(incumbent) is int and 0 <= incumbent <= min(raw['additions'] for raw in solutions),
                  'Reference exceeds the native donor minimum; upstream unsigned subtraction would underflow')
    lines = [f'{n} {len(target)} {incumbent} {len(solutions)}']
    lines.extend(' '.join(map(str, row)) for row in target)
    for raw in solutions:
        native = dict(raw, dimension=n)
        complete, _ = native_complete_program(native, target)
        subs, expressions = raw['substitutions'], raw['expressions']
        values = [tuple(int(i == j) for j in range(n)) for i in range(n)]
        for left, sl, right, sr in complete['gates']:
            value = tuple(sl*a+sr*b for a, b in zip(values[left], values[right]))
            audit.require(all(abs(x) <= safe_coefficient for x in value),
                          'A native helper or terminal sum lacks safe upstream int32 headroom')
            values.append(value)
        lines.append(f'{n} {len(subs)} {len(expressions)}')
        lines.extend(f"{s['i']} {s['j']} {s['ai']} {s['aj']}" for s in subs)
        lines.extend(' '.join([str(len(row))]+[str(x) for term in row
                     for x in (term['index'], term['value'])]) for row in expressions)
    Path(path).write_text('\n'.join(lines)+'\n')


def launch(command, timeout):
    start = time.monotonic()
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    try:
        process = subprocess.run(command, capture_output=True, text=True, timeout=timeout, env=env)
        record = dict(command=command, process_wall_seconds=time.monotonic()-start,
                      returncode=process.returncode, stderr=process.stderr,
                      stdout=process.stdout, hard_wall_allowance=timeout)
        audit.require(process.returncode == 0, 'Driver failed: '+process.stderr)
        record['result'] = json.loads(process.stdout)
        record['status'] = 'PASS'
    except subprocess.TimeoutExpired as error:
        record = dict(command=command, process_wall_seconds=time.monotonic()-start,
                      status='HARD_WALL_TIMEOUT', hard_wall_allowance=timeout,
                      stdout=error.stdout.decode() if isinstance(error.stdout, bytes) else error.stdout,
                      stderr=error.stderr.decode() if isinstance(error.stderr, bytes) else error.stderr)
    return record


def run(args):
    if np is None:
        raise ImportError('Install the optional NumPy search dependency before running lookahead scoring')
    audit.require(args.draws > 0 and 0 <= args.seed <= (1 << 32)-args.draws, 'Invalid seed/draw range')
    audit.require(type(args.gate_limit) is int and args.gate_limit >= -1, 'Invalid gate cap')
    if args.gate_limit == -1 and args.draws > 1:
        audit.require(args.extra_seed_offset > 0 and
                      args.seed+args.extra_seed_offset+args.draws-2 < (1 << 32),
                      'Invalid extra sampling seeds')
    audit.require(math.isfinite(args.seconds) and args.seconds > 0, 'Invalid solver seconds')
    audit.require(math.isfinite(args.hard_wall) and args.hard_wall > args.seconds, 'Hard wall must exceed solver budget')
    audit.require(0 <= args.solver_seed <= (1 << 32)-1, 'Invalid completion seed')
    audit.require(math.isfinite(args.temperature) and args.temperature > 0, 'Invalid temperature')
    audit.require(math.isfinite(args.epsilon) and 0 <= args.epsilon <= 1, 'Invalid epsilon')
    audit.require(args.strategy_index >= 0, 'Invalid strategy index')
    audit.require((args.input is None) != (args.bank is None), 'Choose exactly one of --input or --bank')
    if args.input is not None:
        audit.require(args.input.is_file(), 'Input payload file missing')
    else:
        audit.require(args.bank.is_file() and type(args.best) is int and args.best > 0,
                      'Native bank and positive --best reference required')
    audit.require(args.binary is not None or args.leo is not None,
                  'Supply a verified --binary or an external pinned --leo checkout')
    if args.binary is not None:
        audit.require(args.binary.is_file(), 'Driver executable missing')
    audit.require(not args.out.exists(), 'Refusing to replace experiment output')
    target = audit.read_matrix(args.matrix)
    adapter = driver_module(args.driver_module)
    args.out.mkdir(parents=True)
    start = time.monotonic()
    setup = {}
    if args.input is None:
        begin = time.monotonic()
        args.input = args.out/'input.txt'
        bank = json.loads(args.bank.read_text())
        # Independent exact integer replay before passing a donor to C++.
        write_input(args.input, bank, target, args.best)
        setup.update(raw_bank_sha256=sha(args.bank), raw_reference=args.best,
                     raw_bank_replay_and_payload_seconds=time.monotonic()-begin,
                     pool_intake='native substitutions only; original terminals remain unexpanded')
    if args.binary is None:
        begin = time.monotonic()
        args.binary = args.out/'pool_driver'
        build = adapter.build(args.leo, args.binary)
        setup['compilation_seconds'] = time.monotonic()-begin
    else:
        metadata = args.binary.with_suffix('.build.json')
        audit.require(metadata.is_file(), 'Verified driver build metadata is required')
        build = json.loads(metadata.read_text())
        setup['compilation_seconds'] = 0.
    audit.require(build['upstream_commit'] == PIN and build['executable_sha256'] == sha(args.binary),
                  'Driver pin or executable hash differs from verified build metadata')
    common = [str(args.binary.resolve()), '--input', str(args.input.resolve()),
              '--mode', args.mode, '--temperature', str(args.temperature), '--epsilon', str(args.epsilon),
              '--gate-limit', str(args.gate_limit), '--preset', args.preset,
              '--strategy-index', str(args.strategy_index), '--seconds', str(args.seconds)]
    first_draws = 1 if args.gate_limit == -1 else args.draws
    sampled = launch(common+['--sample-only', '--seed', str(args.seed), '--draws', str(first_draws)], args.hard_wall)
    dump(args.out/'sampling.json', sampled)
    if sampled['status'] != 'PASS':
        return dict(status=sampled['status'], sampling=sampled)
    sampling_records = [sampled]
    draws = list(sampled['result']['draws'])
    actual_gate_limit = draws[0]['gate_limit']
    if args.gate_limit == -1 and args.draws > 1:
        # The first prefix is exactly the ordinary weighted arm: same random
        # cap draw, same generator state, same helper sampler. Only the extra
        # candidates use fixed-cap calls, with preregistered disjoint seeds.
        extra_common = list(common)
        extra_common[extra_common.index('--gate-limit')+1] = str(actual_gate_limit)
        extra = launch(extra_common+['--sample-only', '--seed', str(args.seed+args.extra_seed_offset),
                                    '--draws', str(args.draws-1)], args.hard_wall)
        dump(args.out/'sampling_extra.json', extra)
        if extra['status'] != 'PASS':
            return dict(status=extra['status'], sampling=sampled, extra_sampling=extra)
        audit.require(extra['result']['weights'] == sampled['result']['weights'], 'Sampler donor weights changed')
        sampling_records.append(extra)
        draws.extend(extra['result']['draws'])
    audit.require(all(draw['gate_limit'] == actual_gate_limit for draw in draws), 'Sampled gate caps differ')
    audit.require(len(draws) == args.draws, 'Driver changed sample count')
    scores = []
    selection_start = time.monotonic()
    for index, draw in enumerate(draws):
        program = prefix_program(draw['prefix'])
        check = score_prefix(program, target, actual_gate_limit)
        audit.require(len(program['gates']) == draw['prefix_gates'], 'Driver prefix count mismatch')
        dump(args.out/f'prefix_{index}.json', program)
        scores.append(dict(index=index, seed=draw['seed'], sampling_seconds=draw['sampling_seconds'], **check))
    selected = min(scores, key=lambda record: (record['selection_key'], record['index']))
    selection_seconds = time.monotonic()-selection_start
    prefix_path = args.out/'selected.prefix'
    write_prefix(prefix_path, draws[selected['index']]['prefix'])
    record = dict(status='sample_only', binary_sha256=sha(args.binary), input_sha256=sha(args.input),
                  matrix_sha256=sha(args.matrix), mode=args.mode, temperature=args.temperature,
                  epsilon=args.epsilon, draws=args.draws, sampling_seed=args.seed,
                  completion_seed=args.solver_seed, gate_limit=actual_gate_limit,
                  gate_limit_policy='ordinary first-draw default 10%-50%' if args.gate_limit == -1 else 'fixed',
                  sampling_seeds=[draw['seed'] for draw in draws],
                  selection_seconds=selection_seconds, selection=selected, scores=scores,
                  sampling_process_wall_seconds=sum(r['process_wall_seconds'] for r in sampling_records),
                  sampling_pool_preparation_seconds=sum(r['result']['preparation_seconds'] for r in sampling_records),
                  signed_wire_model='strict original input/output orientation still required',
                  method='unchanged upstream HelperPool; best-of-K whole-prefix signed L1 selection',
                  upstream_pin=PIN, setup=setup, driver_build=build,
                  driver_module_sha256=sha(args.driver_module))
    if args.complete:
        completion_common = list(common)
        completion_common[completion_common.index('--gate-limit')+1] = str(actual_gate_limit)
        completed = launch(completion_common+['--prefix-file', str(prefix_path.resolve()), '--seed', str(args.solver_seed), '--draws', '1'], args.hard_wall)
        dump(args.out/'completion.json', completed)
        record['completion_process_wall_seconds'] = completed['process_wall_seconds']
        record['status'] = completed['status']
        if completed['status'] == 'PASS':
            final = completed['result']['draws'][0]
            record.update(status=final['status'], solver_seconds=final.get('solver_seconds'),
                          completion_pool_preparation_seconds=completed['result']['preparation_seconds'],
                          strategy=final.get('strategy'), completed_count=None)
            if final['solution'] is not None:
                program, check = native_complete_program(final['solution'], target)
                dump(args.out/'complete_paid.json', program)
                dump(args.out/'complete_verification.json', check)
                record['completed_count'] = len(program['gates'])
    record['end_to_end_wall_seconds'] = time.monotonic()-start
    dump(args.out/'summary.json', record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--leo', type=Path)
    parser.add_argument('--driver-module', type=Path, default=HERE/'run.py')
    parser.add_argument('--input', type=Path)
    parser.add_argument('--bank', type=Path)
    parser.add_argument('--best', type=int)
    parser.add_argument('--matrix', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=('weighted', 'uniform'), default='weighted')
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--solver-seed', type=int, required=True)
    parser.add_argument('--draws', type=int, default=4)
    parser.add_argument('--extra-seed-offset', type=int, default=1000000)
    parser.add_argument('--gate-limit', type=int, default=-1)
    parser.add_argument('--seconds', type=float, default=5)
    parser.add_argument('--hard-wall', type=float, default=10)
    parser.add_argument('--temperature', type=float, default=1)
    parser.add_argument('--epsilon', type=float, default=.01)
    parser.add_argument('--preset', choices=('distance', 'default', 'all'), default='distance')
    parser.add_argument('--strategy-index', type=int, default=0)
    parser.add_argument('--complete', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2))


if __name__ == '__main__':
    main()
