# Selective partial reconstruction and exact donor pooling

The public upstream library is unchanged at commit
`2abd2fd8f15dc1c97dd24777515324f865e77504` on `solution_optimization`.
It supports restarting from a partial straight-line program. Its ordinary
restart independently retains each gate with probability one half,
conditional on retaining its parents. A gate with a distinct noninput
ancestral set of size a therefore survives with probability 2^-a.

The selective variant chooses one to three gates sharing parents or nearby
dependencies, removes them and their descendants, and keeps every unaffected
gate. The resulting partial SLP is compacted and passed to the unchanged
`VectorCoveringSolver::solve(partial, 1.0)`. This can discover exact
intermediate forms outside the original finite pool. Independently replayed
repairs can then enlarge a pool whose alternative dependencies are searched
globally.

The experimental ranking favors removed-gate count minus lost distinct
output-form count. Each lost nontrivial output form needs a replacement gate
if the retained circuit remains fixed. This difference is an optimistic repair
margin, not a predicted completed cost. Cuts are capped at twelve removed
gates. Candidate groups use up to eight nearby gates.

## Concrete witness

For the 3x6x8 V map, selecting original wires 51 and 117 invalidated nine
gates, including five output forms. Retaining 150 gates and rebuilding eight
produced a 158-gate circuit. Four repaired intermediate forms were absent
from the incumbent. The winning repair took 0.183 seconds, after 52.256
seconds in the ranked search, with seed 4064, savings 0 and support slack 4.
All 5,424 coefficients were checked exactly, including the fixed signs,
with no separate negations, scalars or dead assignments.

The control shuffled the same 743 eligible groups. It also found 158,
after 3.645 seconds; see `comparison.json`. Both policies used structured
dependency groups. This single control supports reconstruction as a useful
hybrid but provides no evidence that the ranking is better than random order.
Wall-clock timings depend on hardware, system load and timeout decisions.

## Replay the exact prepared input

Run from the repository root with a separately obtained upstream checkout
at the stated commit:

```sh
python3 -I -B methods/linear/reconstruction/reconstruct.py \
  --leo /tmp/leo \
  --prepared certificates/fmm_maps_20261009/method/cut_064.txt \
  --out /tmp/fmm-158-replay --seed 4064 --savings 0 --slack 4 --timeout 30
```

The portable module compiles its adapter against that external checkout,
leaving upstream unchanged. The expected raw solution is
`cut_064.raw.json`, SHA-256
`445ab21008379dc4b877b8cd07136b5bb729477fc438d129981fa9cd9ad0a507`.
The archive includes the original winning driver source as a provenance
snapshot. `winning_cut.json` preserves the seed and original source hashes;
the historical Python instrumentation is not required for replay.

For arithmetic verification alone, run `python3 -I -B verify.py` from the
certificate directory. No compiler, upstream checkout or third-party Python
package is required. Every repair must pass exact coefficient replay before
pool admission. A complete multiplication claim also requires a U/V/W tensor
check with the correct W orientation.
