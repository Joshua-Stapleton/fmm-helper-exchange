"""Deterministic signed pair-reuse CSE adapter extracted from the pilot.
Input must be ternary; signs are free until strict whole-algorithm orientation.
"""
import collections,itertools,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"circuits"))
from circuits import Circuit

def cse(matrix):
    """Construct a literal signed CSE schedule with duplicate-target reuse."""
    width=len(matrix[0]);c=Circuit(width);wires=list(range(width));rows=[];rowids={};outputs=[]
    for source in matrix:
        nonzero=next((x for x in source if x),0)
        if not nonzero:outputs.append((None,1));continue
        sign=1 if nonzero>0 else -1;normalized=tuple(sign*x for x in source)
        if normalized not in rowids:rowids[normalized]=len(rows);rows.append({i:x for i,x in enumerate(normalized) if x})
        outputs.append((rowids[normalized],sign))
    while True:
        counts=collections.Counter()
        for row in rows:
            for a,b in itertools.combinations(sorted(row),2):counts[a,b,row[a]*row[b]]+=1
        if not counts:break
        pair,freq=min(counts.items(),key=lambda v:(-v[1],v[0]))
        if freq<2:break
        a,b,sign=pair;logical=len(wires);wires.append(c.add(wires[a],c.scale(wires[b],sign)))
        for row in rows:
            if a in row and b in row and row[a]==sign*row[b]:coef=row.pop(a);row.pop(b);row[logical]=coef
    answers=[]
    for row in rows:
        parts=[c.scale(wires[i],coef) for i,coef in sorted(row.items())]
        answer=parts[0] if parts else c.const_zero()
        for part in parts[1:]:answer=c.add(answer,part)
        answers.append(answer)
    c.outputs=[c.const_zero() if i is None else c.scale(answers[i],s) for i,s in outputs];c.check(matrix);return c
