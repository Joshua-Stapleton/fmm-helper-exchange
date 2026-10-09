#!/usr/bin/env python3
"""Re-derive all source alignments, replay local kernels/lifts, and verify strict final maps."""
import importlib.util
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('tensor_factors',HERE/'tensor_factors.py')
tf=importlib.util.module_from_spec(spec);spec.loader.exec_module(tf)

def verify():
    fixture=HERE/'fixtures';manifest=tf.api.json_read(fixture/'SHA256.json')
    for name,digest in manifest.items():
        tf.api.require(Path(name).name==name,'Manifest paths must be local filenames')
        tf.api.require(tf.api.hashlib.sha256((fixture/name).read_bytes()).hexdigest()==digest,'Fixture hash mismatch: '+name)
    independent=tf.module('independent_literal',tf.ROOT/'methods/linear/independent_verify.py')
    results={}
    for side,local_count,lift_count,final_count in [('u',51,437,383),('v',49,423,375),('wt',48,416,650)]:
        original=tf.api.read_matrix(fixture/('source_w.sms' if side=='wt' else 'source_'+side+'.sms'))
        target=[list(row) for row in zip(*original)] if side=='wt' else original
        decomposition=tf.factor_bits(target);local=tf.conditional_map(decomposition)
        program=tf.api.json_read(fixture/('local_'+side+'.json'))
        tf.api.require(len(program['gates'])==local_count,'Local count changed')
        lifted=tf.lift(decomposition,local,program,target)
        tf.api.require(lifted['outer_additions']==80 and len(lifted['gates'])==lift_count,'Lift count changed')
        direct=tf.transpose(lifted) if side=='wt' else lifted
        tf.api.require(tf.api.exact_circuit(direct,len(original[0]))==original,'Lift differs from original source')
        text=fixture/('final_w.slp' if side=='wt' else 'final_'+side+'.slp')
        actual,count=independent.literal(text,len(original[0]),len(original))
        tf.api.require([list(row) for row in actual]==original and count==final_count,
                       'Final strict literal map/count mismatch')
        results[side]=dict(axis_forms=[len(forms) for forms in decomposition['axis_forms']],
                          groups=local['repeated_groups'],local_additions=local_count,
                          lifted_signed_additions=lift_count,strict_final_additions=count,
                          exact_original_coefficients=len(original)*len(original[0]))
    # These unsupported shapes must fail explicitly, rather than silently replacing factors.
    try:tf.factor_bits([[1,1,1,0,0,0]])
    except ValueError:pass
    else:raise ValueError('Nonsquare input grid accepted')
    try:tf.factor_bits([[1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1]])
    except ValueError:pass
    else:raise ValueError('Non-rank-one bit factors accepted')
    return dict(status='PASS',maps=results,strict_total=1408,products=343,basis_change=False,
                qualification='Strict total is independently replayed for the three fixed maps. Full tensor certificate is in the separate archive bundle.')

if __name__=='__main__':print(json.dumps(verify(),indent=2))
