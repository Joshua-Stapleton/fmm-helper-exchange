# Pool search certificates, 17 October 2026

These are exact improvements for four supplied matrix multiplication schemes in their original coordinates and with their original signs.

| Scheme | Products | U additions | V additions | W additions | Total additions | Previous total |
|---|---:|---:|---:|---:|---:|---:|
| 5x7x7 | 176 | 177 | 203 | 314 | 694 | 695 |
| 4x4x16 | 192 | 75 | 219 | 339 | 633 | 634 |
| 5x5x12 | 220 | 105 | 229 | 387 | 721 | 722 |
| 6x7x8 | 239 | 219 | 279 | 454 | 952 | 953 |

Including the products, these totals are 870, 825, 941 and 1191 scalar operations respectively. The multiplication ranks and matrices are unchanged. There is no basis change, uncounted negation, nonunit scaling or conversion. A and B use row-major storage; C uses column-major storage, which is only an ordering convention.

## Verify

Extract the ZIP, enter its directory, and run:

```sh
python3 -I -B verify_all.py
```

Only Python's standard library is needed. The verifier checks every file against MANIFEST.json, replays all twelve final and all twelve previous literal programs with exact rational coefficients, independently replays their physical JSON programs with exact integer coefficients, and verifies all four complete bilinear tensors. Every JSON gate is an ordinary addition/subtraction; output aliases are positive and every gate is used. The JSON files were encoded from the literal programs so their operation conventions agree. Both representations are then evaluated independently against the original SMS matrices.

## What changed

Only the V programs changed: 5x7x7 V fell from 204 to 203, 4x4x16 V from 220 to 219, 5x5x12 V from 230 to 229, and 6x7x8 V from 280 to 279. The other eight programs are unchanged from the preceding published certificates.

The 203 and 219 reductions came from restarting the existing plateau search from other complete solutions in the same frozen pool. No new donor vectors were generated for these two wins. Successful starting circuits cost 205 for 5x7x7 V and 221 for 4x4x16 V, so starting only from the cheapest circuit can miss useful search paths in these bounded experiments. The exact start rows and pool bytes are included under search/.

The 229 reduction followed new native completions from the omission-size experiment and pooled search. Its matched prior-bank-only control stayed at 230. The final witness uses two helper vectors absent from the prior pool. One occurs in the selected k2, k3 and uniform1to8 donor banks; the other occurs only in the selected uniform1to8 bank. This does not establish a particular advantage of removing three helpers.

The 279 reduction came from an extra 15-second search over prior donors and the previous incumbent alone; it is not attributed to newly generated native donors. The expanded new-donor pool also reached 279.

Each successful multi-start portfolio comprised eight 0.75-second native search calls, six nominal search seconds in total. The separate native-donor pooling follow-up used 15-second plateau budgets per control or expanded arm. These exclude separately recorded preparation and donor-generation time. Timing depends on the machine and scheduling; no general search-speed claim is made. The certificates do not depend on rerunning a time-limited search. All discovery searches used signed wires; final orientation fixed every original input and output sign without extra gates.

The original schemes, donor circuits and restart methods build on Andrey Perminov's FastMatrixMultiplication and linear-expressions-optimization repositories, alongside the methods and provenance in the preceding public release. These certificates concern named supplied maps; they do not assert global optimality, practical matrix multiplication speedup, or a lower multiplication exponent.
