# Exact fixed V-map certificate: 78 additions/subtractions

`V.slp` computes the bundled 64-by-28 matrix with its original input
coordinates and signed outputs, using 78 binary additions/subtractions,
zero standalone negations and zero nonunit scalar multiplications. There is
no basis change. This factor matches [Perminov's public FMM collection](https://github.com/dronperminov/FastMatrixMultiplication/blob/6c75fd36564b177165d6968efd4c9e6199266191/schemes/results/addition_reduced_ZT/3x4x7_m64_cr249_cn446_ZT_reduced.json);
expanding that published factor program requires 82 additions/subtractions.
The public source hash and coefficient match are recorded in `PROVENANCE.json`.

From the repository root, run:

```sh
python3 -I -B certificates/fmm_maps_20261008/347_V78/verify.py
```

Alternatively, enter an extracted standalone certificate directory and run
`python3 -I -B verify.py`. Python's standard library is sufficient. The
independent verifier checks payload hashes, every matrix coefficient and all
literal operation counts, including signs and unused assignments.

`signed_candidate.json` preserves the circuit before fixed-sign orientation.
Optional orientation replay requires OR-Tools:

```sh
python3 orient_fixed.py signed_candidate.json V.sms regenerated.slp
python3 verify_literal.py V.sms regenerated.slp
```

This is a feasible bound for this fixed linear map, not a global optimality
claim. It certifies the V factor only, not a complete multiplication cost.
Arithmetic counts do not establish a practical runtime improvement.
