# Why a common square filtration gives only ordinary column sectors

This elementary representation constraint addresses the literal next-step suggestion in the October 7 tensor report. It is valid over every field K; no novelty is claimed.

Identify the right input and output spaces of square matrix multiplication with Mat_n(K). Fix the full first-input space, so its slices are all left multiplications `L_A: B -> AB`.

Suppose a proposed paired invariant layer consists of equal-dimensional spaces U in the right input and V in the output with `A U subset V` for every A. Taking A=I gives U subset V, hence U=V. Thus U is a left ideal of Mat_n(K).

Let R be the span in K^n of every row appearing in a matrix in U. Applying matrix units E_ij extracts row j and places it in row i. Stability therefore puts in U every matrix with any one row in R and all other rows zero. By summing, U contains all matrices whose rows belong to R. The reverse inclusion follows from the definition of R. Consequently

    U = K^n tensor R,          dim U = n dim R.

Every chain of equal-dimensional paired invariant layers is therefore an ordinary flag of column-coordinate sectors, after a change of coordinates on the n-dimensional row-vector factor. Such layers have dimensions divisible by n. A complement of R produces a simultaneous invariant complement, so in a suitable basis every L_A is block diagonal, and its off-diagonal residual is zero.

For n=3 the only proper nonzero layer dimensions are 3 and 6; for n=4 they are 4,8,12. This explains why the polynomial determinant filtration, which has genuine off-diagonal residuals and changing layer lengths, cannot transfer literally to the full M3/M4 slice family by a square change of basis.

This argument leaves open restricted first-input spaces, unequal paired dimensions, restrictions/degenerations, non-square constructions, and joint processing of several slices. It is a constraint on that specific proposed search route, not a general matrix-multiplication lower bound.
