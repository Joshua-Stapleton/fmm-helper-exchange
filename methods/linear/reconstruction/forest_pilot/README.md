# Charged output-forest experiment and frozen search witnesses

These are numeric, reproducible search artifacts for one rank-176 5x7x7 scheme. All circuits retain the original input coordinates and ordered outputs. The complete standard-basis certificate has **180 + 205 + 316 = 701 additions**, with 176 products; see [the complete certificate](../../../../certificates/scheme_5x7x7_176/README.md). This directory supplies search evidence, rather than another claim of global optimality or runtime superiority.

The WT witness computes the transpose of the original W linear map. WT is a circuit-transposition device, not a changed matrix basis. The complete certificate supplies the resulting original W circuit with 316 additions and checks the full multiplication tensor. This directory independently verifies that `maps/WT.sms` is exactly the transpose of `maps/W.sms`.

## Charged output forest

The method in [output_forest.py](../output_forest.py) makes a vertex for each target row up to sign and chooses signed sparse differences between nearby targets. A root edge computes a target directly. A non-root edge computes `d = y_child - sign*y_parent`, then pays a binary operation to reconstruct `y_child = sign*y_parent + d`. The score estimates residual support cost plus reconstruction, rewards repeated residuals, and varies tie-breaking noise. LEO solves the resulting residual map using the original inputs. All reconstructed outputs and latent computations are counted; signed aliases and unused gates are then removed.

For the frozen seed-8804 witness, the original V map has 49 inputs, 176 output rows, and 172 distinct rows up to sign. The selected forest needs 94 residual forms. The accounting is **80 latent additions + 147 reconstruction additions = 227**, followed by three normalization savings, giving 224. `winning_forest/` preserves the exact plan, raw solver result, latent target order, charged 227-gate circuit, normalized 224-gate circuit, and modular implementation compatibility check. The verifier reconstructs all 227 gates directly from the raw solver result and plan, independently of the search code.

Later repair produced 220 and 219-gate V donors. Combining chains and reconnecting the larger frozen pool produced the final 205-gate V witness. The general ideas of residual factorization, circuit transposition, and common-expression reuse are established techniques; this evidence concerns their selection and combination on this particular scheme.

## Frozen numeric evidence

| Directory | Donors | Forms | Initial pool count | Selected witness |
|---|---:|---:|---:|---:|
| `control_V/` | 20 | 471 | 225 | 225 |
| `V/` | 270 | 685 | 207 | 205 |
| `U/` | 25 | 313 | 194 | 180 |
| `WT/` | 25 | 320 | 187 | 175 |
| `V/ablation/` | 250 | 666 | 207 | 205, linked below |

Donor order and each signed DAG are preserved exactly. The frozen V bank contains the original 270 circuits, including 20 direct mixed-start completions; later pair-start variants were not added. `V/sources.json` aligns one source label with each donor. The ablation removes precisely those 20 direct completions and retains every other donor in its original order. [Ablation results and the 205-gate winner](intelligent/ablation/) describe the matched 80-second, seed-577002, width-10 control. Both banks reached 205, so this experiment does **not** establish that those 20 mixed starts caused the final improvement. It also does not erase possible earlier ancestry shared by retained circuits.

Donor banks and candidate files omit repeated target matrices. Each pool keeps the single target matrix required by the existing search interface. Original U, V, W, and WT maps are separately supplied in `maps/`. `SHA256SUMS.json` freezes the numeric evidence and independent verifier; the repository release manifest covers the complete distribution.

## Verify and reproduce

From the repository root, the independent check uses only Python's standard library:

```
python3 -I -B methods/linear/reconstruction/forest_pilot/verify.py
```

It checks artifact hashes, every donor, every stored pool relation, acyclic selected productions, fixed root coordinates, ordered target coefficients, the frozen ablation subset, and the complete paid output-forest reconstruction. It also invokes [the mixed-start record checker](intelligent/verify.py), covering 48 charged starts, 38 exact completions, ten recorded timeouts, three strict intermediate witnesses, and the direct-donor ablation accounting. These signed circuit checks complement the separate strict literal certificates; they do not replace checks for unary negations or nonunit scalings.

To rebuild every frozen pool, first compile the relation enumerator, then pass its path:

```
c++ -O3 -std=c++17 methods/linear/pool_relations.cpp -o /tmp/fmm-pool-relations
python3 -I -B methods/linear/reconstruction/forest_pilot/verify.py \
  --native /tmp/fmm-pool-relations
```

The recorded [native verification](verification_native.json) confirms identical inputs, forms, production lists, outputs, targets, and incumbents for all five banks. The default [verification report](verification.json) checks 590 donor entries across those banks; the 250-entry ablation is an ordered subset of the 270-entry V bank.

A new plateau search over the frozen final V pool uses:

```
python3 -B methods/linear/search.py \
  --data methods/linear/reconstruction/forest_pilot/V/pool.json \
  --out NEW_OUTPUT_DIRECTORY --engine plateau --seconds 80 --seed 577002 --width 10
```

Search is heuristic and its outcome under a wall-clock limit can vary. The stored 205-gate witness is verified independently of reproducing its discovery. To generate new forests, use the external pinned LEO repair driver with [the method's CLI](../output_forest.py); default seed 8800 and the first five trials reproduce the seed-8804 selection, while the preserved raw solver result removes dependence on a repeated solver run.

## Cross-map controls

Twenty new-forest trials per map gave best signed counts 84 for 3x4x7 V, 179 for 5x5x8 V, and 154 for 2x4x14 V, against existing certified counts 78, 161, and 133. Pooling each new forest bank with its existing best circuit and running plateau search for 30 seconds also retained 78, 161, and 133. Those searches completed rather than timing out; [standalone](cross_standalone.json) and [pooled](cross_pooled.json) summaries preserve the details. On 8x8x8 V, all twelve latent-map calls timed out after five seconds each and produced no accepted candidate. Thus the new method was useful on this uploaded scheme, but these controls do not demonstrate a general advantage across maps.
