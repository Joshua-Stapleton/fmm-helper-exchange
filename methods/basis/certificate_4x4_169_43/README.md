# Exact rank-48 4x4 certificate: 169 core operations + 43 conversions

This alternative-basis circuit uses the same ordinary rank-48 matrix multiplication
scheme as the earlier 170/43 certificate. Both input and output interfaces are paid
for separately. There are 48 bilinear multiplications. Every explicit unary
negation and nonunit scaling is counted. All final circuits have zero unary negations.
The core is pure addition/subtraction; conversions include four explicit halvings.
All three factors retain 16 canonical coordinates. The ordinary 204 count is unchanged.
The full construction requires characteristic other than two.

The new search pulls helper forms from prior bases into a common coordinate system,
then selects the basis roots and the kernel/conversion DAGs jointly. This finite-pool
search produces upper bounds; it is not a global optimality proof.

For n=4^k under full scalar recursion and levelwise Kronecker boundaries:

    48^k + 169*(48^k-16^k)/32 + 43*k*16^(k-1).

This is an arithmetic count, not a runtime claim. A single isolated product costs
48 + 169 + 43 = 260 operations.

## Reproduce

Run `python3 -I -B verify.py` after unpacking. No dependencies are required.
The verifier checks file hashes, all 4096 tensor coefficients, all basis factorizations,
two literal program interpreters, 25 exact products, and a two-level 16x16 recursive test.
See verification.json for per-map counts and proof check output.
