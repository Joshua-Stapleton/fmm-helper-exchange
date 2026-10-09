# Supplied test-archive experiments, 9 October 2026

The experiment tested 25 specified ternary linear maps from nine existing matrix multiplication schemes. Exactly replayed circuits improve 24 of the supplied maps; the remaining U map already uses its proven minimum of 35 additions. The factors, ordered input/output coordinates and multiplication ranks remain fixed. All final linear programs use ordinary additions/subtractions and copies, with no standalone negations, nonunit scalar multiplications or unused assignments.

The [certificate collection](../certificates/tests_archive_20261009/README.md) contains the matrices, programs, source identifiers and independent checks. Two schemes supplied only V and W; their unchanged U factors are explicitly marked as corpus supplements. The full scheme totals below include those supplements.

## Source and search model

The base schemes are from [Andrey Perminov's FastMatrixMultiplication collection](https://github.com/dronperminov/FastMatrixMultiplication). Historical programs were recovered from the published factor data and checked against each supplied SMS matrix before reuse. The completion solver is [linear-expressions-optimization](https://github.com/dronperminov/linear-expressions-optimization/tree/2abd2fd8f15dc1c97dd24777515324f865e77504), pinned at `2abd2fd8f15dc1c97dd24777515324f865e77504`; its library was not edited.

The bounded portfolio combines small upstream rounds, partial reconstruction from a good existing program, exact intermediate-form pooling and plateau searches over alternative dependencies. Reconstruction generally uses the favorable orientation of a linear map and transposes the result back before comparison. Circuit transposition and coordinate regrouping are computation techniques; the final programs still compute the original signed matrices.

## Complete verified triples

| Scheme | Earlier additions | U | V | W | Current additions | Products |
|---|---:|---:|---:|---:|---:|---:|
| 2x4x7 | 174 | 35 | 67 | 67 | 169 | 45 |
| 3x3x14 | 361 | 49* | 123 | 183 | 355 | 101 |
| 3x4x6 | 209 | 44* | 64 | 94 | 202 | 56 |
| 4x5x7 | 400 | 89 | 112 | 178 | 379 | 104 |
| 4x5x9 | 542 | 130 | 144 | 233 | 507 | 137 |
| 4x6x7 | 517 | 114 | 140 | 215 | 469 | 123 |
| 5x6x6 | 562 | 129 | 147 | 227 | 503 | 130 |
| 6x6x7 | 769 | 185 | 186 | 334 | 705 | 183 |
| 8x8x8 | 1,661 | 383 | 375 | 650 | 1,408 | 343 |

\* Unchanged corpus-completion factors, not additional uploaded maps or newly improved results.

For the largest supplied triple, 1,408 additions and 343 products give **1,751 scalar operations** under this accounting model. These are improvements for named inputs; the table is not a comparison against every known scheme of those dimensions. Lower additions do not establish a new multiplication rank or exponent, or a practical runtime or energy gain.

## Exact verification and scope

The final independent archive audit reads the SMS entries directly from the original ZIP and checks them with a standalone integer-vector evaluator. It imports no optimizer and uses no candidate's `target_matrix`. All 147,413 ordered coefficient identities across the 25 uploaded maps pass. The literal syntax permits only copies and one binary plus or minus per gate, and all assignments must be used. The package additionally verifies the two supplemental U factors and the complete tensors.

Thus the programs have their original interface signs and coordinates; a basis conversion is not being omitted from their arithmetic counts. Numeric input permutations used while recognizing structure merely relabel existing coordinate indices, and every constructed sum/difference appears in the counted circuit.

These verification claims are stronger than observing a reducer's printed count. Timed-out calls contribute no donor unless a complete saved circuit is independently replayed. Intermediate signed-wire search representations also require a strict fixed-sign orientation and literal replay before they become final certificates.

## Structural reuse in the 8x8x8 maps

The supplied 343-output, 64-input kernels have an exact factorization across pairs of row/column bit coordinates. Each factorization was checked against all 21,952 original kernel coefficients. The bit-index regrouping is a bijection of the original 64 coordinate slots.

There are seven forms on each outer axis. The middle direction set contains fourteen forms for U/V and thirteen for W-transpose. The 343 requested outputs select conditional middle/inner combinations. Each of the seven outer groups requests the same exact 49-by-16 local map. This conditional reuse is the relevant structure; it should not be described as a plain Kronecker cube of three fixed seven-form maps. The [portable factorization module](../methods/linear/tensor_factors/README.md) re-derives these identities and constructs the charged lifts.

Evaluating the outer forms on sixteen slices costs 80 additions. Improving the shared local map, lifting it through the seven groups, and combining the resulting circuits with other donors exposes further reconnections in the complete kernel. For example, the 51-gate local U program lifts to a 437-gate donor; the full pooled search yields the independently verified 383-gate U program. All intermediate stages are charged. The W kernel is processed in transpose and then converted back to its actual original-map circuit before counting its 650 operations.

The final largest-map search fixtures are freshly reconstructed from surviving exact donors and include the known best witness. Their pool hashes match their saved records. These runs validate the frozen artifacts; they do not claim to reproduce the first discovery. Earlier auxiliary files overwritten by concurrent controllers are excluded from the release.

## Two exact fixed-map floors

The [projective-direction analyzer and proof](../methods/circuits/directions_README.md) produce elementary lower bounds over Q even when scalar copies are allowed for free.

The specified 2x4x7 U matrix has 35 distinct noncoordinate target directions, so it requires at least 35 binary linear gates. Its strict program attains 35. The transpose of the specified W matrix has 36 such directions. The live-circuit transposition count gives a W floor of `36 + 45 - 14 = 67`, attained by the strict 67-operation program.

The self-contained [U35](../certificates/tests_archive_20261009/proofs/2x4x7_U35/PROOF.md) and [W67](../certificates/tests_archive_20261009/proofs/2x4x7_W67/PROOF.md) certificates include explicit direction lists and complete proofs. These establish optimality for those two fixed linear maps, not for all multiplication schemes, bases or ranks. The other counts remain upper bounds.

## Timing and exact native pool construction

These are observed elapsed times on a shared development machine, not controlled solver-performance benchmarks. A donor/search invocation uses one worker; different maps run in parallel. Time budgets, compilation, intermediate preparation, sign orientation and verification must be distinguished from the time at which an improvement first appears.

| Stage | Observed complete-run time | Qualification |
|---|---:|---|
| Initial ten smaller-map portfolios | 32 to 75 s per map | Includes bounded donor attempts, pool/search and strict verification |
| Initial 6x6x7 U/V/W portfolios | 84 / 86 / 112 s | Native pool phases were approximately 0.19 / 0.22 / 0.20 s |
| Frozen 8x8x8 U/V/W validation | 31 / 31 / 57 s | Begins with known best witnesses; not first-discovery timings |
| One early 4x5x9 W Python pool phase | 188 s | Motivated moving identical relation enumeration to a native backend |

[`fast_pool.py`](../methods/linear/fast_pool.py) preserves the reference pool's mathematical objects and verifies every returned relation exactly in Python. The native backend is an implementation change for relation enumeration, not an additional reduction rule. Controlled checks on identical donor inputs gave equal full pool objects:

| Fixture | Forms | Productions | Python call | Native call |
|---|---:|---:|---:|---:|
| Small toy | 8 | 11 | 0.00175 s | 0.596 s |
| 2x4x14 V133 fixture | 687 | 4,473 | 6.437 s | 0.353 s |
| 3x8x8 V173 fixture | 961 | 5,910 | 12.515 s | 0.615 s |

The larger calls were about 18 and 20 times faster in these observations. The toy case was slower with the native adapter. These measurements do not imply a universal speedup, and larger end-to-end phases include further conversion and validation costs.

## Bounded negative results

Additional selected-cut and pool passes retained 2x4x7 V67 and 3x4x6 V64. Strict finite-pool CP searches for at most 66 and 63 respectively returned UNKNOWN after about 22 seconds. Their expanded pools contained 196 forms/912 productions and 206 forms/1,029 productions. UNKNOWN excludes nothing and establishes no lower bound.

For the largest kernels' local 49-by-16 maps, tested enriched dictionaries returned INFEASIBLE for requested bounds 50, 48 and 47 for U, V and W. Those models contained 104, 101 and 97 forms respectively. This excludes the requested counts only in those specified finite dictionaries and sign/operation models; it is not global optimality of the local maps.

The two direction-count proofs above have different scope: they reason about all rational binary linear circuits for the fixed matrices. Their sharpness follows from matching independently checked programs, rather than solver exhaustion of a chosen pool.
