#!/usr/bin/env python3
"""Elementary projective-direction lower bounds for one fixed rational linear map.

Each binary linear gate creates at most one new projective direction. Free scalar
copies create none. A live circuit with n used inputs, s gates and m output uses
transposes with at most (2s+m)-(n+s)=s+m-n binary accumulations. These are bounds
for the fixed supplied matrix, never a claim about all FMM schemes or bases.
"""
import argparse,hashlib,json
from fractions import Fraction as Q
from pathlib import Path

MODEL=dict(coefficient_field='Q',binary_linear_gates_counted=True,scalar_copies_free=True,fixed_input_output_coordinates=True,basis_change_optimization=False,scope='Fixed linear map only; not optimization over multiplication schemes, ranks, or changes of basis.')

def read_sms(path):
 raw=Path(path).read_bytes();lines=[r.split() for r in raw.decode('utf-8').splitlines() if r.strip() and not r.lstrip().startswith('#')]
 if not lines or len(lines[0])<2:raise ValueError('SMS header required')
 m,n=map(int,lines[0][:2])
 if min(m,n)<=0:raise ValueError('Positive dimensions required')
 a=[[Q(0)]*n for _ in range(m)];seen=set()
 for row in lines[1:]:
  if len(row)!=3:raise ValueError('SMS row column coefficient required')
  i,j=map(int,row[:2]);value=Q(row[2])
  if (i,j,value)==(0,0,0):continue
  if not (1<=i<=m and 1<=j<=n) or (i,j) in seen:raise ValueError('Invalid or repeated coordinate')
  seen.add((i,j));a[i-1][j-1]=value
 return a,hashlib.sha256(raw).hexdigest()

def directions(rows):
 result=set()
 for row in rows:
  first=next((x for x in row if x),None)
  if first is None or sum(bool(x) for x in row)<=1:continue
  result.add(tuple(x/first for x in row))
 return sorted(result)

def scalar(x):return x.numerator if x.denominator==1 else str(x)

def analyze(path,explicit=False):
 a,sha=read_sms(path);m,n=len(a),len(a[0]);columns=list(zip(*a));rowdirs=directions(a);coldirs=directions(columns)
 allinputs=all(any(row) for row in columns);alloutputs=all(any(row) for row in a);applicable=allinputs and alloutputs
 rawbound=len(coldirs)+n-m if applicable else None
 result=dict(filename=Path(path).name,source_sha256=sha,outputs=m,inputs=n,model=MODEL,row_noncoordinate_projective_directions=len(rowdirs),transpose_noncoordinate_projective_directions=len(coldirs),all_input_columns_nonzero=allinputs,all_output_rows_nonzero=alloutputs,row_direction_lower_bound=len(rowdirs),transpose_argument_applicable=applicable,transpose_argument_lower_bound=max(0,rawbound) if applicable else None,transpose_argument_formula='column_direction_count + inputs - outputs',addition_lower_bound=max(len(rowdirs),max(0,rawbound) if applicable else 0),proof='Distinct noncoordinate target directions each require a binary gate. For the transpose, reverse accumulation uses at most s+outputs-inputs gates when every input wire is used; comparing with its target-direction count yields the second bound.')
 if explicit:
  result['row_noncoordinate_classes']=[[scalar(x) for x in row] for row in rowdirs];result['transpose_noncoordinate_classes']=[[scalar(x) for x in row] for row in coldirs]
 return result

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path,nargs='+',help='SMS files or directories');parser.add_argument('--out',type=Path);parser.add_argument('--explicit-classes',action='store_true');args=parser.parse_args()
 paths=[]
 for source in args.source:paths.extend(sorted(source.glob('*.sms')) if source.is_dir() else [source])
 if not paths:raise ValueError('No SMS files')
 results=[analyze(p,args.explicit_classes) for p in paths];report=dict(model=MODEL,results=results)
 if args.out:args.out.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps([dict(filename=d['filename'],rows=d['outputs'],columns=d['inputs'],row_bound=d['row_direction_lower_bound'],transpose_bound=d['transpose_argument_lower_bound'],lower_bound=d['addition_lower_bound']) for d in results],indent=2))
if __name__=='__main__':main()
