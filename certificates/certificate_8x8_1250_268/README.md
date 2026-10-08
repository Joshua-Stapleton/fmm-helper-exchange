# Certified rank336 alternative-basis8x8 composition

Run `python3 verify.py` in this folder using ordinary Python3.

Core: 1250 scalar linear operations. Conversion maps: 268 operations. Products:336. The core count excludes conversion and is not an ordinary-coordinate multiplication count. Isolated one-level ordinary multiplication costs 1854 operations including all conversions. There are no uncounted unary negations. Division by2 must exist.

The 4x4 component is the displayed, independently certified rank-48 component. The 2x2 component is the known 12-addition alternative-basis algorithm of Schwartz and Vaknin, Pebbling Game and Alternative Basis for High Performance Matrix Multiplication, SIAM2023, https://epubs.siam.org/doi/10.1137/22M1502719 . This is a mixed composition and circuit optimization experiment, not a rank, exponent or priority claim.

All six composed linear maps are checked against Kronecker products of their displayed4x4 and2x2 factors. Both base multiplication tensors are checked exhaustively; three exact ordinary8x8 products are also checked after conversions.
