# Exact minimum 51 over a specified 784-member rank-23 transformation grid

Run `python3 -B verify.py`. Only the Python standard library and a C++17 compiler are needed. The full replay normally takes tens of seconds. `--fast` checks the source, all transformed coefficients and all native inputs without rerunning closure; it deliberately reports `DATA_ONLY_PASS`.

The grid applies the independently discovered four-term GL2 x GL2 transformation to the fixed 51-addition rank-23 source. These are different decompositions, so the older fixed-decomposition optimality theorem alone does not settle them. In this exact finite grid, the minimum kernel addition count remains **51**. Of 784 specified transformed decompositions, 757 have lower bound at least 52; the other 27 have lower bound at least 51. A simultaneous row-swap member is a term permutation of the supplied 51-addition source and attains 51.

## Exact scope

Let D be the eight primitive integer directions in [-2,2]^2, choosing the representative whose first nonzero entry is positive. A 2x2 basis is any unordered pair of different directions, with the lexicographically smaller row first. There are 28 bases. The grid contains all 28 x 28 ordered choices (P,Q). `grid.json` stores every P,Q and every exact rational factor matrix. This is not all GL2(Q) x GL2(Q), nor does it include arbitrary magnitude changes of those eight directions.

For each specified transformed decomposition, the lower model allows arbitrary independent invertible rational coordinate bases for the two inputs and output. The three linear maps use binary addition/subtraction, with free copies and signs. Nonunit scalar gates and further nonunit rank-term gauges are excluded. Boundary conversions are excluded. There is no unrestricted multiplication lower bound, new smaller kernel, runtime result, or claim of literature novelty.

## Construction and tensor audit

The grid of rank terms is [[12,21],[22,18]]. For i,j in {0,1}, replace its vectors by

    V'_i = sum_a P[i,a] V_a
    W'_j = sum_b Q[j,b] W_b
    U'_{ij} = sum_ab inverse(P)[a,i] inverse(Q)[b,j] U_ab.

All other terms remain fixed. The verifier re-derives the ordinary matrices from the supplied 51-addition program, checks all 729 source tensor coefficients, reconstructs all 784 transforms independently, and compares every potentially changed block coefficient exactly. All factors and source outputs use row-major coordinates.

## Cheap input bounds

A factor of rank 9 with N different nonzero signed targets needs at least N-9 gates: a circuit with g gates contains at most 9+g distinct nonzero signals up to sign, including its roots. Equality forces every signal, including every root, to be one of the targets.

In that equality case, each gate is a signed additive relation among targets. Any one unordered additive triple can supply at most one gate in an acyclic circuit: choosing two of its vectors as outputs of the same triple would produce a dependency cycle. Therefore fewer than N-9 additive triples excludes equality. The verifier independently recomputes the triples. It also handles any doubling relations; none changes the stated grid counts.

Every U factor has either 20 targets with at most 10 triples, or 21 targets. Hence U needs at least 12 gates. Every V factor has 20 targets with at most 9 triples, so V also needs at least 12. For 757 U factors, there are 21 targets and fewer than 12 triples, giving the stronger U bound 13.

## Complete one-helper decoder bound

Every W-transpose factor has 20 distinct signed targets of rank 9. A program with at most 12 gates can have at most one non-target signed signal among its roots and gates. With no such signal it would require a closure of 9 target roots; these are excluded. If an extra signal h is used, its first necessary relation implies h = +/-t_i +/-t_j or h = +/-t_i/2. The latter also covers a repeated-parent gate. An isolated or unused extra signal is removable and reduces to the no-helper case. This classifies h without bounding its coefficients in advance.

For every candidate h, the native enumerator checks all 9-target-root choices with h initially unavailable, and all 8-target-root choices with h available as a root. Dependency closure is exact and can only add a signal after both parents are available. It is an over-approximation if some selected roots are dependent, which is harmless for exclusion. Root subsets producing the same target closure are deduplicated, without deleting any reachable result. All 28 W factors exclude 12 gates. The native records cover 3,013,370,360 root/helper cases via 284,851,988 distinct closure tests.

Thus the transposed decoder needs at least 13 gates. Its direct decoder has 23 active product inputs and 9 outputs; the addition-only transposition offset is 23-9=14. The three-stage kernel therefore needs at least 12+12+13+14=51, and at least 52 for the 757 stronger U cases.

`one_helper.cpp` reuses the independently written exhaustive engine from the preceding fixed-333 certificate. `verify.py` independently checks the newly generated matrices, primitive-direction enumeration, triangle counts, all native inputs, and replays all native exclusions. The older upper verifier has a free-sign cost model; this package does not reinterpret it as a new literal sign-free construction.
