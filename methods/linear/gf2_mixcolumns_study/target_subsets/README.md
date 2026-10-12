# Output-support helper extension for depth-three MixColumns

This is a separate experiment; the original `../` frozen-pool study is unchanged.

The 32 FIPS 197 output forms have weights five (20 outputs) or seven (12 outputs). A two-input XOR at depth two can involve at most four input bits. Therefore every parent of a depth-three output must be a form of support at most four. The seven-bit outputs also show that depth three is the smallest possible depth in the two-input XOR basis: depth two can cover at most four inputs.

## Informed candidate generation

`extend.py` generates every weight-two, weight-three and weight-four subset of each output support. It adds all 496 pairs of primary inputs and retains every form from the three official donor circuits. It does not sample masks or read an improved oracle circuit.

This gives 1,280 distinct output-support subsets and a total of **1,649 forms**, 1,432 of them absent from the original 217-form pool. Enumerating every exact relation `c=a XOR b` among the included forms gives **83,246 constructions**.

The depth-three model retains **4,527 admissible productions**. The reductions are structural, not arbitrary score pruning:

- A weight-two helper can always be computed directly from its two free primary inputs, with one XOR and depth one. Any alternative producer is dominated for gate count and depth.
- A weight-three helper at depth two uses a primary input and a weight-two helper.
- A weight-four helper at depth two uses two weight-two helpers.
- Output parents have support at most four. Non-output forms of greater support cannot be needed as their depth-two parents.

These layers strictly increase along every dependency, so the selection model is automatically acyclic. Each selected noninput form costs one XOR, uses exactly one producer, and requires both parents. All output forms are mandatory. The official 97-gate/depth-three source circuit is an exactly verified feasible hint.

The helper inventory is restricted. In particular, arbitrary weight-three/four masks outside the included subset/observed inventory are not searched. Cancellations are permitted where the included masks allow them; this is not a claim to search every depth-three XOR circuit.

## Reproduce and inspect results

Standard-library catalogue generation, official-hint validation and any saved-witness replay:

```sh
python3 -I -B extend.py
```

Optional bounded OR-Tools solve in a fresh output snapshot:

```sh
python3 -I -B extend.py --search --seconds 180 --out /tmp/mixcolumns-target-subsets-run
```

The solve uses one worker and seed 12013. OR-Tools is optional for verification. `depth3.result.json` records the returned status, best objective and bound, measured times and exact witness replay; a timeout is not an optimality proof. The original model text is omitted here; `../MODEL_OMISSIONS.json` preserves its hash, and an explicit rerun regenerates it. Source provenance remains in `../provenance.json` at the official NIST commit `113aec82e939be46ad72522032df90cb4355f46c`.

Exact replay checks every FIPS input basis image, recomputes paid gates and dependency depth, and confirms the example column `db 13 53 45` maps to `8e 4d a1 bc`. The original seven semantic controls in `../test_probe.py` remain applicable. Every saved candidate relation and all support-layer contracts were also checked directly.

No timing/silicon improvement or global-best-known result follows from abstract XOR counts alone. No submission, external message or paid hardware was used.

## Result

The single-worker run ended after **180.024 solver seconds** with status **FEASIBLE**, retaining the verified **97-XOR, depth-three** starting circuit. Its reported lower bound was only 32, the number of required noninput output forms. **No improvement was found and the 93-gate target was not met.** This timeout establishes neither optimality of 97 in the enlarged pool nor impossibility of the target. The larger inventory makes the selection problem harder; improving solver guidance is a possible next experiment, not a result of this one.

The default command is read-only. Optional reruns require a new `--out` directory outside this study. The study is copied there first; supplied records are never overwritten.
