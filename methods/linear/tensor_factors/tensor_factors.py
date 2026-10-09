#!/usr/bin/env python3
"""Exact bit-axis factorization, repeated local-map extraction, and charged SLP lift."""
import argparse
import importlib.util
import itertools
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

api=module('tensor_reconstruction_api',HERE.parent/'reconstruction/common.py')
circuits=module('tensor_exact_circuits',ROOT/'methods/circuits/circuits.py')


def root_index(digits):
    depth=len(digits)
    row=sum((digit//2)<<(depth-1-axis) for axis,digit in enumerate(digits))
    column=sum((digit%2)<<(depth-1-axis) for axis,digit in enumerate(digits))
    return (2**depth)*row+column


def factor_bits(target):
    """Rows must be ternary rank-one products across paired row/column bits."""
    api.matrix_check(target)
    inputs=len(target[0]);side=math.isqrt(inputs)
    api.require(side*side==inputs and side>=2 and side&(side-1)==0,
                'Input coordinates must be a power-of-two square grid')
    depth=side.bit_length()-1
    index_map=[root_index(digits) for digits in itertools.product(range(4),repeat=depth)]
    api.require(set(index_map)==set(range(inputs)),'Input coordinate map is not a bijection')
    axes=[set() for _ in range(depth)]
    row_factors=[];signs=[]
    for row in target:
        api.require(all(x in (-1,0,1) for x in row),'This adapter requires ternary targets')
        pivot=next(i for i,x in enumerate(row) if x)
        r,c=divmod(pivot,side)
        digits=tuple(2*((r>>(depth-1-axis))&1)+((c>>(depth-1-axis))&1)
                     for axis in range(depth))
        pivot_sign=row[pivot];sign=pivot_sign;forms=[]
        for axis in range(depth):
            vector=[]
            for digit in range(4):
                coordinate=list(digits);coordinate[axis]=digit
                vector.append(row[root_index(coordinate)]*pivot_sign)
            form,orientation=api.canonical(vector)
            sign*=orientation;forms.append(form);axes[axis].add(form)
        for coordinate in itertools.product(range(4),repeat=depth):
            expected=sign*math.prod(forms[axis][digit] for axis,digit in enumerate(coordinate))
            api.require(row[root_index(coordinate)]==expected,'Target row does not factor across bit axes')
        row_factors.append(forms);signs.append(sign)
    axes=[sorted(forms) for forms in axes]
    ids=[{form:index for index,form in enumerate(forms)} for forms in axes]
    tuples=[[ids[axis][row[axis]] for axis in range(depth)] for row in row_factors]
    return dict(depth=depth,side=side,inputs=inputs,outputs=len(target),
                axis_forms=[[list(form) for form in forms] for forms in axes],
                output_factor_indices=tuples,output_signs=signs,
                input_index_map=index_map,basis_change=False,
                exact_coefficient_identities=inputs*len(target),
                coordinate_rule='digit =2*row_bit+column_bit, high bits first; original root=side*row+column')


def conditional_map(factorization,split_axis=0):
    """Extract one local map only when every outer group has exactly the same row set."""
    depth=factorization['depth'];axes=factorization['axis_forms']
    api.require(0<=split_axis<depth and depth>1,'Invalid split axis')
    remaining=[axis for axis in range(depth) if axis!=split_axis]
    groups=[set() for _ in axes[split_axis]];vectors=[]
    for indices in factorization['output_factor_indices']:
        vector=tuple(math.prod(axes[axis][indices[axis]][digit]
                              for axis,digit in zip(remaining,coordinate))
                     for coordinate in itertools.product(range(4),repeat=depth-1))
        groups[indices[split_axis]].add(vector);vectors.append(vector)
    api.require(groups and all(group==groups[0] for group in groups),
                'Outer groups do not share one identical local map')
    rows=sorted(groups[0]);ids={row:index for index,row in enumerate(rows)}
    return dict(split_axis=split_axis,remaining_axes=remaining,
                target_matrix=[list(row) for row in rows],
                local_output_indices=[ids[row] for row in vectors],
                repeated_groups=len(groups),inputs=4**(depth-1),outputs=len(rows))


def _axis_stage(table,dimensions,axis,forms,gates,inputs):
    dimensions=list(dimensions);dimensions[axis]=len(forms);result={}
    for key in itertools.product(*(range(size) for size in dimensions)):
        terms=[]
        for digit,sign in enumerate(forms[key[axis]]):
            if sign:
                coordinate=list(key);coordinate[axis]=digit
                terms.append((table[tuple(coordinate)],sign))
        wire,sign=terms[0]
        if len(terms)==1:
            api.require(sign==1,'Canonical singleton sign must be positive')
        else:
            for right,right_sign in terms[1:]:
                gates.append([wire,sign,right,right_sign])
                wire,sign=inputs+len(gates)-1,1
        result[key]=wire
    return result,dimensions


def lift(factorization,local,program,target):
    """Pay for the outer transform, then compute a local SLP separately in each group."""
    api.require(program['inputs']==local['inputs'],'Wrong local input count')
    api.require(api.exact_circuit(program,local['inputs'])==local['target_matrix'],
                'Local program differs from the extracted coefficient map')
    depth=factorization['depth'];inputs=factorization['inputs'];axis=local['split_axis']
    axes=factorization['axis_forms'];remaining=local['remaining_axes'];gates=[]
    table={coordinate:root_index(coordinate)
           for coordinate in itertools.product(range(4),repeat=depth)}
    table,_=_axis_stage(table,[4]*depth,axis,axes[axis],gates,inputs)
    outer_gates=len(gates);outputs={}
    for outside in range(local['repeated_groups']):
        references=[]
        for coordinate in itertools.product(range(4),repeat=depth-1):
            key=[0]*depth;key[axis]=outside
            for other,digit in zip(remaining,coordinate):key[other]=digit
            references.append((table[tuple(key)],1))
        for a,sa,b,sb in program['gates']:
            left,left_sign=references[a];right,right_sign=references[b]
            gates.append([left,sa*left_sign,right,sb*right_sign])
            references.append((inputs+len(gates)-1,1))
        for index,(wire,sign) in enumerate(program['outputs']):
            actual,actual_sign=references[wire]
            outputs[(outside,index)]=(actual,actual_sign*sign)
    result=[]
    for indices,sign,index in zip(factorization['output_factor_indices'],
                                  factorization['output_signs'],local['local_output_indices']):
        wire,wire_sign=outputs[(indices[axis],index)]
        result.append([wire,wire_sign*sign])
    candidate=dict(inputs=inputs,gates=gates,outputs=result,target_matrix=target,
                   additions_signed=len(gates),free_signed_wires=True,
                   outer_additions=outer_gates,
                   local_additions=len(program['gates']),
                   repeated_groups=local['repeated_groups'],basis_change=False)
    api.require(api.exact_circuit(candidate,inputs)==target,'Lift changed the original target matrix')
    api.require(len(gates)==outer_gates+local['repeated_groups']*len(program['gates']),
                'Lift gate-count identity failed')
    return candidate


def transpose(candidate):
    """Use the public exact Circuit transposer, preserving the actual target coefficients."""
    n=candidate['inputs'];c=circuits.Circuit(n);references=list(range(n))
    for a,sa,b,sb in candidate['gates']:
        references.append(c.add(c.scale(references[a],sa),c.scale(references[b],sb)))
    c.outputs=[c.scale(references[wire],sign) for wire,sign in candidate['outputs']]
    c=c.transposed();c.prune();aliases=[(i,1) for i in range(c.inputs)];gates=[]
    for node in c.nodes:
        if node['op']=='scale':
            a,sign=aliases[node['a']]
            api.require(abs(circuits.Q(node['c']))==1,'Nonunit scalar operation unsupported')
            aliases.append((a,sign*int(circuits.Q(node['c']))))
        else:
            api.require(node['op']=='add','Unsupported transposed operation')
            a,sa=aliases[node['a']];b,sb=aliases[node['b']]
            gates.append([a,sa,b,sb]);aliases.append((c.inputs+len(gates)-1,1))
    result=dict(inputs=c.inputs,gates=gates,outputs=[list(aliases[wire]) for wire in c.outputs],
                additions_signed=len(gates),free_signed_wires=True)
    expected=[list(row) for row in zip(*candidate['target_matrix'])]
    api.require(api.exact_circuit(result,c.inputs)==expected,'Transposition changed the matrix')
    result['target_matrix']=expected
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix',type=Path,required=True)
    parser.add_argument('--local-program',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--split-axis',type=int,default=0)
    parser.add_argument('--transpose',action='store_true',help='Optimize the matrix transpose and transpose the lifted program back')
    args=parser.parse_args();original=api.read_matrix(args.matrix)
    target=[list(row) for row in zip(*original)] if args.transpose else original
    factorization=factor_bits(target);local=conditional_map(factorization,args.split_axis)
    program=api.json_read(args.local_program);candidate=lift(factorization,local,program,target)
    args.out.mkdir(parents=True,exist_ok=False)
    api.dump(args.out/'factorization.json',factorization);api.dump(args.out/'local_map.json',local)
    api.dump(args.out/'lifted_candidate.json',candidate)
    if args.transpose:
        direct=transpose(candidate)
        api.require(direct['target_matrix']==original,'Original matrix was not recovered')
        api.dump(args.out/'direct_candidate.json',direct)
    else:direct=candidate
    api.dump(args.out/'donors.json',dict(inputs=direct['inputs'],circuits=[
        dict(name='charged_conditional_lift',gates=direct['gates'],outputs=direct['outputs'])]))
    report=dict(status='EXACT_ORIGINAL_MAP_PASS',source_sha256=api.hashlib.sha256(args.matrix.read_bytes()).hexdigest(),
                axis_form_counts=[len(forms) for forms in factorization['axis_forms']],
                outer_additions=candidate['outer_additions'],local_additions=candidate['local_additions'],
                groups=candidate['repeated_groups'],lifted_additions_signed=candidate['additions_signed'],
                direct_additions_signed=direct['additions_signed'],basis_change=False,
                exact_original_coefficients=len(original)*len(original[0]),free_signed_wires=True,
                scope='Exact fixed matrix; counts assume signed wires. Strict final literal programs are verified separately.')
    api.dump(args.out/'result.json',report);print(json.dumps(report,indent=2))


if __name__=='__main__':main()
