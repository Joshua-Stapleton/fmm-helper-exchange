# GF(2) AES MixColumns reconstruction studies

Research date: 12 October 2026. These are exact arithmetic benchmark experiments with **no improved circuit found**. They use NIST's published forward MixColumns circuits, not integer addition certificates interpreted as XORs.

## Verified inputs

The original NCFF files are pinned to [usnistgov/Circuits commit 113aec82e939be46ad72522032df90cb4355f46c](https://github.com/usnistgov/Circuits/tree/113aec82e939be46ad72522032df90cb4355f46c/data/slp/aes/aes-mixcols). SHA-256 hashes and immutable URLs are in `provenance.json`; original comments and attribution are preserved. See `SOURCE_NOTICE.md`.

Independent parsing recomputes **88 XORs/depth 5**, **90/depth 4** and **97/depth 3**. Each is exactly the 32-bit [FIPS 197](https://doi.org/10.6028/NIST.FIPS.197-upd1) forward MixColumns map. Verification constructs all 32 basis images from the byte matrix over the AES polynomial field, checks the standard example column, and treats every gate as a paid two-input GF(2) XOR.

## Three studies

| Study | Inventory | Solver outcome | Verified circuit | Solver seconds |
|---|---|---|---:|---:|
| Frozen donor pool, any depth | 217 forms; 824 enriched productions | FEASIBLE | 88 / depth 5 | 60.059 |
| Frozen donor pool, depth at most 3 | Same pool | OPTIMAL within pool | 97 / depth 3 | 2.601 |
| [Target-support extension](target_subsets/README.md) | 1,649 forms; 4,527 active productions | FEASIBLE | 97 / depth 3 | 180.024 |
| [Complete depth-three formulation](complete_depth3/README.md) | 8,457 forms; 30,307 productions | FEASIBLE | 97 / depth 3 | 180.038 |

The frozen depth-three pool has a solver-reported minimum of 97 only within its catalogue; default replay does not independently certify the solver's optimality reasoning. The enlarged target-support pool is a restricted helper inventory. The final model includes every possible depth-three output split, including cancellation of one bit outside a weight-five output. Its normalization/completeness argument assumes pure two-input XOR, free copies and unrestricted fanout; it is a derived argument, not a mechanized theorem or novelty claim. A separate exhaustive enumeration of all 41,448 masks of weights one through four checks its output-split generator.

The final search reported a lower bound of 63 total gates, far below its incumbent. This is a saved solver record, not a claimed new best-known lower bound. No timeout establishes optimality or impossibility of NIST's contribution targets of at most 86 gates, or at most 93 at depth three. [NIST catalogue and requested contributions](https://csrc.nist.gov/Projects/circuit-complexity/list-of-circuits)

## Read-only verification

From this folder, using Python 3.10 or later and no optional packages:

```sh
python3 -I -B verify_all.py
```

This regenerates the inventories in memory, checks source hashes and every exact witness, independently checks the complete output split sets, and runs seven semantic controls. It verifies upper-bound circuits; it does not certify UNSAT or solver lower bounds. The command leaves the supplied dataset unchanged.

Individual default commands are also read-only:

```sh
python3 -I -B probe.py
python3 -I -B target_subsets/extend.py
python3 -I -B complete_depth3/search.py
python3 -I -B complete_depth3/verify.py
```

## Optional reruns

OR-Tools 9.15.6755 was used for the recorded searches. No solver implementation or binary is bundled. Explicit searches require a **fresh output directory outside this study**. They first copy the complete input snapshot there, then write their models/results into that copy. Existing output directories are rejected.

```sh
python3 -I -B probe.py --search --seconds 60 --out /tmp/mixcolumns-frozen-run
python3 -I -B target_subsets/extend.py --search --seconds 180 --out /tmp/mixcolumns-subset-run
python3 -I -B complete_depth3/search.py --search --seconds 180 --out /tmp/mixcolumns-complete-run
```

Source refetch at the same immutable pin also requires a fresh snapshot:

```sh
python3 -I -B probe.py --fetch --out /tmp/mixcolumns-source-refetch
```

Four bulky model text files are omitted; `MODEL_OMISSIONS.json` retains their hashes and sizes, matching the result records. The explicit reruns regenerate them. `EXPORT_PROVENANCE.json` distinguishes original experiment-file hashes from portable adaptations. Adaptations add read-only default guards and fresh-output snapshots; algebraic generators, model definitions, seeds and solver settings are preserved.

These studies establish no hardware timing, energy or silicon improvement. A two-input XOR count is a mathematical circuit metric, not a technology-mapped area result.
