# Exact transformation search primitives

These portable, standard-library implementations separate **candidate generation**
from **circuit certification**. They are extractions of the September–October
research methods; `PROVENANCE.json` pins original implementations. They combine
established exact linear algebra and finite searches, with no general novelty or
optimal-SLP claim.

Run the independent controls from this directory:

```sh
python3 -B test_transforms.py
python3 -B ternary_shears.py
```

The controls exhaust all 2,048 identity-plus-at-most-three-edit 4×4 matrices,
compare the tiny determinants to rational Gaussian elimination, replay every
unimodular inverse circuit, test both shear orders, compare matching DP with an
independent brute-force enumeration, and check all 64 tensor coefficients after
each elementary isotropy on a classical 2×2 example.

## Implementations

* `sparse_identity.py`: generate `B = I + E` with at most three distinct signed
  off-diagonal entries. The determinant lemma reduces the invertibility screen
  to at most a 3×3 determinant. `counts` gives exact determinant-class counts;
  `inverse_circuit` constructs a signed-addition inverse for acyclic supports.
  The returned circuit uses one gate per edit and is **not necessarily optimal**.
  `preserves_singletons` implements the exact protected-row restriction for
  this particular diagonal-one family.
* `ternary_shears.py`: bitset admissibility and exact nonzero deltas for a
  single signed shear; one-to-four-donor common-destination updates; exact
  inverse/history composition. A joint ternary endpoint can be useful even
  when neither specified sequential ordering has ternary intermediate states.
  The bitset primitive was already described by
  [Perminov, §3.5.2](https://arxiv.org/html/2511.20317v1).
* `transforms.py`: test both orders of two specified shears, canonicalize column
  signs and permutations, replay symmetry maps, and apply paired matrix-index
  shears that preserve the **ordinary** multiplication tensor. The last uses
  U/V row-major and W flattened in trace orientation (k×n).
* `matching.py`: choose exactly k disjoint coordinate pairs and optimize signs
  and directions using a subset dynamic program. Since disjoint edges have
  additive nonzero savings, the returned matching is globally sparsest in that
  finite family. The ternary mode also requires every unchanged column to be
  ternary, so it can screen/repair a nonternary starting factor. Its complexity
  is exponential in coordinate dimension; 16-coordinate factors were the
  intended research use. **Sparsity optimality is not SLP optimality.**
* `symmetry.py`: match exact Gram invariants, solve column signs, and finally
  verify every coefficient of a signed row/column equivalence. Such an
  equivalence transports a circuit from one input factor to another. UNKNOWN
  means no witness before the time limit, not non-equivalence. A Gram mismatch
  is a necessary-condition failure only for this signed-permutation action.

Independent entry-coordinate changes need explicit boundary circuits. Paired
matrix-index isotropies preserve ordinary multiplication and need no omitted
external conversions. Signed-column canonicalization and circuit transport use
free signs/copies as a search convention; a final strict algorithm still needs
joint sign orientation and literal operation counting. Never identify different
coefficient magnitudes or discard a conversion because the transformed kernel
is cheaper.

For the complete 9×9 three-edit determinant census, build and run the independent
integer elimination checker (C++17):

```sh
c++ -O3 -std=c++17 enumeration_audit.cpp -o enumeration_audit
./enumeration_audit 9 9
```

This enumerates 487,488 candidates, including singular matrices. It is a
determinant census, not a count of new tensor algorithms or optimized circuits.
