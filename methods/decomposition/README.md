# Rational span moves and geometric helper candidates

`span_moves.py` extracts two October4 methods as standard-library exact functions:

1. Given a proposed rank-one pair `a⊗b` in the span of old pair products, solve its coefficients exactly, replace any old term with nonzero coefficient, and compensate every third-factor row. Full tensor replay confirms the change. This can explore moves beyond a single shared-factor flip. It does not guarantee ternarity, lower rank or fewer additions.
2. Enumerate minimally dependent target quadruples and intersect their two-target spans to generate basis-independent helper directions. A direction still needs a chosen magnitude and a realizable construction; projective normalization is not free scaling in an addition circuit.

Run `python3 -B methods/decomposition/span_moves.py` for exact positive/negative controls. Use `replace(A,B,C,av,bv,drop)` and `four_target_directions(rows)` as library functions; caller-owned candidate generation can use the transformation tools and persistent queue. These expose the reusable algebra without bundling the old corpus-specific launches or NumPy scanning loops.

The fixed4×4 rational rigidity proof in `../structure/` shows that these pair-span replacements cannot find a new direction for its rank48/rank49 sources. They remain applicable to other sources, such as the rank15 neighbors explored in the earlier experiment. Larger transformations preserving those fixed spans do not evade that theorem.

Underlying linear algebra, rank-one replacement and span intersections are not claimed as new inventions. Source implementations: `focused_research_20261004/small_schemes/pair_span_moves.py` and `focused_research_20261004/new_decompositions/four_target_intersections.py`.
