Exact certificates for nineteen fixed matrix multiplication schemes

Run from this folder:

python3 -I -B verify_all.py

The verifier uses only the Python standard library. It checks SHA256 hashes,
expands the original published source DAGs, compares all uploaded SMS maps,
replays each of 57 final programs with exact rational coefficient vectors,
counts all binary additions/subtractions, rejects extra unary negations and
nonunit scalars, rejects unused assignments, and checks every complete
multiplication tensor. A/B inputs are row-major and C outputs are column-major.

There is no arithmetic basis change. Products and ranks are unchanged.
These files certify fixed decompositions, not global records or optimality.
To multiply A by B, apply U.slp to row-major A entries and V.slp to row-major
B entries, multiply corresponding U and V outputs, then apply W.slp to these
products to obtain column-major C entries. Aliases cost zero; every binary
addition/subtraction is counted. All scalar products are charged.

Original decompositions and historical reductions: Andrey Perminov.
Source repository, exact checkout commit, original source hashes, uploaded
archive hash and current phase counts are in claims.json. Four previously
published totals are retained for comparisons with the previous release.
Original source files and uploaded matrices are preserved byte for byte.

Reduction experiments use upstream linear-expressions-optimization, weighted
HelperPool starts, shared-residual forests, paid-chain reconstruction, finite
pool global reconnection, and charged transposition searches. Complete scripts
and provenance are in fmm-helper-exchange. Public results use relative paths.
