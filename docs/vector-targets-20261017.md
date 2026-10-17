# Retained helper vectors, followed by pooled reconstruction

This pass improved seven of ten tested linear maps, saving sixteen additions
across six existing schemes. Six improvements used donors from Perminov's new
restart mode; one came from the historical donor pool alone.
Every final certificate preserves the original ordered map and its signs,
uses ordinary bases, and charges every binary addition or subtraction.
All six complete multiplication tensors were independently checked.

| Matrix | Previously verified | New certificate |
|---|---:|---:|
| 3x6x8 V | 158 | **155** |
| 4x4x16 V | 222 | **220** |
| 4x4x16 W | 343 | **339** |
| 5x5x12 V | 232 | **230** |
| 5x7x7 V | 205 | **204** |
| 6x7x8 V | 281 | **280** |
| 4x4x14 W | 297 | **294** |

The 4x4x16 W improvement came from searching the frozen historical donor pool
alone. It is not attributed to the new vector initializations. Its search was
performed on W-transpose at 211 additions; the returned W circuit costs 339.
Likewise, 4x4x14 W-transpose costs 181 and its returned W costs 294.

| Scheme | U + V + W | Total additions | Products |
|---|---|---:|---:|
| 3x6x8 | 56 + 155 + 200 | 411, previously 414 | 113 |
| 4x4x16 | 75 + 220 + 339 | 634, previously 640 | 192 |
| 5x5x12 | 105 + 230 + 387 | 722, previously 724 | 220 |
| 5x7x7 | 177 + 204 + 314 | 695, previously 696 | 176 |
| 6x7x8 | 219 + 280 + 454 | 953, previously 954 | 239 |
| 4x4x14 | 137 + 187 + 294 | 618, previously 621 | 169 |

These improve our checked-in certificates for the supplied exact schemes.
They are not claims of global optimality, lower rank, a lower exponent, or
measured implementation speed.

## What changed

The upstream idea is to omit 1–8 eligible helper vectors from a complete
circuit, then use the survivors as optional hints for vector-cover synthesis.
Keeping a vector does not freeze its chain of sums. The solver can construct
it differently, recreate an omitted vector, or leave a surviving hint unused.
Every sum it actually uses must still be paid.

We used the unmodified LEO API at
[`7c8b598`](https://github.com/dronperminov/linear-expressions-optimization/tree/7c8b59864e000bdc880938428d8a1991ec1f0bea),
then fed completed exact circuits into the existing finite-pool reconstruction
method in this repository. Retained circuits need not be individually best:
a more expensive solution can supply one useful expression for a cheaper
combined circuit. Final sign orientation fixes all original inputs and outputs.

For 3x6x8 V, native vector restarts first gave 157. The pool built from twenty
historical donors and thirty-two selected new circuits then gave 155. That
witness contains seven helper forms absent from the entire historical bank.
Covering these particular forms requires seven different new donor circuits,
including donors costing 159 and 160. Seven binary constructions in the final
witness appear in none of the fifty-two supplied circuits. This is evidence
of combination and reconnection; the donor-cover calculation is not an SLP
lower bound. Its exact integer replay is included in the method verifier.

## Controlled comparison and costs

Ten frozen incumbents and 185 prior donors were verified before running.
Each initializer received two six-second native budgets per case, with one
CPU worker per invocation and at most three concurrent invocations.
Per-draw limit was 0.25 seconds, with a cap of 1,000 draws. The incumbents and
historical banks did not change during this comparison.

| Initializer | Completed / attempted draws | Cases improved directly /10 |
|---|---:|---:|
| Executable helper prefix | 352 /742 | 0 |
| Random retained vectors | 2306 /2381 | 6 |
| 50/50 mix | 785 /1049 | 4 |
| Guided omission | 2756 /2819 | 1 |
| Random omission, matched sizes | 2395 /2451 | 3 |

All 8,594 completed native circuits passed exact replay. The 100 invocations
took 246.47 seconds wall time; summed native process time was 608.63 seconds.
Guided schedule preparation adds 12.99 seconds, and frozen-bank preparation
took 7.47 seconds. Historical search costs are not included in those warm-start
timings. Unresolved returns combine timeout, pruning and no-candidate states;
they are not infeasibility results.

Postprocessing compared a frozen-bank baseline, each bank augmented by one
initializer's donors, and their union. Separate arms used five-second pool
searches; the union used eight seconds and is reported separately. Seventy
jobs took 143.75 seconds wall time with no exact replay failures. For the 155
witness, pool preparation took 0.249 seconds and search 5.008 seconds, finding
155 at 3.285 seconds into search. These exclude generating the new donors:
the corresponding native arm used 12.137 seconds across its two seeds, plus
validation. They are not end-to-end discovery times from scratch.

The first guided score required all surviving hints in its scoring surrogate.
A revised score required only original outputs and allowed helper recreation.
In a separate two-case, two-seed test, it did not beat random omissions:
random reached 157 twice on 3x6x8 while both guided variants stayed 158;
all three stayed 222 on 4x4x16. Final revised scoring took 1.012 and 0.942 seconds.
Earlier costly attempts took 65.07 seconds in total, plus an interrupted case
whose elapsed time was not captured. Those failed exploratory costs are
preserved rather than hidden. A final adaptive experiment fed improved pooled
circuits back into native restarts on four maps, varying coefficient caps,
omission sizes and bounds; it produced no further count reduction.

## A useful pruning control

This study explicitly used `ignoreUnusedInBound=true`; the upstream CLI sets
it false. A small recorded example has output `a+b+c+d` and optional hints
`a+e`, `b+f`. Both hints can be computed and later discarded. Counting every
materialized step against a three-gate budget rejects the tested path; counting
only currently used dependencies permits a valid three-gate completion.
This illustrates a local pruning issue, not a new global addition bound.
Native forced cascades also mean a search bound is not a hard ceiling on every
returned count. Final arithmetic is checked independently of these controls.

## Verify and reproduce

Download the [standalone certificate ZIP](../downloads/fmm_vector_targets_certificates_20261017.zip),
extract it, and run `python3 -I -B verify_all.py` in the extracted directory.
Only Python's standard library is required. The bundle contains final and
previous literal programs, source matrices, eighteen final factor maps, all
six full tensors, six intermediate native witnesses and file hashes.

ZIP SHA256: `eb80815cc2504ff9d9ea18bd85420f13f2a505a313e417dbb03f6f547edfa264`.

The [portable methods](../methods/linear/reconstruction/vector_targets/README.md)
include the pinned native API adapter, frozen bank, guided selectors, matched
runner, pool postprocessing, feedback experiment, exact provenance check and
recorded negative results. Wall-time-limited search can produce different
circuits on another machine; certificate replay is deterministic.
