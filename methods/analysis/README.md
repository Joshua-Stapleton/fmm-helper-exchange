# Recursion counts and rational roundoff envelopes

`count_portfolio.py` counts three specified tensor-axis schedules with all conversions and classical cutoffs. `count_winograd.py` independently executes the ordinary Strassen-Winograd rule and its bordered81×81 example with scalar counters. Their comparison demonstrates why a kernel improvement need not improve the best complete algorithm at a small dimension. Neither script searches all algorithms or measures time.

`roundoff_audit.py` propagates first-order local rounding symbols through the complete one-level4×4 computation, allowing exact downstream cancellation before taking absolute bounds. `allorders_roundoff.py` additionally propagates previously accumulated error and bilinear cross terms. The latter gives an all-orders rational envelope, not merely the first-order coefficient. The default is the included169/43 certificate, including every boundary.

Assumptions: exact inputs of magnitude at most one, a relative-error model per rounded operation, no overflow/underflow, and exact signs/power-of-two scaling. These are upper envelopes, not measured error or a stability comparison over all inputs. The included all-orders169/43 bound at binary32 is approximately2508.504474u. Classical multiplication was more accurate in the historical sample trials; no speed claim follows.

```sh
python3 -B methods/analysis/count_portfolio.py
python3 -B methods/analysis/count_winograd.py
python3 -B methods/analysis/roundoff_audit.py
python3 -B methods/analysis/allorders_roundoff.py
```

All four use the Python standard library for these paths. `Circuit.float_eval` is an optional NumPy helper. Results print to standard output. Original script hashes and changes are in PROVENANCE.json. First-order and all-orders theory are standard; this is their explicit application to these literal circuits with conversion costs included.

`support_distance.py` gives a cheap necessary lower bound on the number of elementary column shears, allowing arbitrary interleaved signed row/column permutations. Each shear changes one support-size histogram entry, at L1 cost at most two. It is not a lower bound for arbitrary basis conversions. Run without arguments for exact controls, or pass a JSON containing matrices A and B.
