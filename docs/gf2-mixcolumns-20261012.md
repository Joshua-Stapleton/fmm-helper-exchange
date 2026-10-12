# Exact XOR synthesis for AES MixColumns

12 October 2026. A transfer experiment from fixed arithmetic-circuit search to
binary linear circuits. **No smaller circuit was found.**

The [NIST catalogue](https://csrc.nist.gov/Projects/circuit-complexity/list-of-circuits)
requests forward MixColumns circuits using at most 86 gates, or at most 93 with
depth three. This study uses pure two-input XOR, free copies and unrestricted
fanout. It does not attempt general Boolean synthesis or technology mapping.

Three original pinned NIST sources independently replay as 88 XORs/depth5,
90/depth4 and 97/depth3. All 32 input basis images agree exactly with the
[FIPS197](https://doi.org/10.6028/NIST.FIPS.197-upd1) byte-field specification.
Gate counts, dependency depths and the standard example column are checked
independently. XOR identities are used throughout; integer-addition circuits
are not reinterpreted as binary circuits.

| Selection problem | Solver seconds | Verified witness | Scope |
|---|---:|---|---|
| 217-form pool, any depth | 60.059 | 88 / depth5 | FEASIBLE; no improvement |
| Same pool, depth<=3 | 2.601 | 97 / depth3 | Solver-reported optimum only within the pool |
| Output-support extension, 1,649 forms | 180.024 | 97 / depth3 | Restricted inventory; FEASIBLE |
| Complete normalized depth-three model | 180.038 | 97 / depth3 | FEASIBLE; target93 unresolved |

## Structural search rather than random helper sampling

In a two-input XOR circuit, a depth-two form depends on at most four inputs.
MixColumns outputs have support five or seven, so every output needs depth
three. A used nonoutput gate can therefore have depth at most two. Duplicate
forms can be merged using a producer of minimum depth; pairs can be computed
directly from their inputs. The remaining helpers are triples and quads.

Enumerating every output split includes cancellation of one bit outside a
weight-five output's support. The resulting model has 8,457 forms and 30,307
productions. A separately implemented enumeration of all 41,448 masks of
weights one through four checks its split generator. The
[full normalization argument](../methods/linear/gf2_mixcolumns_study/complete_depth3/README.md)
is derived and unmechanized; it is not a research-priority claim or a checked
UNSAT certificate. This structural model is the useful artifact, rather than
a new gate-count result.

The complete search's saved bound is 63 total gates, far below the 97-gate
incumbent. Default replay checks witnesses and inventories, not solver
infeasibility/optimality reasoning. No timeout proves that 93 is impossible.

## Reproduce

From the repository root, with standard-library Python3.10+:

```sh
python3 -I -B methods/linear/gf2_mixcolumns_study/verify_all.py
```

This checks export hashes, original source hashes, all witnesses, regenerated
catalogues, exhaustive output splits and seven negative semantic controls.
It leaves the supplied dataset unchanged. All upper-bound replay is included
in the repository's default release checks.

[The method README](../methods/linear/gf2_mixcolumns_study/README.md) gives
optional OR-Tools reruns in fresh output directories. Four large solver-model
text files are omitted with original hashes and regeneration commands
preserved. Source attribution is retained.

[Download the standalone study](../downloads/gf2_mixcolumns_study_20261012.zip),
extract it, and run `python3 -I -B verify_all.py` from its folder.
The result establishes no runtime, energy, silicon-area or full-AES advantage.
