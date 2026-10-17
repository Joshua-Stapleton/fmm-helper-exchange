# Starting circuits, exchange radius and exact replacement filtering

A second 17 October pass improved four original signed V maps by one addition
each. All final circuits use literal additions/subtractions with fixed original
inputs and output signs. No basis conversion, product-sign change or rank
reduction is involved.

| Map | Previous certificate | New certificate | Source of new result |
|---|---:|---:|---|
| 5x7x7 V | 204 | **203** | Other starts in the same pool; also longer old-bank search |
| 4x4x16 V | 220 | **219** | Other starts in the same pool |
| 5x5x12 V | 230 | **229** | New native completions added to the pool |
| 6x7x8 V | 280 | **279** | Longer search of the old bank alone |

The complete schemes now use **694, 633, 721, 952** additions respectively, with
the same 176, 192, 220, 239 products. All twelve factor maps and all 328,457
coefficients of the four multiplication tensors were independently checked.
These are improvements to the supplied certificates, not global record claims.

## Starting from more than the shortest donor

The previous pool builder merged forms from every donor, but chose just one
initial helper set: the donor with the fewest live operations before sign
canonicalization. Ties follow input order. The search discards that donor's
specific chains and reconnects its forms through the shared pool. Two donors
with identical helper-form sets are therefore the same search start.

We froze six pools and compared one best start with two eight-start portfolios:
the best plus the next seven by normalized cost, and the best plus seven chosen
for new helper-form coverage with a cost penalty. Every portfolio retained the
global incumbent. Each policy received six nominal search seconds per seed,
two seeds per case, split equally among its starts. Candidate embedding,
deduplication and selection took 6.064 seconds across all six cases. The 36
policy runs comprised 204 native search calls and took 225.90 seconds overall,
including 216 nominal search seconds. Actual startup and validation costs are
recorded separately.

The single best start improved none of the six incumbents. Cost-ordered and
diverse portfolios both reached 219 on 4x4x16 in both seeds; the diverse portfolio
also reached 203 on 5x7x7 in one seed. Successful starts included 221 instead of
220, and 205 instead of 204. These improvements use only forms and exact
productions already present in the same frozen pools.

This is an operational policy comparison, not proof that diversity alone caused
the gain: a larger starting circuit also gives this plateau engine a higher
initial size ceiling. A separate bounded-uphill control allowed the best start
to retain states one or two helpers above its current best. Sixteen six-second
trials on four cases produced no count improvement. Multi-starting helped in
this small trial; trying every increasingly expensive donor is not established
as a generally better allocation. Some historical donors are much larger, so
both tested portfolios were capped at eight distinct helper sets.

## Two removals versus three

Three different controls should not be confused:

* The original exchange engine disables up to three existing helper forms and
  introduces fewer replacement forms. Descendants remain eligible and can be
  rebuilt using other exact productions. Dead work is pruned at the end.
* The later plateau engine inserts one through six reachable forms and then
  greedily attempts individual deletions. Its six is an insertion parameter,
  not a limit of three deleted helpers.
* Perminov's native restart omits optional wanted-vector hints. A retained hint
  need not survive and an omitted form can be recreated. This is not the same
  neighborhood as explicit pool deletion.

All twelve two-removal calls on six current pools completely exhausted their
single/pair exchange neighborhoods without improving counts 77, 110, 155, 204, 230,
280. Triple enumeration did not finish within five seconds and also found no
gain. This supports a cheap pair scan first, followed by more selective or
bounded triple work when it stalls; it does not prove pairs are sufficient.

Two historical controls give a rigorous finite-neighborhood counterexample.
For the same saved U160 and W-transpose 156 anchors, every single/pair exchange
fails (231 and 171 pairs respectively), but checked three-removal exchanges
give 158 and 155. The positive witnesses and complete restricted negative scans
are supplied together. This is a separation between two fixed-pool exchange
neighborhoods, not a global SLP lower bound or a new count discovery.

## Safe filtering of the final replacement

When only one insertion remains, reverse-trace unfinished outputs through all
currently allowed, unready forms. Stop at ready forms or disallowed forms.
The disallowed boundary contains every viable single insertion that could
complete an output: any successful newly enabled dependency path must enter
the allowed graph through such a boundary node. Candidates outside it can
therefore be skipped without removing a successful last-insertion completion.
Cycles are handled with a visited set. The first of two jointly useful
insertions must remain unfiltered; the test suite includes a counterexample.

In six matched five-second pilots, the filtered search started 3.17–10.06 times
as many triples. A started triple may be partial at timeout; these are small
traversal-throughput measurements, not full-layer completion times or a
universal speedup claim. In a blind historical ten-second control, filtered
search recovered the known W-transpose 156-to-155 witness in 8.180 seconds;
the original search with the same seed missed it within ten seconds. No
current addition bound improved from this radius-only subexperiment.

Four safety tests pass, including an independent Python/native comparison on
200 randomized cyclic graphs and 2,000 one-insertion states. A separate
standard-library verifier replays all 77 exported ordered maps exactly.

## Native omission-size control and new donors

Five frozen best V circuits were tested with exact omission sizes two and
three, uniform sizes one through three, and uniform sizes one through eight.
Two seeds received six seconds each per case and arm, at one worker per call.
All 40 calls and 2,357 completed circuits replayed exactly;2,522 draws were
attempted. None directly improved 155, 220, 204, 230, 280. Exact size two produced
716 completions versus 523 for size three under equal budgets. The size-three
exports contained more forms absent from the incumbent in every case, but
that alone does not establish better addition counts or novelty to the old pool.

In separate fifteen-second old-bank/new-bank pool comparisons, the new donors
enabled 229 for 5x5x12 while the matched old bank stayed 230. Its witness uses two
helper forms absent from the old pool. One occurs only in the selected
one-through-eight donor export; the other occurs in several omission arms.
This is evidence for retaining some broader sampled diversity, not proof that
size three or size eight is necessary. Old-bank controls independently reached
203 on 5x7x7 and 279 on 6x7x8, so those gains must not be credited to the new donors.
The ten postprocessing calls took 161.60 seconds, including 150 nominal search
seconds plus pool preparation and validation.

## Certificates and code

[Download the four-scheme certificate ZIP](../downloads/fmm_pool_multistart_certificates_20261017.zip).
Extract it and run `python3 -I -B verify_all.py`. Python's standard library is
sufficient. It checks final and previous text/physical-JSON programs, matrices,
pool provenance, full tensors and file hashes.

SHA256: `c577fc10d90e843d1073c64cf999ed1d5ea0a89a99505ac4e199a1df06a8d576`.

[Portable policy and filtering study](../methods/linear/reconstruction/pool_policy_study/README.md)
includes frozen inputs, original and filtered native search, start selection,
bounded-uphill controls, native-size tests, exact witnesses, observed timings
and negative results. Search stopping is wall-clock dependent; arithmetic and
certificate replay are deterministic.
