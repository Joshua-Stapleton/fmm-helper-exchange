# Supplied fixed-map certificates, 8 October 2026

These standalone certificates preserve the exact signed linear maps from
Perminov's public FMM collection. They use binary additions/subtractions and
copies, with no basis changes, extra negations or nonunit scalar operations.

| Map | Certified additions | Certificate |
|---|---:|---|
| 3x4x7 V | 78 | [Program and verifier](347_V78/README.md) |
| 5x5x8 V | 161 | [Program and verifier](558_V161/README.md) |
| 7x8x8 V | 401 | [Program and verifier](788_V401/README.md) |

From the repository root:

```sh
python3 -I -B certificates/fmm_maps_20261008/347_V78/verify.py
python3 -I -B certificates/fmm_maps_20261008/558_V161/verify.py
python3 -I -B certificates/fmm_maps_20261008/788_V401/verify.py
```

Only Python's standard library is required. Each leaf certificate includes
the public source match, file hashes, literal program, signed candidate and
independent coefficient/operation replay. These are individual V-factor
upper bounds, not complete multiplication costs or proofs of optimality.

The [9 October follow-up](../fmm_maps_20261009/README.md) includes nine maps,
the complete 3x6x8 triple, reproducible donor pools and new reconstruction
witnesses. The [experiment report](../../docs/experiments-20261009.md) records
the later bounded searches that retained the 161 and 401 certificates.
