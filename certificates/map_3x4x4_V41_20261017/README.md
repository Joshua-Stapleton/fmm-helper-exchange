# A 41-addition program for the supplied 3x4x4 V map

Run `python3 -I -B verify.py`. Python's standard library suffices.

The verifier checks all 608 entries of the original ordered 38-by-16 integer
matrix against both the literal program and its JSON circuit. There are exactly
41 binary additions/subtractions, no unary negations, no nonunit scalar
operations, and no unused assignments. Input and output signs are fixed.

The source SMS comment reports 43 additions; the original 43-gate program was
not supplied or independently replayed. The 41-gate program was found directly
by Andrey Perminov's unchanged LEO solver, using the `new-improvements` API
pinned at commit `7c8b59864e000bdc880938428d8a1991ec1f0bea`. Our adapter and
independent verification are credited separately. Donor pooling matched 41
but did not improve it in the bounded tests.

Only this V factor was supplied. This package makes no complete multiplication
tensor, new rank, global addition record or unrestricted optimality claim.

[Study and replacement counterexample](../../docs/344-and-exchange-20261017.md).
