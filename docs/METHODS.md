# Methods, evidence and boundaries

## One reusable search representation

Represent every intermediate sum by its exact coefficient vector. Pool forms from multiple valid programs for the same map, identify only a vector and its negative, and retain its magnitude. Enumerate exact signed binary productions. This makes a circuit a constructible set of forms rather than a fixed wiring of a previous SLP.

Helper exchange removes incumbent optional forms and inserts new ones. Recompute the entire forward closure after each insertion, reconstruct an acyclic program, and prune unused work. New expressions can be useful together although neither helps alone. `exchange.cpp` supplies the small complete neighborhood; `methods/linear/plateau.cpp` keeps unseen equal-cost helper sets and perturbs larger groups; `beam.cpp` prunes insertions heuristically. The latter two do not prove exhaustion.

Linked-pair generation uses exact target/helper identities to propose cooperating forms. Reachability cuts give a necessary condition: if closure reaches R but misses a target, a successful extension must select some outside form with a production whose parents lie in R. The first new gate of any successful circuit proves this cut. Repeated necessary cuts can reject subsets without explicitly choosing every gate in the solver, but a timeout is not an exclusion.

Donors from a worse overall program can contain useful individual forms. The5×5 U experiment provides a controlled example: the enriched pool's three-for-two neighborhood exhausted without success while equal-cost exploration reached87. The output improvement also follows from a simpler two-for-one exchange in the enriched pool. This evidence separates search reach from pool quality; it does not prove that any one upstream scorer is indispensable.

## Partial reconstruction outside a fixed pool

Perminov's `solution_optimization` branch at commit `2abd2fd8f15dc1c97dd24777515324f865e77504` introduces solving from a partial existing program. Its round scheduler favors lower-cost prior solutions and retains individual steps with probability1/2, conditional on retaining their parents. A chain of d dependent noninput gates survives with probability2^-d. The CLI exports only its best final program; retaining round populations can expose further donor diversity.

Our [reconstruction module](../methods/linear/reconstruction/README.md) can select one to three nearby gates, remove them and their descendants, compact the unaffected computation and call the unchanged upstream solver with retention1. This permits replacement forms outside the original finite pool. An optimistic ranking margin is the number of removed gates minus the number of lost distinct noninput target forms: each lost form needs a newly computed gate while the retained computation remains fixed. This is a repair heuristic, not a global addition lower bound.

The certified3×6×8 V repair replaces9 gates by8, reducing159 to158 with fixed signs. Pooling separately repaired159-or-worse donors also reaches158. Adjustable-retention donors for3×8×8 V all cost at least174, but their combined pool yields173. Conversely, random ordering of the same structured cut groups found158 faster than the current ranking. This validates these repair and combination witnesses, not superiority of the ranking or general SLP-minimizer performance. [The dated report](experiments-20261009.md) distinguishes donor generation, pool construction, discovery time, continued search budgets and verification.

## Basis transformations and exact feasibility

For a right shear I+sE_ij, only column j changes. Bitset sign compatibility decides ternarity exactly; support creation minus cancellation gives the exact nonzero delta. Joint common-destination moves may have a ternary endpoint even if constituent intermediate states fail. Looking at both orders gives a necessary endpoint repair screen, with exact replay of survivors.

Sparse identity perturbations permit small determinant/inverse calculations. Disjoint shears have additive sparsity savings, so a cardinality-constrained matching solves that specified sparsity problem exactly. It does not solve addition minimization. Column sign/permutation canonicalization removes equivalent coordinate labels under the free-sign model, and Gram-invariant screening can discover exact signed symmetries that transfer circuits between factors.

Matrix-index sandwiching preserves the ordinary multiplication tensor. Independent flattened-coordinate bases instead change its interfaces: their input/output conversions must be counted. A helper in old coordinates becomes `v C_old C_new^-1` in new coordinates; this permits pooling across bases, without making physical conversions free.

## Joint selection and strict accounting

The finite-pool CP models select forms, gate productions, increasing depths, and optionally root bases. Requiring a full-rank target set to be reached from exactly d roots enforces root independence; exact inversion/replay verifies each witness. A second linked DAG can represent basis conversion, exposing kernel/boundary tradeoffs. These are finite candidate models; they do not enumerate every rational SLP.

Searches often treat signs as free. A literal gate can perform x+y, x−y or y−x at one operation, while −x−y needs a different orientation or extra negation. Strict orientation chooses internal and term signs jointly; the three factors' term signs must multiply to+1. The final certificates independently replay literal programs and distinguish additions, unary negations, nonunit scaling, products and conversions. Transposition is checked as a linear map, not assumed from a count alone.

## Complete helper-budget exclusions

For q distinct signed targets in dimension d, at least q−d binary gates are required. Near that floor, only a few non-target forms can occur, including free input roots. Their earliest necessary relations constrain possible rational helpers. Complete coefficient-pattern enumeration and exact inversion generate finite domains; exhaustive closure over root subsets excludes budgets. The proofs include their treatment of proportional targets and doubling.

The fixed3×3 source and the784 specified Segre-transformed decompositions have minimum51 in their stated separate-factor, fixed-term-scale models. The latter changes the decomposition itself. It does not cover all rational2×2 transforms, arbitrary term gauges, mixed-interface circuits, or paid nonunit-scalar gates. Smaller-source kernel and fully canonical staged-boundary theorems likewise have separate assumptions.

## Decomposition changes and structural restrictions

The four-term Segre move changes V,W by invertible P,Q and the corresponding U block by P^(-T) U Q^(-1), preserving the tensor exactly. The structural package also computes annihilators of pair-product spans and exhausts rank-one points over small finite fields. A p-unit pivot minor and full projective Jacobian rank turn the complete finite-field census into a rational span-rigidity statement for the two pinned4×4 sources.

Any lower-rank rational decomposition must therefore leave each old pair span. This closes a replacement family, not the global rank question. Span-changing moves, rank-increasing detours, other sources and algebraic extensions remain open.

## Practical accounting and experiment management

The SQLite queue keys literal exact maps and reducer implementations/configurations/seeds, validates every output, preserves leases and failures, and reports factor portfolios separately from a single reducer's run. It is an explicit local harness, not an unattended service.

Fixed-DAG storage scheduling minimizes a specified live-buffer model without changing arithmetic. Recurrence scripts include basis boundaries and classical cutoffs. Roundoff scripts use exact rational propagation, distinguish first-order and all-orders envelopes, and include conversions. None establishes a measured runtime or bandwidth improvement.

## Publication scope

This release preserves the reusable implementations and representative certificates for the methods above, including unsuccessful finite searches that delimit their reach. Repetitive campaign launchers, superseded duplicates, private collaboration material, raw logs, and upstream dependency checkouts are excluded. The original experiment path and content hash remain in module provenance. Algorithms and classical tools retain attribution; no claim of general novelty, global SOTA, or global optimality follows from their inclusion.
