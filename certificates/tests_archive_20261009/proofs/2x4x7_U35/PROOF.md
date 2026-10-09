# A sharp addition bound for one fixed U map

The included 45-by-8 matrix U is the input factor of the specified rank-45 2x4x7 multiplication scheme. Its 35-addition/subtraction program uses the original input coordinates and output signs.

Work over Q and allow scalar copies for free. The eight input wires supply coordinate directions. Multiplication of a wire by a nonzero scalar preserves its projective direction, so only a binary linear gate can first produce a noncoordinate direction. One gate produces at most one such direction.

The target rows of U have exactly 35 distinct noncoordinate projective directions. They are explicitly listed in proof.json after dividing each row by its first nonzero coefficient. Every circuit for this fixed map must produce all 35, and therefore requires at least 35 binary gates. The included strict program uses exactly 35 additions/subtractions, so the bound is sharp even in the more permissive model with free scalar copies.

This is optimality for the specified U map over Q. It does not establish optimality over matrix multiplication schemes, changes of basis or multiplication ranks.

```sh
python3 -I -B verify.py
```

The independent verifier checks the matrix hash, the complete list of 35 directions, every coefficient of the attaining program, its 35 binary operations, and absence of extra negations/scalar operations or unused assignments.
