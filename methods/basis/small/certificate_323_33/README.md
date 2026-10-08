# Rank-15 3x2 by 2x3 multiplication:33 core additions plus 10 conversions

Run `python3 verify.py`; only the Python standard library is needed. It verifies all 324 rational tensor identities, exact basis compositions, both representations of all circuits, literal operation counts and canonical coordinates.

The kernel uses 15 products plus33 binary additions/subtractions, split9+9+15. Boundary conversion costs are2+2+6=10 more additions/subtractions, so an isolated ordinary-coordinate multiplication costs43 additions plus15 products, or58 scalar operations. There are zero unary negations and zero scalar gates. All6/6/9 canonical coordinates appear in the three forward factors.

This is the cyclic (W,U,V) rotation of the accompanying233 rank15 construction. Each forward map costs 9 additions. The output width is9, so transposition adds15-9=6 to the third forward count, producing15 decoder additions and33 total. The233 variant's output width 6 instead produces an18-addition decoder and36 total. The shape distinction matters when comparing reported bounds.

The source is Perminov's AlphaTensor233 seed, with signed rank-term gauges, basis-coordinate signs, and the stated cyclic tensor rotation. The full provenance and matrices are in scheme323.json. The accompanying233 lower certificate proves the forward costs 9/9/9 optimal with fixed target scalings, arbitrary rational bases and signed binary gates; cyclic rotation gives the corresponding33 lower bound here. It is not a global optimality or record claim.

Flatten inputs in row-major order; apply u_boundary.slp and v_boundary.slp, then u.slp and v.slp. Form15 coordinatewise products, then apply w.slp and w_boundary.slp. The nine outputs list the3x3 product in column-major order. Every SLP uses only copies and literal binary + or -.

Prepared locally for review; nothing was published or sent.
