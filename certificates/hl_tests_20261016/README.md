# Exact certificates for Perminov hl_tests (16 October 2026)

Run `python3 -I -B verify_all.py` in this directory. Only the Python standard library is required. The verifier checks the manifest, original source-chain expansion, all 57 returned literal and signed circuits, addition counts and all 19 complete multiplication tensors. A PASS is an exact upper-bound certificate, not a minimality proof.

`counts.csv` lists U,V,W counts. `claims.json` retains original source annotations, current counts, previous verified or original-source comparisons, and per-phase elapsed times. `provenance/` records each selected witness, reused earlier witness if any, donor/pool statistics and timing stages. Time is this campaign's observed elapsed time on a shared host; historical time to a reused witness is not included. Initial environment installation, adapter rebuilding and discarded startup attempts are excluded. Independent verification and packaging time are recorded separately, not attributed to discovery.

The maps use ordinary integer coordinates. Inputs A,B are row-major and output C is column-major; that ordering is not a basis change. Every addition/subtraction in the displayed literal programs is charged. There are no unpaid unary negations, nonunit scalar operations or unused intermediate assignments. Transpose searches, where used, return and verify the original W map.

Source schemes are from Andrey Perminov's FastMatrixMultiplication repository at commit `6c75fd36564b177165d6968efd4c9e6199266191`. Upstream attribution and rights are retained. The counts do not establish new multiplication ranks, global records, practical speed or numerical stability.

## Repeat the bounded campaign

Use `archive_batch.py` and `archive_wt_extra.py` from `fmm-helper-exchange/methods/linear/reconstruction/`, together with the documented compiled upstream reduce CLI, repair adapter, pool backend and weighted pool adapter. Set RECON, LEO, REPAIR, POOL, WEIGHTED and PYTHON to their local locations; PYTHON must have OR-Tools. Run the following from this certificate directory. The three manifests retain exact original group order, original filenames, source hashes, source chains and only the prior candidates actually supplied at the start. They do not initialize with newly found final circuits.

```sh
"$PYTHON" -B "$RECON/archive_batch.py" --inputs . --manifest manifest_group_a.json --out rerun_group_a --leo-cli "$LEO" --repair-binary "$REPAIR" --pool-binary "$POOL" --weighted-binary "$WEIGHTED" --runtime-python "$PYTHON" --method-seconds 4 --call-timeout 1 --attempts 12 --search-seconds 8 --orientation-seconds 5 --strict-candidates 6 --seed 46160000
"$PYTHON" -B "$RECON/archive_batch.py" --inputs . --manifest manifest_group_b.json --out rerun_group_b --leo-cli "$LEO" --repair-binary "$REPAIR" --pool-binary "$POOL" --weighted-binary "$WEIGHTED" --runtime-python "$PYTHON" --method-seconds 4 --call-timeout 1 --attempts 12 --search-seconds 8 --orientation-seconds 5 --strict-candidates 6 --seed 47160000
"$PYTHON" -B "$RECON/archive_batch.py" --inputs . --manifest manifest_group_c.json --out rerun_group_c --leo-cli "$LEO" --repair-binary "$REPAIR" --pool-binary "$POOL" --weighted-binary "$WEIGHTED" --runtime-python "$PYTHON" --method-seconds 4 --call-timeout 1 --attempts 12 --search-seconds 8 --orientation-seconds 5 --strict-candidates 6 --seed 48160000
```

For each W row, run `archive_wt_extra.py` with `--source rerun_group_GROUP/PRIMARY_RERUN_DIRECTORY --out rerun_group_GROUP/PRIMARY_RERUN_DIRECTORY/adjoint_extra --pool-binary "$POOL" --runtime-python "$PYTHON" --seconds 8 --orientation-seconds 5 --seed CAMPAIGN_W_ADJOINT_SEED`; the directory and seed are explicit fields in that row's manifest. Primary seed = group base + 1000 * zero-based manifest index. Adjoint seeds are group A: base + 1000 * primary index + 900; group B: base + 50000 + 1000 * primary index; group C: base + 500 + 1000 * zero-based W index.

`campaign_protocol.json` records all fixed method knobs: one solver thread, retention0.5/0.9 from the same incumbent and seed, scored cuts, residual forests, two weighted draws, and paid donor-pool reconnection. Three campaign workers ran concurrently; each processed one map at a time. The group-C adjoint pass ran after its primary pass; A/B ran it immediately after each W. Fixed seeds and limits repeat the procedure, but wall-time stopping and host contention can produce different heuristic search results. The supplied exact witnesses verify deterministically.

## Fixed output signs

A circuit that treats wire signs as free can have fewer gates than its implementation with the exact supplied output signs. Only strict literal-program counts are reported in `counts.csv` and `claims.json`. `best_unoriented_signed_additions` in a phase's provenance is a separate search diagnostic.

Where a sign orientation alone cannot implement every output, paid output-sign correction is recorded explicitly. Its additional subtraction gates are included in the final count. An intentional zero wire or two wires representing opposite forms can be needed by this implementation. The certificate verifier replays those raw gates; it does not projectively normalize the final circuit. The signed base candidate is included in `provenance/sign_recovery/` so its count and exact map can be checked separately from the charged fixed-sign result.

The per-phase `paid_sign_recovery` metadata and affected campaign-manifest rows retain the correction method, seed/limits and reproduction command when applicable. Correction time is shown separately and added to the map's current-campaign total unless it was already included in the primary summary.

The reported net sign overhead includes output corrections, internal corrections and shared-zero construction, accounting for any gate elisions or pruning. Output-correction count alone can be smaller than total overhead. The portable correction script is included; OR-Tools is required only to repeat its bounded orientation. From the bundle root:

```sh
"$PYTHON" harness/paid_sign_repair.py --candidate provenance/sign_recovery/7x7x8_U_base.json --matrix 7x7x8/U.sms --out rerun_paid_signs_7x7x8_U --seconds 5.0 --seed 46198000
"$PYTHON" harness/paid_sign_repair.py --candidate provenance/sign_recovery/7x7x8_V_base.json --matrix 7x7x8/V.sms --out rerun_paid_signs_7x7x8_V --seconds 5.0 --seed 46199000
```

## Separate tensor-preserving product-sign variant

`joint_product_signs_7x7x8/` contains a separate1179-addition variant using the existing public joint orientation method. Its273/334/572 phase counts preserve the ordinary-coordinate multiplication tensor by compensating product signs across U,V,W. Individual original maps change, so this result does not replace the fixed-map1200 row. The standalone verifier checks both scopes separately. The supplement includes its three original signed input candidates and a portable reproduction wrapper.
