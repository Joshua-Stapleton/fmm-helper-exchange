# Random initialization from pooled computation chains

The adapter samples intermediate forms from several complete donor SLPs and
imports their required ancestor computations into one acyclic partial SLP.
Already computed forms are reused up to sign only; scalar magnitudes remain
distinct. Importing parents before children and keeping the first producer
prevents cycles between alternative donor identities. The completion solver
receives the original inputs, not the sampled helpers as free new roots.

This uses Andrey Perminov's external LEO partial-solution interface at commit
`2abd2fd8f15dc1c97dd24777515324f865e77504`. His ordinary rounds retain part of
one selected solution. Here the initialization can mix chains from several
solutions before completion. LEO can then invent forms outside the donor bank.
The current adapter requires donors for the same ordered signed linear map.

Sampling is randomized but biased toward used endpoints with low marginal
ancestor cost. It first reserves room for contributions from the requested
sources, then fills the remaining gate budget. Completion uses retention one:
the deliberate partial start is not independently thinned again. The final
count includes every seed computation that remains live after pruning.
Completed programs can subsequently be pooled and globally reconnected using
the existing exchange/rebuild tools; this pilot measures completion alone.

## Functional example

Two five-addition donors compute `a+b+c+d` and `a+b-c-d`. One makes `a+b`
useful, the other makes `c+d` useful. A mixed two-gate start allows completion
as `t=a+b; u=c+d; y1=t+u; y2=t-u`, four total additions. The two seed gates
are charged. This illustrates sound accounting, not an advantage over every
single-donor completion or a new matrix-multiplication result.

## Small controlled pilot

The real target is the supplied 45-by-28 2x4x7 V linear map. Its existing
strict certificate already attains 67 additions. The bank has 43 entries and
42 distinct normalized donor DAGs. Each arm uses seeds 4500 through 4529,
20 initial gates, retention one, savings .01 and slack 4. Both arms finish
all 30 attempts with a two-second per-call timeout and a 25-second total cap.
Compilation is reused and excluded; the two arms run concurrently with one
solver thread each.

| Initialization | Best strict additions | Median signed gates | Elapsed seconds | Mean initially covered target forms |
|---|---:|---:|---:|---:|
| One source per start | 67 | 68 | 9.917 | 15.533 |
| Three contributing sources per start | 67 | 67 | 10.678 | 15.433 |

All 60 completions have exact coefficient replay. Both saved best programs
have independent fixed-sign literal verification: 67 binary additions,
zero unary negations, nonunit scalars or dead gates. There is **no new real
map bound**. Coverage is close on average but not matched per trial, and one
small benchmark is insufficient to establish superiority or a speedup.
The next fair comparison should stratify by both initial gate cost and target
coverage, include empty starts, and vary the scorer and bank diversity.

## Reproduce and verify

From the repository root, standard library only for saved witness checks:

```sh
python3 -I -B methods/linear/reconstruction/test_pool_starts.py
python3 -I -B methods/linear/reconstruction/pooled_start_pilot/verify.py
```

The pilot directory includes the numeric source bank, toy bank, all completed
donors, partial starts, records and strict best programs. Repeated source
`target_matrix` fields were removed only to reduce duplication; gate arrays,
outputs, ordering and names were preserved. Run new searches with the pinned
external LEO checkout as explained in the reconstruction README:

```sh
python3 -I -B methods/linear/reconstruction/pool_starts.py \
  --leo /tmp/leo \
  --donors methods/linear/reconstruction/pooled_start_pilot/source_donors.json \
  --out /tmp/fmm-pooled-starts --sources 3 --gates 20 \
  --attempts 30 --seconds 25 --timeout 2 --seed 4500
```

Use `--sources 1` and a separate output directory for the control. New
search runs need C++17; `--binary` reuses the existing repair adapter. Timings
and budget-truncated trajectories depend on the machine and concurrent load.
Generic signed output counts still require strict orientation before claims
that exclude separately charged negations. The saved bests supply that check.

[Visual chain-merging sketch](pooled-starts.html).
