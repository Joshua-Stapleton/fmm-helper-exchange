# Repeated bit-axis factors in fixed linear maps

This module extracts an exact structural reduction from the supplied rank-343
8x8x8 scheme. It keeps every original coefficient and variable coordinate.
Input bit pairs provide an index bijection, not a change of basis.

For each factor map, every coefficient row splits across three four-coordinate
bit axes. The outer axes each contain seven forms, but the middle axis contains
14 forms for U/V and 13 for W-transpose. **These matrices are not one fixed
S7 tensor-cubed.** The code checks this actual factorization against all 21,952
coefficients of each supplied map, preserving source output order and signs.

After the first outer axis, each of its seven groups requires the same
49-by-16 local coefficient map G. Compute the outer map on sixteen slices
(80 additions), then replay G separately in seven groups. The saved local
programs cost 51,49,48 signed gates, giving exact lifts 437,423,416 for U,V,WT:

`lift cost =80+7*(local cost)`.

The subsequent global form pool reconnects expressions across those groups.
The frozen final programs use **U383, V375 and direct W650**, hence 1408
additions/subtractions with 343 products for the original scheme. WT371 is a
signed transpose-kernel count; direct W650 has its own strict literal certificate.
Signed search/lift counts assume free wire signs. The final literal programs
separately establish their fixed-sign ordinary add/sub counts.

## Verify without any compiler or solver

Python 3.10+, standard library only, from the repository root:

```sh
python3 -I -B methods/linear/tensor_factors/verify.py
```

It re-derives the index bijection, row/sign alignment and repeated local maps
from the original SMS files; replays all three local kernels; constructs and
checks the charged lifts; and independently replays the final literal programs
against the original fixed matrices. Each map checks 21,952 coefficients. The
separate archive certificate verifies the full multiplication tensor.

## Re-derive and lift the saved local programs

```sh
python3 -I -B methods/linear/tensor_factors/tensor_factors.py \
  --matrix methods/linear/tensor_factors/fixtures/source_u.sms \
  --local-program methods/linear/tensor_factors/fixtures/local_u.json \
  --out /tmp/fmm-8-u-lift
python3 -I -B methods/linear/tensor_factors/tensor_factors.py \
  --matrix methods/linear/tensor_factors/fixtures/source_v.sms \
  --local-program methods/linear/tensor_factors/fixtures/local_v.json \
  --out /tmp/fmm-8-v-lift
python3 -I -B methods/linear/tensor_factors/tensor_factors.py \
  --matrix methods/linear/tensor_factors/fixtures/source_w.sms --transpose \
  --local-program methods/linear/tensor_factors/fixtures/local_wt.json \
  --out /tmp/fmm-8-w-lift
```

Each output directory must be new. The W command operates on the linear-map
transpose and reverse-accumulates its program back to the original decoder;
it verifies the original W coefficient matrix on export. This is not an external
basis conversion. `factorization.json` records the input index bijection,
axis forms, original output indices and signs. `local_map.json` records G and
every original output's local-row index. `donors.json` can feed the existing
exact pool builder and search engines.

## Build further local donors, then pool the lifted circuits

The same local G must be used; substituting another 4x4 multiplication scheme
does not reproduce these coefficient matrices. The portable reconstruction
adapter can optimize the saved local programs against their fixed targets:

```sh
git clone https://github.com/dronperminov/linear-expressions-optimization /tmp/leo
git -C /tmp/leo checkout 2abd2fd8f15dc1c97dd24777515324f865e77504
python3 -I -B methods/linear/reconstruction/reconstruct.py \
  --leo /tmp/leo --candidate methods/linear/tensor_factors/fixtures/local_u.json \
  --out /tmp/fmm-local-u-donors --retention .9 --seconds 20 --attempts 40
python3 -I -B methods/linear/tensor_factors/tensor_factors.py \
  --matrix methods/linear/tensor_factors/fixtures/source_u.sms \
  --local-program methods/linear/tensor_factors/fixtures/local_u.json \
  --out /tmp/fmm-new-u-lift
python3 -I -B methods/linear/fast_pool.py /tmp/fmm-new-u-lift/donors.json \
  /tmp/fmm-u-pool.json
python3 -B methods/linear/search.py --data /tmp/fmm-u-pool.json \
  --out /tmp/fmm-u-search --seconds 30 --seed 20261009 --width 8
```

If reconstruction emits a new `best_candidate.json`, replace the saved local
fixture path with that program. Otherwise keep the fixture or use an exactly
checked donor from its `donors.json`. Combine several lifted and
ordinary donor circuits with identical ordered outputs before pooling. One
lift alone need not reproduce the larger frozen pool or its final count.

Library functions `factor_bits`, `conditional_map`, `lift` and `transpose`
can be called with other power-of-two square coordinate grids. They reject
rows that fail the exact bit-axis product test or outer groups that do not
share an identical local map. This adapter currently requires ternary targets.
It does not search for arbitrary basis changes.

## Provenance and limits

The coefficient matrices are Perminov's public
`8x8x8_m343_cr1661_fv1015_cn4434_ZT_reduced` scheme, pinned at
FastMatrixMultiplication commit 6c75fd36564b177165d6968efd4c9e6199266191.
The local kernels combine upstream LEO donors with exact form pooling. Generic
factorization, tensor composition, vector covering and local search are
established methods; no broad novelty or superiority theorem is claimed.

The original experimental controllers overwrote some shared auxiliary files.
The published final validation instead uses frozen directories reconstructed
from surviving exact donors, **including already verified best witnesses as
incumbents**. Fresh searches record matching pool hashes. Those artifacts
validate the counts; they are not a causal replay of the first discovery.
Old mixed auxiliary pools are excluded. Fixture hashes and sources are listed
in `PROVENANCE.json` and `fixtures/SHA256.json`.

The results preserve the rank and basis of this particular decomposition.
They do not establish a global 8x8 record, a lower exponent, global SLP optimality
or measured matrix-multiplication speed. The local coordinate-enriched finite
pool exclusions in the research log apply only to their supplied dictionaries.
