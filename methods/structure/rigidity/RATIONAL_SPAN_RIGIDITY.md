# Complete rational rank-one loci of two fixed 4x4 decompositions

8 October 2026. This is a computationally certified, fixed-decomposition result over Q. It is not a lower bound on the rank of matrix multiplication and not a uniqueness theorem for arbitrary decompositions.

## Result

Let `(a_i,b_i,c_i)`, `1<=i<=r`, be either exact rational source included here:

- `rank48_source.json`: the October 4 rank-48 4x4 source, with its output coordinate order converted to row-major;
- `rank49_source.json`: the October 4 rank-49 4x4 source, with its output coordinate order converted to row-major.

For any of the three pairs of factor spaces, put `S = span_Q(a_i tensor b_i)`, with the roles permuted for the other two pairs. Then **the only projective rational rank-one matrices in S are the r displayed pair products**. This includes arbitrary rational coefficients and arbitrarily large simultaneous changes of a basis of S.

Consequently, a rational decomposition of the same tensor whose pair products all lie in any one of these original S must use at least r terms. If it uses exactly r, it is the same decomposition up to term permutation and factor rescaling. In particular, any rank-47 rational candidate derived from the rank-48 source, or rank-48 candidate derived from the rank-49 source, must contain a pair product outside **each** of the three original pair spans.

This closes the *span-preserving replacement* route for these two sources over Q. It does not exclude moves that change a pair span, rank-increasing detours, other sources, algebraic-extension coefficients, or lower-rank matrix multiplication algorithms.

## Arithmetic premises

For rank49 use p=2; for rank48 use p=3 (halves in rank48 are units at 3). In each factor pair:

1. The r pair products remain linearly independent modulo p.
2. Complete enumeration of all projective first factors, followed by exact computation of the compatible second-factor nullspace, finds exactly the r original projective pair products over F_p.
3. At each of those points, the Jacobian of the rank-one span equations in a projective affine chart has full column rank 30 over F_p.

Each rank49 pair enumerates 65,535 first factors. Each rank48 pair enumerates 21,523,360 first factors. There are no additional points. Every nonempty second-factor kernel has dimension one. All 147 rank49 and all 144 rank48 Jacobians have rank 30.

A separate bit-plane implementation repeats all six complete domains, using last-nonzero projective charts and reverse pivot order. It reproduces every fiber-dimension histogram and matches the original first-factor directions. `verify_rigidity.py` rebuilds the annihilators over Q, verifies their exact vanishing on every original pair product, checks that every denominator is a p-unit, matches their reductions to the enumerated equations, and checks all Jacobians again. It also verifies every rational tensor coefficient of both sources.

## Proof of the rational lifting step

Write P for the r by 256 matrix whose rows are the original pair products. Its rank-r reduction supplies an r by r minor with determinant a p-adic unit. Use this minor to write a basis N of the annihilator of S. All entries of N are p-integral; their reductions cut out exactly the reduced span. These statements can alternatively be expressed in the local ring Z_(p), without assuming any theorem about p-adic geometry.

Suppose `a tensor b` is a nonzero rational rank-one point of S. Rescale a and b separately so that their entries are p-integral and each has at least one p-unit entry. The p-unit pivot minor forces the coefficients expressing `a tensor b` in P to be p-integral. Thus its reduction is a nonzero rank-one point of the reduced span, hence one of the listed original points.

Choose a unit coordinate on each factor, and divide by it to normalize those two coordinates to 1. Let x be the resulting 30 affine coordinates and x0 the normalized rational coordinates of the corresponding original point. Both are p-integral and `x = x0 (mod p)`. The span equations are degree-two polynomials f with p-integral coefficients, and `f(x)=f(x0)=0`.

If `x != x0`, let k>=1 be the smallest p-adic valuation of an entry of `x-x0`; this is a finite integer since the entries are rational. Write `x-x0 = p^k delta`, where delta is p-integral and nonzero modulo p. Exact polynomial expansion gives

    0 = [f(x0+p^k delta)-f(x0)]/p^k
      = J_f(x0) delta + p^k Q(delta).

Reduce modulo p. Full column rank of J gives `delta=0 (mod p)`, a contradiction. Therefore x=x0. No additional rational point exists. The same argument also establishes the statement over Q_p.

Finally, the r original pair products are independent. Expressing the whole tensor in this basis gives unique nonzero remaining-factor coefficients c_i. Any decomposition restricted to these projective pair directions must therefore include every one of the r directions. If there are r terms, each direction occurs once and its remaining factor is forced. This proves the consequence above.

## Reproduction

Portable replay after unpacking `rational_span_rigidity_certificate.zip` needs Python 3 and a C++17 compiler:

```
python3 -B replay.py
```

This verifies file hashes, builds the independent scanner in a temporary directory,
repeats all six complete finite-field domains and checks the exact rational premises.
`--rational-only` checks the rational premises while trusting saved scan summaries;
it is not a complete replay.

For a second enumeration implementation, build `span_scan.cpp` as `span_scan`
and run `python3 -B span_exhaust.py` in a disposable copy of this directory. Its
portable entry point loads the exact included sources and regenerates constraints.

The result depends on exhaustive computation plus the elementary proof above;
it is not a formal proof-assistant artifact. No literature-priority claim is made.
