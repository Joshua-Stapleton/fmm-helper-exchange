# Partial-start and control evidence

The uploaded V map has 49 original inputs and 176 ordered outputs, representing 172
forms distinct up to a unit sign. Every seed here is a paid, acyclic circuit over
those same 49 inputs. Completed raw programs retain all original output signs.
This directory records a small experiment on one fixed map.

## Frozen banks and starts

- `bank20.json`: twelve shortest available forest/baseline donors plus eight
  sampled alternatives, frozen before the original comparison.
- `bank23.json`: the same bank plus later 205, 207 and 213 programs.
- `pilot2/`: matching random/gain seeds and budgets 180, 210, 130, 80, 40; three starts
  per cell.30 starts, 20 completions, ten eight-second timeouts;169.47 seconds.
  Best 213 is strictly verified in `pilot2/best.slp`.
- `pair_pilot/` and `pair_control/`: same 23-donor bank, seeds and budgets 90, 140, 180,
  three starts per cell. Both completed 9/9. Exact-pair scoring reached 217 in 24.10
  seconds; L1-only reached 211 in 34.56 seconds. The latter strict program is
  `pair_control/best.slp`. These followups did not beat 205.

Each trial contains its recorded seed, actual initial gate count, contributing
sources, consistent unique-form and ordered-row coverage, start-assembly time and
completion status. Prefix files contain the original input count and charged
gates. Raw files contain the completed LEO substitutions and original signed
expressions. Completed donor banks omit repeated target matrices; the common
original target is the [V matrix](../../../../../certificates/scheme_5x7x7_176/V.sms).

The raw counts are generic signed counts until strict orientation. Only the 213,
211 and ablation 205 literal witnesses here are explicitly certified with no
extra negations, nonunit scalars or unused assignments. The full 701-addition
scheme is certified separately.

Elapsed start-experiment times include prefix assembly, completion calls and
exact checks. They exclude bank normalization, selector precomputation and driver
build. Trials were completed sequentially with one native solver subprocess per
experiment; these are bounded run observations, not hardware-normalized timings.
Driver records specify pinned upstream LEO
`2abd2fd8f15dc1c97dd24777515324f865e77504`, retention 1, savings 0.01 and support
slack 4. L1 distance and the pair-bonus weight are heuristic choices.

## Exact replay

From the repository root, this check needs only Python's standard library and
imports no optimizer:

```
python3 -I -B methods/linear/reconstruction/forest_pilot/intelligent/verify.py
```

It checks 43 frozen-bank entries, all 48 starts and their original coordinates,
38 complete exact programs, ten recorded timeouts, the three strict literal
witnesses, and the direct-completion ablation's new-form usage. It does not
reproduce randomized timings or establish optimality.

To rerun the original comparison with the portable selector and an external
pinned driver:

```
python3 methods/linear/reconstruction/gain_starts.py \
  --donors methods/linear/reconstruction/forest_pilot/intelligent/bank20.json \
  --binary /path/to/repair --out new-pilot \
  --budgets 180,210,130,80,40 --modes random,gain \
  --sources 6 --attempts 3 --seconds 240 --timeout 8 --seed 9000
```

For the matched pair/control experiment use `bank23.json`, budgets 90, 140, 180 and
seed 19000. Use `pair_starts.py --modes pair --seconds 90` for the pair arm and
`gain_starts.py --modes gain --seconds 60` for its control. NumPy is needed for
these selectors. Existing output directories are always rejected.

## Ablation and cross controls

`ablation/` contains the exact matched search summary, removed source list,
205-addition candidate and literal witness. The frozen 270/250 donor banks and
685/666-form pools are in [V](../V) and [V/ablation](../V/ablation). Removing all 20
direct partial-start completions still reached 205 with seed 577002, width 10 and
80 seconds. The 19 forms unique to those direct completions were unused by the
full-pool 205 program. Indirect provenance was not exhaustively tracked, so this
is a direct-removal result, not an ancestry-wide attribution claim.

`cross_summary.json` records twenty forests each on 3×4×7, 5×5×8 and 2×4×14 V maps.
They reached 84, 179, 154 and did not improve records 78, 161, 133. Their subsequent
30-second pool searches are in `cross_pool_summary.json` and also retained the
previous records. `cross_888_timeouts.json` records twelve five-second failures
with no accepted candidate. `blank_start_control.json` preserves the ordinary
initial solver attempts and their bounded failures. No timeout is a proof that
an algorithm cannot be found.
