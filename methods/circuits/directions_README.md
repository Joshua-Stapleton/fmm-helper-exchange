# Projective-direction floors for a fixed linear map

[`direction_floor.py`](direction_floor.py) computes elementary addition lower bounds for a specified rational matrix. The model counts binary linear gates and allows scalar copies for free. Input and output coordinates stay fixed. A lower bound in this permissive model also applies to ordinary signed addition/subtraction circuits for the same matrix.

These bounds concern one linear phase. They do not establish optimality over all matrix multiplication schemes, ranks or changes of basis, and they are not derived by restricting the search to a finite pool.

## Direct target count

Two nonzero coefficient vectors have the same projective direction if one is a nonzero rational scalar multiple of the other. The analyzer divides each vector by its first nonzero coefficient to compare directions exactly. Zero vectors are ignored. Vectors supported on one coordinate are input directions and are available through free scalar copies.

Let d(A) be the number of distinct noncoordinate projective directions among the rows of A. Each of these target directions must first occur at a binary gate. Scalar copies preserve direction, and one gate produces at most one new direction. Therefore every binary linear circuit for A uses at least d(A) gates.

## Transposed target count

For an m-by-n matrix with no zero rows or columns, suppose a circuit has s binary gates. Absorb scalar copies into edge labels and prune unused gates. Its n inputs and s gate outputs give n+s wires. Its gates have 2s operand edges, and the requested outputs contribute m output uses.

Reverse the circuit. Inject one new independent input for each original output use. At each original wire, accumulate its outgoing contributions before propagating the result to its parents. If that wire has k contributions, at most k-1 binary accumulations are needed. Every original wire is used after pruning; the absence of zero columns ensures that all n original inputs remain used. Summing gives at most

```
(2s + m) - (n + s) = s + m - n
```

binary gates for the transposed map. Cancellations can only reduce this cost. Since the transposed map needs at least d(A^T) gates, the original circuit satisfies

```
s >= d(A^T) + n - m.
```

The analyzer returns the maximum of the direct count, the applicable transposed count and zero. It conservatively disables the transposed bound if a zero row or column is present; it continues to report the direct bound.

This uses the classical transposition principle. A linear straight-line program formulation appears in Proposition 1 of Bostan, Lecerf and Schost, [*Tellegen's Principle into Practice* (ISSAC 2003)](https://specfun.inria.fr/bostan/publications/BoLeSc03.pdf). The wire/edge argument above makes the addition-only accounting explicit with scalar copies free. The principle itself is not a new contribution here.

## Sharp examples

The supplied rank-45 2x4x7 scheme gives two matching fixed-map bounds over Q:

| Map | Shape: outputs by inputs | Direct noncoordinate directions | Transposed noncoordinate directions | Sharp bound | Attaining program |
|---|---:|---:|---:|---:|---:|
| U | 45 by 8 | 35 | 8 | 35 | 35 additions/subtractions |
| W | 14 by 45 | 14 | 36 | 36 + 45 - 14 = 67 | 67 additions/subtractions |

The [U35 proof bundle](../../certificates/tests_archive_20261009/proofs/2x4x7_U35/PROOF.md) and [W67 proof bundle](../../certificates/tests_archive_20261009/proofs/2x4x7_W67/PROOF.md) include the exact matrices, explicit direction lists, strict attaining programs and independent verifiers. Thus these two phases are optimal for their fixed matrices even with scalar copies allowed for free. This does not imply that the entire multiplication scheme is globally optimal. Characteristic-two optimality is not claimed.

## Run the analyzer

Python's standard library is sufficient. From the repository root:

```sh
python3 -I -B methods/circuits/direction_floor.py \
  certificates/tests_archive_20261009/maps --out /tmp/fmm-direction-floors.json
python3 -I -B methods/circuits/direction_floor.py \
  certificates/tests_archive_20261009/proofs/2x4x7_W67/W.sms \
  --explicit-classes --out /tmp/fmm-W67-directions.json
```

Inputs can be individual SMS files or directories containing SMS files. Outputs record the source byte hash, model, dimensions, row and transposed direction counts, applicability checks and resulting floor. `--explicit-classes` additionally exports the normalized rational vectors.

The analyzer does not search for a circuit and does not certify an upper bound. Matching a floor to a verified program is a separate step. The standalone proof verifiers supply that step for U35 and W67.
