# Exact circuit synthesis and basis transport

This packages the general circuit machinery used in the September/October searches. Binary additions, subtractions, signed copies and nonunit scalar gates must be distinguished: `Circuit.cost()` treats signs as free, whereas the strict CP exporter realizes each binary gate as `x+y`, `x-y` or `y-x`. A full multiplication certificate must still coordinate factor signs and count every interface. Generic pool synthesis requires nonzero target forms and rejects zero targets explicitly.

## Components

- `circuits.py`: exact rational and F2 coefficient replay, PLinOpt-format SLP/SMS I/O, pruning, direct circuits, linear transposition and tensor verification. The tensor convention uses W rows paired with column-major output coordinates; L/R/P SMS files in `lrp.py` use row-major output. Do not exchange W and P without that permutation.
- `cp_pool.py`: finite rational-form pool selection. Gate-choice variables and increasing depths enforce an acyclic circuit; Boolean sign choices forbid hidden unary negations in strict mode. Nonunit scale ratios are separate paid operations. Repeated-pair synthesis adds candidate forms; signs alone are canonicalized, not arbitrary magnitudes.
- `joint_basis.py`: select free basis roots and their circuit together. Computing a full-rank target set from exactly d roots forces their independence; every exported solution also undergoes exact inversion and replay. `--roots-all` broadens roots beyond target forms.
- `joint_core_boundary.py`: linked kernel and conversion DAGs, archived helper pullback, optional structural cuts and scalar candidates. Its search uses free signs and exports raw candidates; strict whole-tensor sign orientation remains necessary. `--fixed-roots` fixes both the incumbent root set and its boundary productions, so it is a fixed-boundary control, not a search over all schedules with those roots. `--legacy` may be repeated to read prior certificate folders. Each reused pool must supply its coordinate boundary explicitly.
- `transport.py`: exact helper transfer `v C_old C_new^-1`; this is a representation change, not a free physical conversion.
- `lrp.py`: exact row-major rank48 utilities. Rank and inverse entries are coerced to Fraction before division, including integer input matrices.

These combine established linear algebra, transposition and constraint-programming techniques. No globally optimal or generally superior SLP optimizer is claimed. `INFEASIBLE` applies only to the stated finite pool/model. `UNKNOWN` or timeout proves no exclusion.

## Run

Python3.10+; solver examples need `pip install ortools` (tested9.15.6755). No upstream reducer is required. From repository root:

```sh
python3 -B methods/circuits/test_methods.py
python3 -B methods/circuits/test_methods.py --solver
python3 -B methods/circuits/cp_pool.py ALT_L --cap 0 --bound 44 --seconds 10 --out results/cp
python3 -B methods/circuits/joint_basis.py ALT_L --cap 0 --bound 44 --seconds 10 --out results/joint
python3 -B methods/circuits/joint_core_boundary.py --side P --core 49 --boundary 11 --cap 0 --boundary-cap 0 --fixed-roots --seconds 10 --out results/coupled
```

For another linear map, `cp_pool.py` accepts `--source program.slp --target matrix.sms`. Output directories must be new. The default factor source is the included169/43 certificate. These short searches are examples, not guaranteed reruns of the original discovery budgets.

The controls check a known three-gate circuit, prove its two-gate finite pool infeasible, replay transposition, reject a forward dependency, test nonintegral inversion, and reconstruct a chosen rational basis exactly. Original source identifiers and portability changes are in `PROVENANCE.json`.
