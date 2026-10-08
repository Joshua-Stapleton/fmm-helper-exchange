# Rank-15 2x3 by 3x3 multiplication:36 core additions plus 10 conversions

Run `python3 verify.py`. This standard-library verifier checks all 324 rational tensor identities, the exact invertible basis factorizations, the JSON circuits, the independently parsed SLPs, all operation counts and all canonical-coordinate counts.

The kernel uses 15 bilinear products and36 literal binary additions/subtractions, split9+9+18. Conversion costs are2+6+2=10 more binary additions/subtractions. There are no unary negations, no nonunit scalar gates and no hidden sign-copy operations in any of the six final SLPs. The isolated ordinary-coordinate total is46 additions/subtractions plus15 products, or61 scalar operations. All6/9/6 canonical coordinates appear in the three forward factor maps.

This improves our previously selected 38-addition transformed kernel, by starting from a different decomposition. It does not contradict the 38-optimality certificate for that other decomposition. It is not a claim of a global record, universal optimality, better measured runtime, or the best ordinary-coordinate one-level total.

## Source and method

The source is Perminov's copy of the AlphaTensor scheme `schemes/known/alpha_tensor/2x3x3_m15_ZT.json`, pinned in the 2 October catalogue snapshot at repository commit64f58a5e40806bc47847b11dd8aceec043fa895d. The dense catalogue source hash is a4eb5b76ea03fbd378b882f88896d694afc86065ebf26b32b2f5373debf5a9a2. Initially only rank-term order and signs were normalized.

An exact finite-form solver jointly selected each input basis and an acyclic signed-addition circuit. The forward factors reached 9+9+9 additions; transposition changes the final factor's cost to 18. A separate target-root search retained all 9 canonical coordinates in the middle factor at the same 9-addition cost. Coupled core/conversion optimization then found the 2+6+2 boundary. Finally, one Boolean orientation solve covered all six DAGs and all 15 multiplication interfaces, removing every explicit unary minus without adding any operation. Only coordinate signs and product-one signed rank-term gauges changed in that final step.

The paired323 certificate is a cyclic rotation of this trilinear tensor. Its output dimension is9 instead of6, so the transposition offset falls by3 and the core count is33 rather than36. These dimension-dependent counts must not be compared as if they were the same multiplication shape.

## Reproducing the lower bound

Run `python3 verify_lower.py`; a C++17 compiler is required. The script derives and enumerates every active two-helper coefficient class, then replays an attainable positive control. The result proves that this fixed, numerically scaled decomposition has minimum36 additions under arbitrary invertible rational coordinate bases, using binary addition/subtraction with free signs/copies. Arbitrary nonzero term gauges and paid scalar gates are outside this lower theorem. The upper witness meets the bound even in the stricter literal no-unary-negation model.

The 12 coefficient classes yield108,114 RHS assignments and98,991 valid unordered-up-to-sign helper choices; none passes the necessary formal-relation test. The least target-quotient dimension is10, above the physical dimension 9. An independent generic relation enumerator reproduced the identical full histogram:10:807,11:14652,12:83532. Its source and replay log are included. See PROOF.md for the completeness argument.

## Running the algorithm

Flatten the2x3 left input and3x3 right input in row-major order. Apply u_boundary.slp and v_boundary.slp, then u.slp and v.slp. Multiply corresponding outputs to form15 products. Apply w.slp and w_boundary.slp. The six final outputs list the2x3 result in column-major order. Every SLP consists of copies, binary `+` and binary `-` only.

Everything in this bundle was prepared locally for review.
