# Exact certificate: 5x7x7, 176 products, 701 additions

This bundle computes a 5x7 matrix times a 7x7 matrix using the original 176-product
scheme from Andrei Perminov's collection. The three original signed linear maps
are unchanged. Their addition counts decrease from **205 + 236 + 347 = 788** to
**180 + 205 + 316 = 701**, giving **877 total arithmetic operations** including
the 176 products. This is an exact upper bound for this scheme, not a claim of
global optimality, a fastest implementation, or a best bound among all schemes.

From the repository root:

```sh
python3 -I -B certificates/scheme_5x7x7_176/verify.py
```

Or copy this directory anywhere and run `python3 -I -B verify.py` inside it.
Python's standard library is sufficient. The verifier checks all bundle hashes,
replays the original source expressions and both sets of numeric and literal
programs, and checks all **60025** coefficients of the complete tensor. The
tensor has **245** nonzero coefficients, all equal to one. No extra unary
negations, nonunit scalar operations or unused assignments are accepted.

## Coordinates and operation counting

For zero-based indices, U consumes `a[7*i+j] = A[i,j]`, V consumes
`b[7*j+k] = B[j,k]`, and W produces `c[5*k+i] = C[i,k]`. Thus A and B use
row-major coordinates, while the original W uses column-major output
coordinates. The product with index `s` is `U(A)[s] * V(B)[s]`; W consumes these
products in the same order. The verifier checks the identity
`sum_s W[o,s]*U[s,a]*V[s,b]` against this exact coordinate convention.

Every binary addition or subtraction costs one operation. Copies and output
aliases cost zero. All gates needed by the input and output programs are
included. There are no external basis conversions, sign diagonals or added
products. `U.slp`, `V.slp` and `W.slp` are ordinary literal programs in the
original coordinates; the corresponding `.json` files are separate numeric
witnesses. The `baseline/` programs certify the original 205/236/347 counts.

## Provenance and method

The original source is [Perminov's FastMatrixMultiplication repository](https://github.com/dronperminov/FastMatrixMultiplication),
at commit `6c75fd36564b177165d6968efd4c9e6199266191`, file
`schemes/results/addition_reduced_ZT/5x7x7_m176_cr788_fv371_cn2605_ZT_reduced.json`.
`source.json` preserves those original bytes, with SHA-256
`5dd82fa0ee198f63108e1dbf412cc33a683b3c493697180a739bf83fb89464f2`.
`V.sms` preserves the uploaded map bytes, with SHA-256
`5df6fc138883423e9b6467264760b1b4b783539b075c77e934dff1c845f1134e`.
The U and W SMS matrices are expanded from that same original source.

Joshua Stapleton assembled alternative circuits using paid residual output
forests, LEO completion and repair, then pooled intermediate forms and searched
alternative shared dependencies. Transposing the W linear circuit was a search
device; the final W program is transposed back and verified in the original
coordinates. LEO is credited to [Perminov's linear-expression optimizer](https://github.com/dronperminov/linear-expressions-optimization);
the experiments used upstream commit `2abd2fd8f15dc1c97dd24777515324f865e77504`.
The public [pool builder](../../make_pool.py) and
[plateau search](../../methods/linear/search.py) describe the final reconnection
stage. This bundle verifies a completed result; verification does not repeat
the heuristic discovery search.

For V, the final 205-addition program uses 19 intermediate forms absent from
the initial methods-only pool. A matched trial with the 20 intelligent-start
donors removed also reached 205 additions, and the published V program uses
none of their 19 unique forms. This result therefore does not establish an
advantage for that initialization heuristic.

`manifest.json` checks every file except itself. `verification.json` is a saved
successful verification output; rerun the command to check the bundle locally.
