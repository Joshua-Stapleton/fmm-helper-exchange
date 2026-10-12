# Complete depth-three XOR formulation for AES MixColumns

This separate experiment extends the earlier finite helper catalogues to a formulation intended to cover **every pure two-input XOR circuit of depth at most three** for the FIPS 197 32-bit forward MixColumns map, assuming free copies and unrestricted fanout. It does not cover AND/XNOR/NOT gates, bounded fanout, physical routing delays, arbitrary higher-depth circuits or a hardware area model.

The completeness argument below is derived for this experiment. It is not a novelty claim, a mechanized theorem or an independently certified UNSAT proof. A solver timeout proves no optimum.

## Why the normalized form is sufficient

Each gate's coefficient mask is its set of contributing primary input bits. A two-input XOR at depth `d` has mask weight at most `2^d`, even when cancellation occurs. The output masks have weight five (20 outputs) or seven (12 outputs), so every output has depth at least three. Thus no output can serve as a parent of another output in a depth-three circuit.

Remove unused gates. Merge duplicate masks using a producer of minimum depth; replace all other occurrences by free copies. Selected parents then have strictly smaller minimum depth, so merging cannot create a cycle or increase depth or gate count. A zero intermediate and a weight-one intermediate are unnecessary: zero XOR changes nothing, and weight-one masks are primary-input copies.

Every surviving nonoutput gate has depth at most two and weight at most four. A weight-two mask can be computed directly from its two primary inputs with one XOR and depth one. Replacing any deeper producer this way cannot increase gate count or depth. There are all **496** primary-input pairs.

The only normalized depth-two producers of a weight-three helper are one primary input plus the remaining pair, giving **three choices**. A weight-four helper uses two disjoint input pairs, giving **three partitions**. Triples/quads can be needed only as direct parents of outputs; an intermediate of depth two feeding another nonoutput gate would leave that gate at depth three and its output child at depth four.

## Every possible output split, including cancellation

Write an output mask as `t=a XOR b`, with parent weights at most four.

For a weight-seven output, the only possibility is disjoint weight-three and weight-four parents. Choosing the triple gives **35 splits**.

For a weight-five output, the complete cases are:

- Disjoint weights one and four: **5 splits**.
- Disjoint weights two and three: **10 splits**.
- Weights three and four sharing one cancelling bit outside the output support: choose one of **27 outside bits**, then choose the two output bits assigned to the triple in **10 ways**. This gives **270 splits**.

The last case is the important extension beyond target-support-only helpers. The two parents XOR away the outside bit. Consequently a weight-five output has **285** possible splits, and the whole map has **6,120** output choices.

`search.py` enumerates these endpoints and every normalized producer of their triples/quads, plus every input pair. It constructs **8,457 forms**: 32 inputs, 496 pairs, 3,008 triples, 4,889 quads and 32 outputs; there are **30,307** productions.

The separate `independent_split_check` enumerates all **41,448** masks of weights one through four, then checks each mask and its XOR complement against every output. Its split sets exactly match the case-based generator on all 32 outputs. This is a direct generator check; it does not certify a solver's lower-bound reasoning.

## Selection model

Each used triple/quad selects exactly one producer and activates its required pair parents. Each output selects exactly one split and activates its noninput parents. A selected pair has its unique direct-input production. The support layers strictly increase, so separate DAG/rank variables are unnecessary.

The objective is the number of auxiliary XOR gates; the 32 output XORs are mandatory. The challenge threshold of at most 93 total gates is therefore at most 61 auxiliaries. The official 97-gate/depth-three source is verified before use as a hint, giving an upper bound of 65 auxiliaries. Boolean implications are expressed as linear inequalities, with OR-Tools level-2 linearization enabled.

The bounded run uses one worker, seed 12014 and a maximum of 180 seconds. `depth3.result.json` records the status, best objective/bound and measured solver time. The original model text is omitted from this portable export; `../MODEL_OMISSIONS.json` preserves its hash, and an explicit rerun regenerates it. Any saved witness is independently replayed against all 32 FIPS basis images, with paid gates and depth recomputed; the standard example column is also checked.

## Reproduce

Catalogue/generator checks, official-hint validation and any saved-witness replay use only Python's standard library:

```sh
python3 -I -B search.py
python3 -I -B verify.py
```

Optional bounded search requires OR-Tools and a fresh output snapshot:

```sh
python3 -I -B search.py --search --seconds 180 --out /tmp/mixcolumns-complete-depth3-run
```

The source attribution, immutable NIST commit and hashes are preserved in `../provenance.json`. The original donor sources are unchanged. Standard: [FIPS 197](https://doi.org/10.6028/NIST.FIPS.197-upd1). Contribution targets: [NIST circuit catalogue](https://csrc.nist.gov/Projects/circuit-complexity/list-of-circuits). No submission or external message was sent; no paid hardware was used.

## Bounded result

The run ended after **180.038 solver seconds** with status **FEASIBLE**, retaining **65 auxiliaries plus 32 output gates: 97 XORs at depth three**. Its best reported bound was 31 auxiliaries, or 63 total gates. **No improved circuit was found; the 93-gate contribution target remains unresolved.** The solver performed 424,975 LP iterations, so level-2 linearization was exercised, but this bound is far from the incumbent and does not prove 97 optimal. No claim of a new best-known lower bound is made.

`verify.py` passes on the saved data and circuit: all helper identities/layers, all 32 exhaustive output-split sets, the official source hint, the full FIPS basis-image equality and the example column. The original seven semantic controls in `../test_probe.py` also pass.

The default command is read-only. Optional reruns require a new `--out` directory outside this study. The study is copied there first; supplied records are never overwritten.
