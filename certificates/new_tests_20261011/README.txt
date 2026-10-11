Exact certificates for six fixed matrix multiplication schemes

Run from this folder:

python3 -I -B verify_all.py

The verifier uses only the Python standard library. It checks SHA256 hashes,
expands the original published source DAGs, compares all uploaded SMS maps,
replays each final program with exact rational coefficient vectors, counts
all binary additions/subtractions, rejects extra unary negations and nonunit
scalars, rejects unused assignments, and checks each full multiplication
tensor. A/B inputs are row-major and C outputs are column-major storage.

There is no input or output arithmetic basis change. Products are unchanged.
The files certify these fixed decompositions, not global records or optimality.
To multiply A by B, apply U.slp to row-major A entries and V.slp to
row-major B entries, multiply corresponding U and V outputs, then apply
W.slp to these products to obtain column-major C entries. Aliases cost zero;
every binary addition/subtraction is counted. All products are charged.

Original decompositions and historical reductions: Andrey Perminov.
Source repository and exact checkout commit are in claims.json.
Reduction experiments combine upstream linear-expressions-optimization
with shared-residual forests, paid-chain reconstruction, and finite-pool
global reconnection. The complete scripts are in fmm-helper-exchange.
