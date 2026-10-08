# Review: why finitely many helper equations suffice

Scope: fixed rational target forms of full rank d, arbitrary rational input basis, binary additions/subtractions, free copies/signs. A doubling x+x is one gate. This classification does not automatically include primitive nonunit scalar gates. It is independent of a denominator cutoff for the basis or helper forms.

First remove every zero wire and every computed wire equal up to sign to an earlier wire. Subsequent uses can be redirected for free. The d input forms are independent, so no input is removed. In the resulting circuit with c gates there are N=d+c distinct signed physical wire forms. Choose q of these wires representing the q distinct signed target forms, and call the remaining h=N-q wires helpers. Targets span the full d-dimensional physical space.

Write M for the N×d matrix of all physical forms. Its rational relation space K=ker(M^T) has dimension N-d=c. Each actual gate supplies one relation: the new output minus its two signed operands. These c relation vectors are linearly independent. Indeed, in any nonzero linear combination choose the latest gate with a nonzero coefficient; its output coordinate occurs with coefficient one in that relation and cannot occur in any earlier relation. Therefore the actual gate relations form a basis of K.

Now project K onto the h helper coordinates. For every helper H_j, full target rank supplies rational coefficients lambda_i with H_j=sum_i lambda_i T_i. The relation e_Hj−sum_i lambda_i e_Ti belongs to K and projects to the jth standard basis vector of Q^h. Hence projection is surjective. Because the actual gate relations span K, their projected helper-coefficient rows span Q^h. Select h of those rows that are linearly independent. Their coefficient matrix A is invertible, and the corresponding physical gate equations give exactly

    A H = R,       H = A^(-1) R.

Here R consists of signed target sums or single targets, or zero. Its possibilities are finite. For each selected gate, up to an overall equation sign, the nonzero helper coefficients have one of the forms:

- e_i, right side a sum/difference of two targets, permitting the same target twice;
- 2e_i, right side a signed target;
- e_i±e_j, right side a signed target;
- 2e_i±e_j, right side zero;
- e_i±e_j±e_k with distinct indices, right side zero.

No gate has more than three physical wire occurrences. This exhausts all coefficient rows. Invertibility means the selected rows cannot repeat up to sign. All-zero right sides for an invertible A force H=0 and can be discarded. Column permutations/signs correspond to helper renaming/sign changes; row permutations/signs correspond to equation reordering/negation. These actions preserve completeness and the allowed right-side sets.

The diagonal coefficient-matrix cases give independent helpers of the forms ±T_i±T_j or ±T_i/2. Therefore a complete enumeration of every h-element subset of that exact anchor pool covers all diagonal cases; excluding target-equal, zero, or duplicate signed helpers is legitimate. Nondiagonal patterns require the full rational construction above, not just this anchor pool.

A candidate may contain h helpers even when no acyclic circuit realizes it. This relaxation is intentional. The formal-quotient screen is a necessary condition and cannot establish circuit existence by itself. Conversely, excluding every candidate from the complete coefficient/right-side construction excludes every h-helper circuit. Cases with fewer than h helpers can be checked separately, or covered by the padding argument below.

Independent checks in this session: exact three-helper pattern coverage matches 124 active orbits; exact four-helper coverage matches 1,911 active orbits. The three-helper 2×3×4 enumeration was replayed using generic all-wire pair relations and matched every production count and quotient histogram. Separate exact-rational sampled audits matched the specialized relation rules for both three and four helpers. These checks validate the enumerations described; they do not turn an unfinished four-helper RHS run into an exhaustive result.

## Padding fewer helpers to an exact helper budget

Let P be the set of nonzero signed-canonical target sums/differences T_i±T_j, including repeated targets. Suppose P contains at least H distinct forms outside the target set. Given any circuit with h<H helpers, at most h of those forms are already helpers. Append H−h fresh target-sum gates after all targets are available, selecting distinct forms outside the targets and earlier helpers. This does not alter the outputs. Each appended gate adds one distinct helper and one independent latest-output relation. The resulting circuit has exactly H helpers and q+H−d gates. Thus exclusion of **all** exact-H helper circuits also excludes every circuit with fewer helpers, even if the padded gates are unused by any output.

`helper_padding_audit.json` verifies the needed target-pair pool cardinalities for the selected 2×3×3 and 2×3×4 factors. This padding uses ordinary signed additions only; it does not rely on the half-target candidates in the broader anchor pool.

## Independent-block RHS symmetries

Form the bipartite graph with helper vertices i, RHS vertices j, and an edge whenever (A^(-1))_ij is nonzero. Negating every RHS in one connected component negates exactly the helpers in that component and leaves all other helpers unchanged. Since helper signs are free and helper vectors are canonically signed before testing, this operation leaves the candidate set unchanged. It is safe to fix the sign of the first nonzero RHS in each component. An all-zero RHS component produces zero helpers and is invalid.

For isolated one-helper/one-RHS components, equal absolute inverse-matrix coefficients and equal RHS domains make the blocks interchangeable. Ordering their canonically signed RHS vectors removes only helper permutations and is safe. This conclusion is restricted to those genuinely isolated blocks; a broader RHS ordering would require a separate symmetry argument.

## Completed small-factor conclusions

For the selected 233 V map, q=15 and d=9. A ten-addition circuit has at most four helpers. Padding reduces every smaller-helper possibility to the four-helper case. The complete coefficient census has1,911 active orbits: five diagonal orbits are covered by all1,206,363,501 four-element subsets of the414-helper pool; all1,906 nondiagonal orbits are covered by the original199-pattern run and the1,707-pattern symmetric continuation. Every case has target formal quotient dimension at least10, exceeding d=9. Therefore V requires at least11 additions. The other two forward maps meet their elementary target-count bounds9 and9; transposition adds15−6=9 to the decoder. Together with the exact9+11+18 upper certificate this proves kernel minimum38 for this fixed-scale decomposition under arbitrary rational coordinate bases in the signed-addition model.

For the selected 234 V map, q=20 and d=12. Eleven additions permit at most three helpers. All124 active coefficient orbits are covered: four diagonal cases by the complete anchor triples, and120 nondiagonal cases by16,519,420 RHS assignments. Every candidate has target formal quotient dimension at least13>d. Thus V requires at least12 additions. The other forward maps meet their elementary bounds12 and12, and transposition adds20−8=12. The exact12+12+24 certificate therefore attains the minimum48 in the same fixed-scale signed-addition model.

For completeness, if G is the span over F₂ of every allowed formal gate support on the target/helper candidate set, the dimension of the target image in the quotient is

    q + rank(projection_helpers(G)) − rank(G).

This follows from rank–nullity for projection restricted to G. In a real circuit the actual gate supports generate a quotient from its d input symbols; enlarging the relation space to G cannot increase the target-image dimension. Hence a computed value greater than d rules out the candidate. F₂ is used for formal wire labels, not for reducing rational physical forms.

These exact minima do not include free rank-term rescalings or arbitrary unary scalar gates. The stronger projective51 theorem treats such gauges and counted unary gates with a separate geometric argument.
