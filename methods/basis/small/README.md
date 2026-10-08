# Small-scheme exact constructions and helper-budget proofs

These are selected **fixed scaled decompositions**, not universal minima for their matrix dimensions. Independent rational input/output bases and free signs/copies are permitted in the lower-bound models; nonunit term gauges and arbitrary nonunit scalar gates are excluded unless the individual proof explicitly states otherwise. Boundary costs are separate.

| Directory | Verified result |
|---|---|
| `certificate_233_36` | Rank-15 kernel 36 = 9+9+18, plus boundary 10; exact fixed-source kernel minimum. |
| `certificate_323_33` | Cyclic counterpart: rank-15 kernel 33 = 9+9+15, plus boundary 10. |
| `certificate_canonical_boundary_10` | Separate fully canonical staged boundary minimum 10 = 2+6+2 for that 233 source (rotates to 323). Not a fused ordinary-circuit lower bound. |
| `certificate_small_minima` | Earlier selected 224/rank14, 233/rank15, 234/rank20 sources have minima 21,38,48; a different 234 source has minimum46. The newer 233 source above improves38 to36. |

Within each directory, run `python3 -B verify.py` when present. The 233 package also has `python3 -B verify_lower.py`. For the older collection run `verify_upper.py`, `verify_224.py`, and `verify_lower.py`. The latter lower-bound replay takes several minutes and rebuilds its native engines. Python standard library and C++17 are sufficient. All generated `replay/` and `lower_replay/` files are disposable and excluded from publication.

The helper-budget classification is explained in each `PROOF.md`: root/gate counting reduces the arbitrary-rational search to finitely many relation patterns; exact linear algebra generates helper candidates; exhaustive target closure excludes the smaller gate budget. The supplied programs include positive controls and independent implementations where available. No result follows merely from a solver timeout.

The JSONs retain underlying source provenance. Perminov's upstream license is included. Read each README before comparing counts: for example the 46-addition 234 kernel needs 12 boundary additions, so its one-level isolated cost is58.
