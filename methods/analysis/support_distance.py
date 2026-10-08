"""A necessary elementary-column-shear bound, invariant under signed permutations.

A shear replaces one column; its support-size histogram changes in L1 by at
most2. Signed row/column permutations preserve the histogram. Therefore half
its L1 distance lower-bounds shear count even with free signed permutations.
This is not a bound for arbitrary basis conversions or fused circuit cost.
"""
from collections import Counter
from fractions import Fraction
import argparse,json
from pathlib import Path

def shear_lower_bound(A,B):
    if not A or not B or not A[0] or len(A)!=len(B) or len(A[0])!=len(B[0]):raise ValueError('equal nonempty matrix shapes required')
    n=len(A[0])
    if any(len(row)!=n for row in A+B):raise ValueError('ragged matrix')
    hist=lambda M:Counter(sum(Fraction(row[j])!=0 for row in M)for j in range(n))
    a,b=hist(A),hist(B)
    return sum(abs(a[k]-b[k])for k in a.keys()|b.keys())//2

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('input',nargs='?',type=Path);args=ap.parse_args()
    if args.input:
        data=json.loads(args.input.read_text());print(json.dumps({'minimum_column_shears':shear_lower_bound(data['A'],data['B']),'scope':__doc__}))
    else:
        I=[[1,0,0],[0,1,0],[0,0,1]];T=[[1,1,0],[0,1,0],[0,0,1]]
        assert shear_lower_bound(I,T)==1
        assert shear_lower_bound(I,[[0,-1,0],[1,0,0],[0,0,-1]])==0
        assert shear_lower_bound(I,[[1,1,1],[1,2,3],[1,4,9]])==3
        print('PASS: identity, signed permutation, one-shear and three-column controls')
