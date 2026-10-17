# Exact arithmetic certificates, 17 October 2026

Run `python3 -I -B verify_all.py` after extraction. Python standard library only; no search solver is required.

The verifier checks every binary addition/subtraction, ordered signed coefficient map, previous schedule, SHA256 and full matrix multiplication tensor.

| Scheme | Products | U | V | W | Additions | Previous additions | Scalar operations |
|---|---:|---:|---:|---:|---:|---:|---:|
| 3x6x8 | 113 | 56 | 155 | 200 | 411 | 414 | 524 |
| 4x4x16 | 192 | 75 | 220 | 339 | 634 | 640 | 826 |
| 5x5x12 | 220 | 105 | 230 | 387 | 722 | 724 | 942 |
| 6x7x8 | 239 | 219 | 280 | 454 | 953 | 954 | 1192 |
| 4x4x14 | 169 | 137 | 187 | 294 | 618 | 621 | 787 |
| 5x7x7 | 176 | 177 | 204 | 314 | 695 | 696 | 871 |

All matrices use their original fixed signs and normal arithmetic coordinates. C is stored column-major; this is an index convention, not a basis change. Output negations and scalar multiplications are not free: the final SLPs have no unary negations, nonunit scalars or unused assigned gates.

The search may operate on W transpose; the bundled W schedules include the complete paid return and are independently checked against the original W map. Multiplication rank is unchanged.

Control attribution: the 339-addition W schedule for 4x4x16 was already found by pooling the frozen historical donor bank alone. It is not attributed to newly generated vector hints. The separate native_witnesses retain the six intermediate native improvements before pooling.

Attribution: Perminov supplied schemes and developed the LEO solver/vector-target initialization. The pinned source and numerical experiment summaries are recorded in claims.json and native_study_summary.json. Prior certificates provide the unchanged U/W schedules where applicable.

Exact circuit upper bounds for these fixed linear maps and complete tensors. No proof of optimality, global record, numerical stability or runtime speedup.
