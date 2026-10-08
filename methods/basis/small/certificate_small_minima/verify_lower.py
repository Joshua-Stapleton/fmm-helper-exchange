"""Reproduce the complete three- and four-helper lower bounds, using Python and C++17.

No numeric optimization package is required. See PROOF.md for the mathematical
reduction from arbitrary rational bases to these finite exact enumerations.
"""
from pathlib import Path
from fractions import Fraction as Q
from itertools import combinations_with_replacement
from math import lcm
import json, subprocess, shutil, platform, os, argparse
from three_helper_patterns import patterns, det, canon as canonical_matrix
from itertools import combinations

HERE = Path(__file__).resolve().parent

def canonical(v):
    v = tuple(v)
    return tuple(-x for x in v) if next((x for x in v if x), 0) < 0 else v

def row_type(r):
    a = sorted(abs(x) for x in r if x)
    return 2 if a == [1] else 1 if a in ([2], [1, 1]) else 0

def determinant(A):
    n=len(A)
    if n==1:return A[0][0]
    return sum((-1)**j*A[0][j]*determinant([r[:j]+r[j+1:] for r in A[1:]]) for j in range(n))

def adjugate(A):
    n=len(A)
    return [[(-1)**(i+j)*determinant([[A[r][c] for c in range(n) if c!=i] for r in range(n) if r!=j]) for j in range(n)] for i in range(n)]

def compile_program(name):
    command = [os.environ.get('CXX', 'c++'), '-O3', '-std=c++17']
    clt = Path('/Library/Developer/CommandLineTools')
    if platform.system() == 'Darwin' and 'CXX' not in os.environ and (clt/'usr/bin/clang++').exists():
        command = [str(clt/'usr/bin/clang++'), '-O3', '-std=c++17',
                   '-isysroot', str(clt/'SDKs/MacOSX.sdk'), '-B'+str(clt/'usr/bin')]
    binary = HERE/'replay'/name
    subprocess.run(command + [str(HERE/(name+'.cpp')), '-o', str(binary)], check=True)
    return binary

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--case',choices=['233','234','234_46']);args=parser.parse_args()
    replay = HERE/'replay'; replay.mkdir(exist_ok=True)
    rows = patterns()
    orbits = sorted({canonical_matrix(A) for A in combinations(rows, 3) if det(A)})
    active = [A for A in orbits if any(row_type(r) for r in A)]
    non_diagonal = [A for A in active if not all(sum(bool(x) for x in r) == 1 for r in A)]
    assert (len(rows), len(orbits), len(active), len(non_diagonal)) == (28, 154, 124, 120)
    natives = {3:compile_program('complete_three'),4:compile_program('complete_four_symmetric')}
    p4bin = compile_program('four_patterns')
    p4 = json.loads(subprocess.run([str(p4bin)],capture_output=True,text=True,check=True).stdout)['patterns']
    assert len(p4)==1911
    pool_native = compile_program('triple_quotient')
    results = {}
    for shape in ([args.case] if args.case else ['233','234','234_46']):
        data = json.loads((HERE/f'scheme{shape}.json').read_text())
        h = 4 if shape=='233' else 3
        active_here = [p['A'] for p in p4] if h==4 else active
        remaining = [A for A in active_here if not all(sum(bool(x) for x in r)==1 for r in A)]
        assert len(remaining)==(1906 if h==4 else 120)
        T = sorted({canonical(map(Q, r)) for r in data['inner_forward']['v']})
        q, d = len(T), len(T[0]); dest = replay/shape; dest.mkdir(exist_ok=True)
        pair = {canonical(a+s*b for a,b in zip(x,y))
                for x,y in combinations_with_replacement(T,2) for s in (-1,1)}
        pair = {v for v in pair if any(v)}
        helpers = sorted((pair | {canonical(x/2 for x in t) for t in T}) - set(T))
        assert len(pair-set(T)) > 4  # padding of every smaller helper count
        forms = T+helpers; index = {v:i for i,v in enumerate(forms)}; relations = set()
        for i,j in combinations_with_replacement(range(len(forms)),2):
            for s in (-1,1):
                v = canonical(a+s*b for a,b in zip(forms[i], forms[j]))
                if v in index: relations.add(tuple(sorted((i,j,index[v]))))
        pool_input = dest/'anchor_input.txt'
        pool_input.write_text(f'{q} {d} {len(helpers)} {len(relations)}\n' +
                              ''.join(' '.join(map(str,r))+'\n' for r in sorted(relations)))
        cp = subprocess.run([str(pool_native),str(pool_input),str(dest/'anchor_passes.txt'),str(h)],
                            capture_output=True,text=True,check=True)
        anchor = json.loads(cp.stdout); assert anchor['quotient_passes'] == 0, anchor
        scale = lcm(*(abs(determinant(A)) for A in active_here))*lcm(*(x.denominator for t in T for x in t))
        text = f'{q} {d} {len(remaining)}\n'
        text += ''.join(' '.join(str(int(x*scale)) for x in t)+'\n' for t in T)
        for A in remaining:
            ad = adjugate(A); de = determinant(A)
            assert [[sum(A[i][k]*ad[k][j] for k in range(h)) for j in range(h)] for i in range(h)] == [[de*int(i==j) for j in range(h)] for i in range(h)]
            text += ' '.join(map(str,[de]+[row_type(r) for r in A]+[x for r in ad for x in r]))+'\n'
        inp = dest/'complete_input.txt'; inp.write_text(text)
        cp = subprocess.run([str(natives[h]),str(inp),str(dest/'complete_passes.txt')],capture_output=True,text=True,check=True)
        (dest/'complete.log').write_text(cp.stdout)
        exhaustive = json.loads(cp.stdout.splitlines()[-1]); assert exhaustive['complete'] and exhaustive['passes'] == 0
        forward_v = q-d+h+1
        trivial = {s: len({canonical(map(Q,r)) for r in data['inner_forward'][s]})-len(data['inner_forward'][s][0]) for s in ('u','w')}
        offset = data['source']['m']-len(data['inner_forward']['w'][0])
        lower = trivial['u']+forward_v+trivial['w']+offset
        assert lower == {'233':38,'234':48,'234_46':46}[shape]
        results[shape] = {'status':'PASS','kernel_lower_bound':lower,'known_kernel_upper_bound':data['kernel_additions'],
                          'anchor':anchor,'helper_count':h,'complete_helper_exhaustive':exhaustive,
                          'scope':'Fixed target scalings, arbitrary rational entry bases, signed-addition-only kernels; free signs/copies.'}
        print(shape, json.dumps(results[shape]), flush=True)
    (replay/('verified_'+args.case+'.json' if args.case else 'verified_lower_bounds.json')).write_text(json.dumps(results,indent=2)+'\n')

if __name__ == '__main__': main()
