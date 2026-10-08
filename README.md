# Exact helper exchanges for addition circuits

Research scripts by Joshua Stapleton.

[Download the standalone bundle](downloads/fmm_helper_exchange_scripts.zip)
(115 KB; scripts, examples, and exact certificate).

This contains the C++ search that reduced the 6x6 rank-153 scheme's U circuit
from 160 to 158 signed additions and its transposed output circuit W^T from
156 to 155. With V unchanged at 157, transposing the output circuit back gives
158 + 157 + (155 + 153 - 36) = **587 additions/subtractions**.

The separately included multiplication certificate verifies the final literal
programs in ordinary coordinates: 587 additions and 153 products, without basis
conversions, unary negations or nonunit scalar operations.

## Quick start

Python 3.10+; the quick verification needs only its standard library.
Run these commands from the extracted `helper_exchange` directory:

```sh
python3 -I -B run.py --example wt --verify-only
python3 -I -B run.py --example u --verify-only
```

These replay the saved witnesses and validate every supplied production exactly;
they do not rerun the search. Expected signed counts: W^T 156 -> 155; U 160 -> 158.

To rerun the deterministic search, install a C++17 compiler accessible as `c++`
(Clang or GCC), then run:

```sh
python3 -I -B run.py --example wt --seconds 180 --out results/wt
python3 -I -B run.py --example u --seconds 300 --out results/u
```

The wrapper compiles the included engine and checks the resulting circuit using
exact integers. Each output directory must be new. The original research runs
took approximately 38 seconds for W^T and 84 seconds for U; this is hardware
dependent. A time limit is not an optimality result.

To verify the complete multiplication algorithm, extract
`certificate_666_587.zip` into a separate directory and run there:

```sh
python3 -I -B verify.py
```

It checks all 46,656 tensor coefficients and both the JSON and literal programs.
The certificate is included unchanged, with its own manifest and provenance.

## Method

1. Pool exact intermediate coefficient vectors from several valid SLPs for the
   same linear map. Identify a vector with its negative, but preserve magnitude.
2. Record exact binary productions `form[o] = sa*form[a] + sb*form[b]`, with
   `sa,sb` in {-1,+1}. Inputs and required output forms remain available to use;
   other forms are optional helpers.
3. Remove one, two or three incumbent helpers, and insert at most two pool forms.
   Starting at the inputs, repeatedly construct any allowed form whose two
   parents are ready. After inserting a helper, recompute this closure.
4. If all targets are reached, reconstruct an acyclic SLP, prune unused gates,
   and check every resulting output coefficient exactly.

This allows the dependencies between retained forms to change. The first newly
inserted helper must be constructible from the current closure; the second may
depend on the first. This avoids testing impossible insertion orders.

In the saved W^T example, removing helpers 117,173,178 and adding 396,533 saves
one addition. Helper 396 came from CSE runs costing 198/199; helper 533 came from
a distance-scorer run costing 158. Neither insertion alone repairs that exchange.
In U, removing 65,146,184 and adding 367,373 also makes a fourth old helper
unnecessary, saving two additions after pruning.

## Try other donor programs

`make_pool.py` builds a pool from a portable JSON representation of donor SLPs:

```sh
python3 -I -B make_pool.py data/toy_donors.json toy_pool.json
python3 -I -B run.py --data toy_pool.json --verify-only
python3 -I -B run.py --data toy_pool.json --seconds 10 --out results/toy
```

Input schema:

```json
{
  "inputs": 3,
  "circuits": [
    {
      "name": "example",
      "gates": [[0, 1, 1, 1], [3, 1, 2, -1]],
      "outputs": [[4, 1]]
    }
  ]
}
```

Input wires are numbered 0 through `inputs-1`; gate k creates wire `inputs+k`.
Each gate `[a,sa,b,sb]` computes `sa*wire[a] + sb*wire[b]`. An output `[v,s]`
means `s*wire[v]`. Signs must be -1 or +1, all donors must compute the same
ordered outputs exactly, and zero forms are unsupported. The example above
computes `(x0+x1)-x2`. The toy file includes multiple donors for another small map.

The builder picks the shortest live donor as incumbent, canonicalizes signs,
and enumerates pair productions. Its work grows quadratically in the number of
pooled forms, times their dimension. The supplied U/W^T pools preserve the
original research ordering; they were not regenerated with this utility.

## Files and scope

- `exchange.cpp`: unchanged successful C++ search engine.
- `run.py`: portable wrapper and exact replay, replacing repository-specific imports.
- `make_pool.py`: portable donor-to-pool builder.
- `data/u.json`, `data/wt.json`: frozen pools, target matrices, incumbents and witnesses.
- `data/toy_donors.json`: small input-format example.
- `certificate_666_587.zip`: complete ordinary-coordinate multiplication certificate.
- `PROVENANCE.json`, `SHA256SUMS`: source identifiers and package integrity hashes.

The generic search uses **free signed wires**: exported signed programs and
`additions_signed` do not promise zero separately charged negations. The full
587 certificate includes the separate joint sign handling and literal programs
that establish its strict operation count. The wrapper does not automate that
whole-tensor sign-handling step for arbitrary new matrix multiplication schemes.

This is a fixed finite-pool local search, not a proof of globally minimal SLPs,
a general novelty claim, or a measured matrix-multiplication runtime improvement.
`EXHAUSTED_3_FOR_2` concerns only this pool and exchange neighborhood.

The decomposition is Andrey Perminov's; the donor pool combines earlier reducers
with CSE and his new distance scorer. See `PROVENANCE.json` and the certificate
for pinned sources. This archive does not bundle the upstream reducer or attempt
to regenerate all 81 donor runs.
