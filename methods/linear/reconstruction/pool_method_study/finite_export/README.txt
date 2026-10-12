Restricted 5x5 U observed-production catalogue

287 canonical coefficient vectors, including 25 original inputs.
468 observed binary productions from 38 raw donor solutions with paid
terminal expressions explicitly expanded. All 93 ordered outputs required.

Two fresh single-worker CP-SAT calls reported INFEASIBLE at 87 gates;
88 was feasible and replayed exactly in both runs. This is evidence about
this finite catalogue, not a global lower bound for the matrix. The already
known 87 circuit uses a vector outside this catalogue. No independent
UNSAT proof checker or formal proof certificate is included.

Standard-library upper-witness verification:
python3 -I -B verify_upper.py

Optional exported-model rerun, with OR-Tools 9.15.6755:
python3 -I -B rerun_model.py --bound 87 --seconds 30
python3 -I -B rerun_model.py --bound 88 --seconds 2

UNKNOWN means the supplied time budget did not resolve the model.
The model uses unit signed wires. Strict literal orientation is separate.
