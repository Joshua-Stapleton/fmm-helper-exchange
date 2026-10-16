#!/usr/bin/env python3
"""Repeat existing joint product-sign orientation on the supplied three DAGs.

Requires OR-Tools and the public fmm-helper-exchange methods/linear directory.
Example: python3 reproduce_joint_signs.py --methods METHODS_LINEAR --out rerun
"""
import argparse
import json
from pathlib import Path
import sys
import time
HERE=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--methods',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--seconds',type=float,default=10)
    args=parser.parse_args();sys.path.insert(0,str(args.methods.resolve()))
    from orient import orient,matrix
    initial={f.lower():json.loads((HERE/'input_candidates'/(f+'.json')).read_text()) for f in 'UVW'}
    started=time.monotonic();literal=orient(initial,seconds=args.seconds)
    args.out.mkdir(parents=True,exist_ok=False)
    for side,circuit in literal.items():
        width=circuit['inputs'];label=lambda w:'i'+str(w) if w<width else 't'+str(w-width)
        lines=[f"t{i}:={label(g['a'])}{'+' if g['op']=='add' else '-'}{label(g['b'])};" for i,g in enumerate(circuit['nodes'])]
        lines.extend(f'o{i}:={label(w)};' for i,w in enumerate(circuit['outputs']))
        candidate=dict(inputs=width,gates=[[g['a'],1,g['b'],1 if g['op']=='add' else -1] for g in circuit['nodes']],outputs=[[w,1] for w in circuit['outputs']])
        target=matrix(candidate);candidate['target_matrix']=target;factor=side.upper()
        (args.out/(factor+'.json')).write_text(json.dumps(candidate,indent=2)+'\n')
        (args.out/(factor+'.slp')).write_text('\n'.join(lines)+'\n')
        (args.out/(factor+'.sms')).write_text(f'{len(target)} {width} R\n'+''.join(f'{i+1} {j+1} {x}\n' for i,row in enumerate(target) for j,x in enumerate(row) if x)+'0 0 0\n')
    report=dict(status='COMPENSATED_PRODUCT_SIGNS_ORIENTED',phase_counts={s.upper():len(c['nodes']) for s,c in literal.items()},elapsed_seconds=time.monotonic()-started,basis_change=False,orientation_seconds=args.seconds,solver_threads=1,method='Existing methods/linear/orient.py joint orientation',scope='Individual factor signs may change; run the supplied independent coefficient and tensor verifier on returned files.')
    (args.out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
