# Structural search methods and exact restrictions

These are reusable research methods and fixed-source results, not claims of a new multiplication rank, exponent, general uniqueness theorem, or literature priority. All arithmetic inputs are included; no private repository is needed.

## Rational pair-span rigidity

[The full statement and elementary proof](rigidity/RATIONAL_SPAN_RIGIDITY.md) concerns the supplied rational rank-48 and rank-49 4×4 decompositions. Each of their three pair-product spans contains only the original projective rational rank-one directions. Thus a lower-rank rational decomposition must leave **each** old pair span. Large replacements that remain in one old pair span cannot succeed for these sources.

The general method is to compute exact span annihilators, exhaust their rank-one loci over a small finite field, prove full projective Jacobian rank at every surviving point, and use a unit-minor/first-difference argument to exclude additional rational lifts. The two native scanners use different finite-field representations and enumeration orders. This is a reproducible computational proof plus an elementary argument, not a proof-assistant formalization.

From the repository root:

```sh
python3 -B methods/structure/rigidity/replay.py
```

Python 3.9+ and a C++17 compiler named `c++` are required. Full replay checks 64,766,685 projective first-factor cases, then 8,192 rational tensor coefficients, 60,381 annihilator identities and 291 full-rank Jacobians. The `--rational-only` option deliberately trusts saved scan summaries and is not a full replay. Temporary build products are discarded. The source matrices use ordinary row-major coordinates; source hashes and the column-major conversion provenance are retained in the JSONs.

`span_exhaust.py` exports exact finite-field constraints and runs the first scanner; its public entry point loads the included exact sources. `independent_scan.cpp` supplies the independent complete replay. [The standalone ZIP](rational_span_rigidity_certificate.zip) contains the same readable files.

## Coordinated four-term transformations

`segre_family.py` implements an exact rational GL₂ × GL₂ family on four terms of the existing 51-addition rank-23 source. The zero-based term grid is `[[12,21],[22,18]]`. If its factors are represented by a 2×2 grid U and two-vectors V,W, set

```
V' = P V,    W' = Q W,    U' = P^(-T) U Q^(-1).
```

Every invertible rational P,Q preserves the tensor; the decomposition itself can change. The source's four-term block has flattening rank four, so this isolated block cannot be replaced by three products. Run `python3 -B methods/structure/segre_family.py` for 25 exact examples and 18,225 tensor-coefficient checks. Python's `Fraction` is used throughout. The [784-member circuit study](../basis/segre_grid_floor51/README.md) applies this transformation family and proves a precisely scoped finite-grid minimum; it does not cover all P,Q.

The rank-23 source derives from the Perminov-based 51 certificate; the upstream license is retained in the basis package. The 4×4 sources are pre-existing decompositions; these experiments claim the search restrictions, not their discovery. The rank-49 factors match [Perminov’s pinned rank-49/cr159 source](https://github.com/dronperminov/FastMatrixMultiplication/blob/f200e684283c0d1a15f0efbc548439ba72fb8382/schemes/results/addition_reduced_ZT/4x4x4_m49_cr159_fv100_cn474_ZT_reduced.json), after the documented output-layout conversion.

## Invariant-layer obstruction

[INVARIANT_SUBSPACES.md](INVARIANT_SUBSPACES.md) proves that equal-dimensional paired invariant layers for all left-multiplication slices of Mₙ are ordinary column sectors. Their dimensions are multiples of n and they have invariant complements. This rules out one literal square-filtration transfer; it leaves restricted slices and more general constructions open.

## Context

The relevant prior frameworks include [Kauers–Moosbauer's flip graphs](https://arxiv.org/abs/2212.01175) and [Holtz et al.'s alternative-basis algorithms](https://epubs.siam.org/doi/10.1137/1.9781611979084.24). These results have not established a literature-priority claim.
