# Fixed-scheme optimality of the 51-addition 3x3 kernel

Unpack and run:

    python3 -I -B verify.py

Only Python's standard library is needed. It re-derives the coefficients from the
unchanged `333.json`, verifies the complete matrix-multiplication identity, and
repeats the exhaustive lower-bound checks. A separately written C++ implementation
is included as an independent cross-check:

    c++ -O3 -std=c++17 independent.cpp -o /tmp/fmm333-one-helper
    /tmp/fmm333-one-helper W_targets_scaled2.txt

The Python verifier checks that the C++ target file is exactly the transposed
output map derived from the supplied 51-addition program, with all vectors scaled
by two to represent half-target candidates as integers. File hashes are pinned
in `manifest.json`.

## Precisely what is optimal

For the fixed scaled rank-23 decomposition in `333.json`, the smallest sum of the
three separate factor-SLP addition/subtraction counts over Q is **51 = 12 + 12 + 27**, even allowing arbitrary
independent invertible 9-dimensional input and output basis changes. Copies, sign
changes and fan-out are free. Nonunit scalar operations are not permitted inside
the kernel. Basis-conversion costs are excluded from the optimized quantity.

The supplied program attains this bound and has 23 separate boundary additions.
Its source is `experiments/arxiv_note_20260911/anc/333.json`; its provenance records
the underlying Perminov decomposition. U and V are 23-by-9, W is 9-by-23, and all
matrix input/output entries use row-major layout.

The three-SLP convention computes U(A), V(B), and W(p) as separate linear maps
and sums their gate counts. Circuits that mix the two input families or mix input
signals with product signals across these interfaces are outside the proof.

This is **not** an optimality statement for all 3x3 matrix-multiplication schemes,
all rank-23 decompositions, or every rescaling of this decomposition. Free nonunit
rescaling of individual rank terms, with compensating changes in other factors,
is outside the class. It is also not a claim of historical novelty.

## Why the finite search is complete

Each of U, V and W^T has 20 distinct nonzero target vectors up to sign, spanning
dimension 9. A circuit with 9 input roots and 11 addition/subtraction gates can
provide at most 20 distinct signed signals. Consequently, an 11-gate circuit would
have to use 9 targets as its roots and produce a new target at every gate. The
verifier tests all C(20,9) = 167,960 root sets for each factor, repeatedly applying
every exact relation T_k = +/-T_i +/-T_j. No root set generates every target.
Thus U and V need at least 12 additions, matching the supplied circuits.

For W^T, suppose there were a 12-gate circuit. Its 9 roots and 12 gates provide at
most 21 distinct signed signals, so there is at most one additional non-target vector H up to sign.
A circuit with no such H has already been excluded. If H is computed, its inputs
are targets, so H is a signed target-pair sum or difference (including a doubled
target). If H is a root, it must be used in a gate that produces a target: that
gate is +/-H +/-T, or +/-H +/-H. Hence H is a signed target-pair sum/difference,
or one half of a target. Zero, duplicate and unused signals cannot improve this
count and may be removed. These cases generate exactly 358 distinct candidates.

For each candidate, the verifier checks every possible root set: either 9 targets,
or H together with 8 targets. It even includes dependent sets, so it tests a
superset of legal bases. Every exact target/helper production is closed repeatedly.
None reaches all 20 targets: at most 19 are reached. The enumeration covers
358 * (C(20,9) + C(20,8)) = 105,226,940 root-set cases. Equal target-only closures
are merged without losing information, leaving 4,918,562 distinct closure tests.
Therefore W^T needs at least 13 additions.

Finally, all 23 product inputs to W are used and W has output rank 9. Transposition
turns an a-addition decoder into an (a-23+9)-addition transposed program. This is
also obtained by counting edges in the pruned binary circuit and reversing them.
Thus W needs at least 13+23-9 = 27 additions. An invertible output basis change
becomes an input basis change after transposition and preserves these interface
conditions. Summing the three independent lower bounds gives 12+12+27 = 51,
exactly the count already achieved by the supplied kernel.

This is a reproducible finite computational proof for a specified circuit class;
its conclusion does not rest on an optimization timeout or an unverified solver
claim. The included independent C++ result and the Python verifier agree.
