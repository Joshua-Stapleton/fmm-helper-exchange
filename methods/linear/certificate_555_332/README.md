# Ordinary-coordinate 5x5 multiplication: 332 additions, 93 products

Run `python3 -I -B verify.py`. Python's standard library is sufficient.
Both JSON and literal SLPs are replayed against the exact pinned decomposition;
all 15,625 tensor identities are checked with integers, including coordinated
rank-term signs. Counts: 87 + 88 + 157 = 332 binary
additions/subtractions plus 93 products = 425 scalar operations.
There are no unary-negation gates, nonunit scalar gates or basis conversions.

Source: Andrey Perminov's public rank-93 catalogue decomposition at commit
64f58a5e40806bc47847b11dd8aceec043fa895d. Search included historical donors and
117 new exact programs from his LEO reducer at commit60272dc3cdd751ce53e43e5c021dbb6021fcbf51,
then helper-pool expansion, randomized deletion and equal-cost plateau steps.
The U87 circuit reproduces a count already reported by Perminov;
this package provides our independently replayable construction and does not
establish priority, global optimality or a runtime improvement. The local exact
comparator was334=88+88+158. W was searched transposed with shift93-25=68.

Inputs U/V are row-major A/B; multiply the93 corresponding outputs pairwise;
run W on those93 products. W output5*j+i is C[i,j], a free storage permutation.
