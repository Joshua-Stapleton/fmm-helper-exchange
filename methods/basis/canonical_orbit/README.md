# Canonical vectors: c <= 20 on the 204 orbit, and c = 32 for the square alternative basis

30 September 2026. Research experiment prepared by Joshua Stapleton.

Historical witness: the 174 kernel is superseded by the adjacent 169/43 certificate. This package is retained for the orbit bound and canonical-coordinate method.

## 1. Ordinary coordinates: c = 20 is optimal on the de Groote orbit

```sh
python3 orbit_bound.py
```

This takes about 2 s and needs only the Python standard library. It shows that each of
L, R and P has **at most 10** canonical vectors at every point of the de Groote orbit of
the 204 scheme. Hence c = canonical(L) + canonical(R) <= 20, and the 204 point (10/10/10)
attains it.

The argument:

1. **Only rank-one factors can become canonical.** An isotropy acts on each factor matrix
   by M -> X M Y with X, Y invertible 4x4, so it preserves the rank of every factor. A
   canonical row (or column) is a matrix unit, which has rank one.
2. **Each factor has the same line structure.** Each of L, R and P has exactly 32 rank-one
   factors x y^T. Their left vectors lie on only 8 lines, and so do their right vectors;
   each line is used 4 times and no (x, y) pair repeats. The 8 lines form two 4-line
   frames: the standard one and its dual partner across the shared space.
3. **The condition for a canonical factor.** x y^T becomes a matrix unit exactly when X x
   and Y^T y are coordinate vectors. That is, x lies on one of the 4 lines X^-1 e_1..e_4,
   which are linearly independent, and y likewise.
4. **The count.** The script enumerates every independent set of at most 4 left lines and
   every independent set of at most 4 right lines. It counts the rank-one factors in each
   resulting grid; the maximum is **10** for each of L, R and P.
   - Dropping independence would allow 12, but only with dependent lines.
   - So the bound comes from linear independence, not from the incidence pattern alone.
The independent per-factor bound above suffices for c <= 20. Historical comparisons
to other decompositions are omitted here because their source matrices are not part
of this standalone certificate. The result is specific to this de Groote orbit.

## 2. Square alternative basis: c = 32 with the 174 kernel

Clement's decomposition is right: with 16 rows L_1 of L, CoB_L = Phi = L_1 and
ALT_L = [Id; M] with M = L_2 L_1^-1. **There is no general argument that M costs as little
as L.** For a random choice of L_1 it costs more.

The claim is empirical and certified for a specific choice of rows,
S = [1, 5, 7, 8, 18, 20, 21, 22, 23, 27, 28, 30, 33, 39, 43, 47] (0-based rows of the 204 L).
For these rows, M is ternary with 136 non-zeros, compared with 146 non-zeros and 2 non-units
for the published 13-canonical ALT_L. It has a **44-operation** SLP, the same count as the
published ALT_L.

How S was found:

1. About 10^4 subsets were screened by sparsity.
2. A beam search was scored by PLinOpt cost.
3. Exact z3 form-pool circuit extraction and sign propagation finished the search.

Eight different bases reach 44. At bound 43 the pool search was UNSAT for five of them and timed out
for the other three; neither outcome is a lower bound.

The other factors:

- **R.** ALT_R follows from ALT_L through the exact L/R symmetry (row and column
  permutations with signs), so it also costs 44 and has 16 canonical rows.
- **P.** ALT_P and CoB_P are the published ones (86 operations, 15 canonical columns). P's
  canonical vectors do not affect c.

| | published square ALT | this bundle |
|---|---:|---:|
| kernel L+R+P | 44+44+86 = 174 | 44+44+86 = 174 |
| canonical rows ALT_L / ALT_R / columns ALT_P | 13 / 13 / 15 | **16 / 16** / 15 |
| c (Lemma 4.1) | 26 | **32** |
| conversions CoB_L+CoB_R+CoB_P | 27+27+28 = 82 | 41+41+28 = 110 |

The extra conversion work only enters the n^2 log n term: +2.9% total operations at
n = 64 and +0.6% at n = 1024. The leading constant is unchanged.

## Verify

```sh
python3 verify.py
```

The verifier uses only the standard library and writes `verification.json`. It checks:

- the Brent identities of (L, R, P);
- ALT_L·CoB_L = L, ALT_R·CoB_R = R and CoB_P·ALT_P = P;
- that every SLP computes its matrix, with literal operation counts (strict model:
  zero explicit unary negations);
- canonical counts;
- 25 random one-level executions;
- a two-level recursive 16x16 execution with Kronecker-power changes of basis.

PLinOpt `SLPchecker -M` passes for all six maps.
