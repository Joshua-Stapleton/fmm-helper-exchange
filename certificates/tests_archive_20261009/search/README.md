# Representative finite pools and witnesses

All pools use exact signed intermediate forms. `SEARCH.json` gives their frame,
source hashes and purpose. `donors.json` is compactly formatted, with redundant
per-donor target matrices removed; gate/output arrays remain unchanged.
Every donor is independently replayed against the corresponding matrix.

The 4x5x9 W, 4x6x7 W and5x6x6 W directories are causal pools for the recorded
30-second transpose-frame follow-ups. Their kernel candidates require132,120
and127 additions; the independently verified original W programs require233,
215 and227 respectively. The actual original-map certificates, not a presumed
count shift, establish these final claims.

The 8x8x8 U/V/W directories are reconstructed validation pools containing the
already verified383/375/650 original-map witnesses. They are not the first
causal discovery pools. U/V kernels are in the direct frame. The W pool is in
the transposed343-by-64 frame, with a371-gate witness; the exported original
64-by-343 W program uses650 literal additions/subtractions.

To search a supplied pool again, run from repository root with a new output
location, for example:

```sh
python3 -B methods/linear/search.py \
  --data certificates/tests_archive_20261009/search/5x6x6_W/pool.json \
  --out /tmp/fmm-Wt-search --engine plateau --seconds 30 --seed 71 --width 8
```

This optional search compiles the supplied C++ engine. Verification alone uses
only Python's standard library. A timeout or unsuccessful run gives no proof
that the current finite pool, or the unrestricted problem, is optimal.
