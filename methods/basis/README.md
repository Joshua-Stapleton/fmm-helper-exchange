# Exact basis search, coordinated transformations and lower bounds

This directory records useful positive and negative research outcomes, with the model limits needed to interpret them. A kernel count excludes basis conversions. None of these fixed-source or finite-family proofs establishes the global addition minimum for matrix multiplication.

## Main reusable ideas

1. **Target-root enumeration.** With d input roots and g binary gates, there are at most d+g distinct signed signals. If the targets nearly fill that budget, there can be only a few non-target helpers. Classify those helpers using their first necessary relations to targets, then close every exact production from every possible target-root subset. Including dependent root sets is a safe relaxation for exclusion.
2. **Complete helper patterns.** For several extra helpers, enumerate finite coefficient-pattern classes modulo sign/permutation symmetry, invert their nonsingular relation matrices exactly, and check the resulting target/helper closure. This covers arbitrary rational helper vectors within the proved budget; it is not a bounded-coefficient guess.
3. **Joint root/helper exchange.** Change the input roots and the reusable internal expressions together. Pull donor forms back into common coordinates, canonicalize signs, retain every exact binary production, and search linked helper replacements by closure. A pool exclusion is local to that pool and exchange size.
4. **Coordinated decomposition changes.** The Segre GL₂ × GL₂ move changes four linked terms while preserving the tensor. Proving a minimum across a specified family is stronger than optimizing bases of only one decomposition, but still much narrower than a universal theorem.

## Reproduce

Run from the repository root. Python 3.9+ is required (Python 3.10+ is a safe choice); native exhaustive searches require a C++17 compiler called `c++`. No network, paid service, optimizer or third-party Python package is needed.

| Package | Result and scope | Command |
|---|---|---|
| [Fixed rank-23 source](fixed_scheme_optimal51/README.md) | Exact minimum 51 for the stated fixed-scaled decomposition and separate factor-SLP model | `python3 -I -B methods/basis/fixed_scheme_optimal51/verify.py` |
| [Coordinated 784-member grid](segre_grid_floor51/README.md) | Minimum 51 on exactly the listed rational P,Q grid: 27 members have lower bound 51; 757 at least 52 | `python3 -B methods/basis/segre_grid_floor51/verify.py` |
| [4×4 strict witness](certificate_4x4_169_43/README.md) | 169 kernel additions; boundary 39 additions/subtractions + 4 halvings; rank 48 | `python3 -I -B methods/basis/certificate_4x4_169_43/verify.py` |
| [4×4 helper/root neighborhoods](exchanges/README.md) | Complete specified finite exchange neighborhoods; no improvement found | `python3 -B methods/basis/exchanges/replay.py --case all` |
| [Canonical orbit](canonical_orbit/README.md) | At most10 canonicals per factor throughout the stated de Groote orbit; historical c32 alternative-basis witness | `python3 -B methods/basis/canonical_orbit/orbit_bound.py` |
| [Smaller schemes](small/README.md) | Exact 233/323 constructions, canonical boundary 10, and earlier fixed-source 224/234 minima | See per-package commands |

The grid's full verifier rebuilds the native one-helper engine and checks 3,013,370,360 covered root/helper cases using 284,851,988 distinct closure tests. `--fast` checks data only and is explicitly not a full lower-bound verification. The original intermediate floating-point input screen was replaced with exact fractions; the distributed signatures and complete replays agree.

Standalone ZIPs are provided for the fixed51, grid51, 169/43 and small-scheme certificate directories. Source is also browsable outside the ZIPs. Existing decomposition provenance and Perminov licensing are retained. These methods combine established ideas with the particular search engineering and certified constraints recorded here; no general SLP-optimality or literature-priority claim is made.
