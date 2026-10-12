# What limits the frozen 5x5 U catalogue

The native bank has 38 exact complete programs and a best reported cost of 88.
Its internal substitutions supply 209 non-input helper vectors. Expanding all
native terminal expressions as paid binary gates gives a deliberately different
complete-map catalogue: 287 vectors including 25 inputs, with 468 observed
binary productions. The same vector set has 1,753 exact binary relations when
all pairs of vectors and both signs are considered.

The known 87-gate program is not inserted into either frozen catalogue. It uses
one coefficient vector missing from this set, and two productions absent from
the observed productions between already present vectors. Three of its gates
involve the missing vector as a child or operand. `inventory.json` records the
exact vectors, productions and original program gate positions.

In the observed catalogue, two fresh single-worker CP-SAT runs returned
INFEASIBLE for at most 87 gates and an exactly replayed feasible 88-gate
program. Seven small manually decidable model controls also pass. The model selects at most one
production per used non-input vector, charges every used vector once, requires
all output vectors, requires every selected production's operands, and forces
operand ranks below the child rank. It uses unit signed wires. The solver
therefore reports a minimum of 88 in this restricted observed catalogue. The
lower side relies on completed CP-SAT results; no independent UNSAT proof
checker or formal UNSAT certificate is bundled. This is not a
global minimum for the map, and the already known 87 program demonstrates why
such a claim would be false. The native prefix sampler uses an even smaller
producer catalogue, but its completion solver may invent new vectors and
productions, so this does not rule out its complete workflow finding 87.

The enriched same-vector catalogue returned UNKNOWN at 87 and a feasible 88
program. Its minimum is unresolved. Its 87 run recorded inconsistent timer
values: Python monotonic elapsed 1.90 seconds and OR-Tools wall 1073 seconds,
with a requested 20-second allowance. Preserve the solver status and do not
use this run as a timing comparison or infer infeasibility from it.

All models and result records are saved under `cp_observed` and `cp_enriched`,
with graph/model/candidate hashes and one-worker settings. Feasible candidates
were replayed using integer coefficients. Strict literal sign orientation was
not attempted here. Unary inversions are not silently counted as additions.

This gives a useful practical distinction. Sharing ancestors is already done
by Perminov's actual code. Repeating a complete walk through an unchanged
observed catalogue cannot evade its catalogue minimum. Generating new sums or
new ways to compute existing sums can expand that catalogue. The present
diagnostic identifies this distinction; it does not establish a generally
better initializer or a new unrestricted minimization algorithm.
