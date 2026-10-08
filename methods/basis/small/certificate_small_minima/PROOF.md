# Exact kernel minima for two specified decompositions

The bundled rank-15 2×3×3 scheme has minimum kernel cost **38 additions**;
the bundled rank-20 2×3×4 scheme has minimum kernel cost **48 additions**.
The minima allow arbitrary invertible rational changes of coordinates on each
input/output entry space. They fix the decomposition and its term scalings.
Gates are binary addition/subtraction (including doubling); signs and copies
are free. Nonunit scalar multiplication/division is not a primitive kernel
gate. Basis-conversion costs are excluded. These are not universal bounds for
matrix multiplication of these dimensions.

## Upper bounds

`verify_upper.py` checks all tensor coefficients of the two ordinary-coordinate
decompositions, invertibility of the conversion matrices, the three exact
factorizations, and every assignment of the alternative-basis kernel circuits.
Their forward input / input / decoder costs are respectively 9/11/18 and
12/12/24. The source JSON files are copied byte-for-byte from retained research
witnesses; SHA256 identities are printed by the verifier. Some explicit sign
nodes are treated as free, as required by the stated arithmetic model.

## Trivial parts of the lower bound

If a forward map requires q distinct nonzero forms up to sign on a
d-dimensional input space, at least q-d gates are necessary in any input
basis: at most d of those forms can already be inputs. This argument uses
signed forms, not projective directions; the target scalings are fixed.

| Scheme | U: q,d | V: q,d | W transpose: q,d |
|---|---|---|---|
| 233 | 15,6 | 15,9 | 15,6 |
| 234 | 18,6 | 20,12 | 20,8 |

Thus the U and W-transpose lower bounds are 9/9 and 12/12. Linear-circuit
transposition gives a decoder offset rank minus output dimension: 9 for 233,
12 for 234. It remains to prove V≥11 and V≥12, respectively.

## Formal relation obstruction

Attach a separate formal symbol over F2 to every physical rational wire.
This is bookkeeping, not reduction of the matrix-multiplication tensor mod2.
A gate H=X±Y supplies the formal relation e_H+e_X+e_Y. A doubling supplies
e_H. The actual gate relations are independent because every gate has a new
output. Consequently a d-input circuit has formal quotient dimension d.

For a proposed set of targets and helpers, allow *every* signed gate relation
among those forms, even mutually incompatible or cyclic ones. If R is this
relation matrix and R_H its projection onto helper coordinates, the dimension
of the target image in the formal quotient is

    q + rank_F2(R_H) - rank_F2(R).

Any value greater than d excludes a circuit, whatever its input basis.
Passing this test alone does not prove existence of an acyclic circuit.

## Why the helper search is finite and complete

Ten gates for the 233 V map allow at most 9+10−15=4 helper forms; eleven gates
for 234 V allow at most 12+11−20=3. The helpers may have arbitrary rational
coordinates. Their denominators are not bounded as a search assumption.

Actual signed gate equations form a basis of the physical rational relation
space. Since the targets span the whole input space, projection of that
relation space onto the h helper coefficients is surjective. Choose h gate
equations whose helper coefficient rows are independent. They give AH=R with
A invertible. Up to signs and helper labels, each row of A is one of

    e_i; 2e_i; e_i±e_j; 2e_i±e_j; e_i±e_j±e_k.

The corresponding right sides are respectively a target sum/difference, one
target, one target, zero, and zero. Repeated target operands are allowed.
There are finitely many A and right-side choices, and H=A^(-1)R enumerates
every possible helper set. Details of the completeness argument and valid
symmetries are in `HELPER_RANK_REVIEW.md`.

For three helpers there are 28 row types, 154 nonsingular orbits, of which
124 permit nonzero right sides. Four diagonal orbits are covered by all
triples from the anchor set {±T_i±T_j, ±T_i/2}; 120 other orbits are enumerated
directly. For four helpers there are 60 row types and 1,911 active orbits;
five diagonal cases use the anchor set and 1,906 are enumerated directly.
All-zero right sides imply zero helpers and may be discarded.

The four-helper replay also removes provable duplicate assignments: independent
blocks of A^(-1) permit independent sign choices, and equal isolated one-helper
blocks permit helper permutations. An exhaustive positive-control problem
confirmed the same 18,822 canonical passing sets before/after this reduction.

Every smaller-helper circuit can be padded with fresh target-sum gates after
the outputs. There are 207 available nontarget signed pair forms for 233 and
376 for 234, so there are enough distinct choices. Thus exclusion at h=4 or
h=3 also excludes every smaller helper count.

All enumerated helper sets fail the necessary target-quotient test. Therefore
V≥11 for 233 and V≥12 for 234. Combining the bounds gives

    233: 9 + 11 + (9+9) = 38;
    234: 12 + 12 + (12+12) = 48.

The bundled circuits attain both values.

## Independent checks and limits

Separate implementations regenerated all helper-pattern orbits, compared
specialized relation generation against generic all-wire relation generation,
and replayed the complete three-helper enumerations for both targets. The
four-helper search had independent exact rational sampled relation checks,
full pattern coverage checks, the exhaustive positive control above, and a
separate end-to-end reconstruction/replay in this bundle. This is a
computer-assisted proof with a human-readable completeness argument, not a
Lean formalization. External mathematical review remains appropriate before
publication. The more permissive projective/countable-scalar 51 theorem in
the sibling bundle is a different theorem with different scope.

## Calibration: the selected224 decomposition

The retained224 witness has21 kernel additions (3/6/12) and5 conversion
additions. For its U,V,W-transpose maps, the projective target counts are
7,14,14 in dimensions4,8,8. Thus any input bases need at least3,6,6
new directions; transposition adds14−8=6 decoder gates. The bound is
3+6+12=21, attained by the existing witness. `verify_224.py` reproduces
this argument, and `verify_upper.py` also checks the source tensor and bases.
This simpler bound survives arbitrary term gauges and free scalar weights.
It is a fixed-decomposition result and an audit of an existing count, not a
new21-operation construction or a universal rank14 lower bound.

## A different234 decomposition:46 is attained and optimal

`scheme234_46.json` is based on Perminov's cr58_cn82 rank20 decomposition,
not the earlier48-optimal source. Its U has16 distinct signed targets in
dimension6, so the lower bound is10. W-transpose still has20 targets in
dimension8, giving12 plus12 for transposition. The same complete
three-helper procedure rules out11 for V: all16,519,420 right-side
assignments fail, with minimum target-quotient dimension13>12. Hence its
kernel minimum is10+12+24=46, attained by the bundled circuit.

Reproduce just this additional lower-bound case using:

```sh
python3 verify_lower.py --case 234_46
```

The fixed-scale, signed-addition scope is unchanged. This new kernel has
explicit conversion circuits in its source JSON; it does not automatically
improve the best standard-coordinate one-level multiplication.
