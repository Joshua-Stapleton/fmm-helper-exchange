# Saved exact donor-pool searches

The three directories contain complete portable donor circuits, their finite
pools and saved search records. Donor counts are entries, not claims of globally
unique algorithms. Matrix coordinates and signs are fixed throughout.

| Example | Donor entries | Search seed | Width | Budget | Certified count |
|---|---:|---:|---:|---:|---:|
| 2414_V133 | 50 | 53 | 8 | 45 s | 133 |
| 388_V173 | 60 | 53 | 8 | 45 s | 173 |
| 368_V158 | 84 | 107 | 6 | 60 s | 158 |

Run from the repository root, substituting the desired example directory:

```sh
python3 -I -B make_pool.py \
  certificates/fmm_maps_20261009/search/2414_V133/donors.json \
  /tmp/fmm-rebuilt-pool.json
python3 -B methods/linear/search.py \
  --data certificates/fmm_maps_20261009/search/2414_V133/pool.json \
  --out /tmp/fmm-pooled-search --engine plateau --seconds 45 --seed 53 --width 8
```

The 388_V173 example uses the same search arguments. For 368_V158, use
`--seconds 60 --seed 107 --width 6`. Pool assembly and arithmetic replay use
Python's standard library; search additionally compiles the supplied C++ engine.
The frozen pools are supplied so reproductions do not depend on JSON formatting
or candidate-generation timings. A rebuilt pool can have a different file hash
while representing the same mathematical objects.

First improvements in the saved traces appeared after about 2.54 seconds for
2414_V133, 0.252 seconds for 388_V173 and 11.48 seconds for 368_V158 after pool
assembly. Timing depends on hardware and load; a wall-clock budget does not
promise the same number of search steps or discovery time. All claimed programs
are independently verified by `../verify.py` regardless of search outcomes.
