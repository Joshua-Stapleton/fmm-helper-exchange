# A sharp addition bound for one fixed W map

The included 14-by-45 matrix W is the output factor of the specified rank-45 2x4x7 multiplication scheme. Its 67-addition/subtraction program preserves all input coordinates and output signs. This result concerns this fixed linear map; it does not establish optimality over multiplication schemes, rank choices or changes of basis.

Consider the more permissive model in which scalar copies are free and each binary linear gate costs one addition. Prune unused gates from any circuit for W and absorb scalar copies into edge labels. Every one of the 45 input variables must remain used, since every column of W is nonzero.

Write s for its number of binary gates. There are 45+s wires, 2s operand edges and 14 output uses. Reverse the circuit: inject one new independent input at each original output use, and accumulate outgoing contributions at each original wire before passing the result to its parents. A wire with d contributions requires at most d-1 binary accumulations. Every original wire has at least one use after pruning. Summing gives at most

```
(2s + 14) - (45 + s) = s - 31
```

additions for the transposed map W^T. Cancellations or scalar-only aliases can reduce this count, so this is an upper bound on the cost of the transposed circuit.

The 45 target rows of W^T contain exactly 36 distinct noncoordinate projective directions over Q. They are listed explicitly in proof.json. Each such direction must first occur at a binary gate: free scalar copies preserve direction, and input wires supply only coordinate directions. One gate supplies at most one new direction. Thus every circuit for W^T requires at least 36 binary gates.

Consequently 36 <= s - 31, giving s >= 67. The included strict signed program attains 67, so the bound is sharp even when scalar copies are allowed for free. The lower bound is for the fixed map over Q; the verifier does not claim characteristic-two optimality.

Run the independent standard-library checks from this directory:

```sh
python3 -I -B verify.py
```

The verifier checks the matrix hash, all nonzero input columns, the complete list of 36 projective directions, every coefficient of the attaining program, its 67 binary operations, and absence of uncounted negations/scalar operations or unused assignments. The wire/edge argument above is the mathematical justification for the lower bound.
