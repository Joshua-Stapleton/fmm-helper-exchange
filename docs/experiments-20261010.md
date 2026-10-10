# Fixed-map experiments, 10 October 2026

For Andrey Perminov's **5×7×7 scheme with 176 products**, the verified addition counts
are now **U 180 + V 205 + W 316 = 701**, compared with **U 205 + V 236 + W 347 = 788**
in the source program. These are binary additions/subtractions in the original
coordinates, with no extra negations or nonunit scalar operations. The uploaded
V map alone improved from **236 to 205**. The bilinear rank remains 176.

The source is from [Andrey Perminov's collection](https://github.com/dronperminov/FastMatrixMultiplication).
The [certificate bundle](../certificates/scheme_5x7x7_176/README.md) contains the
source, all three original signed matrices, executable programs and an exact
verifier. This is an improvement for that fixed scheme, not a global optimality,
runtime, exponent or priority claim.

## What produced the new programs

The new [output-forest method](../methods/linear/reconstruction/output_forest.py)
chooses signed relations between target forms. For a child output, compute a
residual `r_i = y_i - s_i*y_parent` from the original inputs, then reconstruct
`y_i = r_i + s_i*y_parent`. Root outputs are computed directly. Every residual
computation and every reconstruction addition is charged. Acyclic parent links
make the reconstruction valid in the original output coordinates.

The [winning standalone V forest](../methods/linear/reconstruction/forest_pilot/winning_forest/compatibility.json)
used 80 additions for 94 distinct residual forms and 147 reconstruction additions:
227 before merging duplicate computations, 224 afterward. Repairing and repooling
these programs supplied additional vectors and identities. The expanded finite
pool reached V 205 with the existing reconnection search; removing and rebuilding
also reached 205. The original-donor-only control pool reached 225 in its bounded
run. The U program reached 180. For W, a 175-addition program for the transposed
linear map was transposed back with all reverse accumulations charged, yielding
W 316. The final literal certificates verify the original U, V and W separately.

## Intelligent partial starts: useful pilot, limited attribution

[Marginal chain selection](../methods/linear/reconstruction/gain_starts.py) scores
the reduction in signed L1 target proximity from **every imported ancestor**, plus
new target coverage, per actual added gate. It encourages complementary donors
and randomly chooses among the best scored chains. This distance is a heuristic
proxy, not shortest-circuit distance. The initial chains retain their real costs;
they are never additional free inputs.

A frozen 20-donor bank was tested with matching seeds and three starts per cell.
The per-completion limit was 8 seconds. Entries are the best completed signed
counts; parentheses show completed starts out of three.

| Paid initial gates | Existing random selector | Marginal chain gain |
|---:|---:|---:|
| 180 | 228 (3/3) | 218 (3/3) |
| 210 | 229 (3/3) | 220 (3/3) |
| 130 | 223 (2/3) | 217 (3/3) |
| 80 | timeout (0/3) | 213 (3/3) |
| 40 | timeout (0/3) | timeout (0/3) |

The best 213 has a strict literal certificate. The 30 starts took 169.47 seconds
including start assembly, completion and exact checks, excluding bank preparation,
selector precomputation and driver compilation. Target coverage was allowed to
differ because improving it is the selector's objective. This is one-map pilot
evidence, not a general solver benchmark.

A matched followup on 23 donors compared an
[exact target-pair bonus](../methods/linear/reconstruction/pair_starts.py) against
L1-only selection: nine starts each, budgets 90/140/180, identical bank and seeds.
The pair bonus completed in 24.10 seconds with best 217; L1-only completed in 34.56
seconds with best 211, also strictly certified. Both completed 9/9. The chosen pair
weight was faster but worse in additions; neither improved on V 205.

The [leave-direct-completions-out ablation](../methods/linear/reconstruction/forest_pilot/intelligent/ablation/summary.json)
removed all 20 direct completions from the frozen 270-donor expanded bank. The
remaining 250 donors still reached 205 with the same seed 577002, width 10 and
80-second search budget. The 19 forms unique to the removed completions were not
used by the full-pool 205 program. Thus these direct partial-start completions do
not explain a uniquely necessary contribution to 205. This does not exclude
indirect ancestry or future benefits from such starts.

## Cross-map controls and failures

Twenty fresh forests were tried for each prior V record, then pooled with the
existing best and searched for 30 seconds. The records remained **3×4×7: 78**,
**5×5×8: 161**, and **2×4×14: 133**; standalone forests reached 84, 179, 154
respectively. An 8×8×8 control produced no accepted candidate in 12 five-second
calls. Those timeouts are budget failures, not impossibility results.

[Compact evidence and replay instructions](../methods/linear/reconstruction/forest_pilot/intelligent/README.md)
include frozen banks, all 48 partial starts, 38 exact completions, ten timeouts,
strict witnesses, matched controls and ablation data. The final 701-addition full
scheme has 176 multiplications, hence 877 arithmetic operations under the stated
addition/multiplication convention. Its measured implementation speed and global
optimality remain open.
