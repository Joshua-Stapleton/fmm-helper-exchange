# Optimal conversion cost with all canonical coordinates: 2+6+2=10

Run `python3 verify.py`. It needs the Python standard library and a C++17 compiler. It rebuilds the complete two-helper enumerator, checks all attained2+6+2 conversion circuits and their target-row basis membership, and tests every possible signed target-row basis of the fixed V factor. A typical replay takes several seconds.

For the accompanying fixed rank-15 233 decomposition, the V conversion has minimum six binary additions/subtractions among all fully canonical bases. U and W each require at least two conversions, so the full staged boundary minimum is ten. The accompanying 36+10 construction attains both the independent kernel lower bound and this conversion lower bound, while retaining all 6/9/6 canonicals. Cyclic rotation gives 33+10 for 323 with 6/6/9 canonicals.

The lower model permits arbitrary rational helper forms and free signs/copies. The upper circuits use only literal binary additions/subtractions, with no unary negations or scalar gates. Target coefficients are fixed up to signs. Arbitrary magnitude term gauges are excluded. This theorem concerns separate conversion stages and fully canonical bases. It is not a lower bound for noncanonical bases or for an ordinary-coordinate circuit that fuses conversions with the core.

All C(15,9)=5,005 candidate V bases are classified: 2,275 contain more than five nonunit output forms; 2,266 remaining subsets are singular; 464 bases require a helper census. Those split into eight cases with three nonunit forms, 96 with four, and 360 with five. The complete search finds no conversion circuit of at most five additions. It checks 16,320 one-helper candidates and 352,896 two-helper assignments (347,760 valid). See PROOF.md for the exact completeness argument.

The JSON contains the exact source factor, bases and retained circuits. The separate 233/323 bundles independently verify the entire multiplication tensor and all literal programs. No global or universal optimality claim is made.

An independent reviewer checked the basis reduction, Hadamard rank test, helper classification, sign symmetries, native filter, fixed-root closure and W-transposition argument. The standalone replay also verifies the U/W attained two-addition conversions.
