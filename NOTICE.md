# Attribution and provenance

The research implementations and portable packaging here are associated with Joshua Stapleton's September–October2026 work. This does not assign priority to standard ideas such as common-subexpression elimination, linear transposition, Gaussian elimination, circuit scheduling, weighted matching, local search, CP-SAT, finite-field reduction or signed-permutation symmetry.

Important sources:

- Andrey Perminov's [FastMatrixMultiplication](https://github.com/dronperminov/FastMatrixMultiplication) supplies many exact source decompositions. His [linear-expressions-optimization](https://github.com/dronperminov/linear-expressions-optimization) supplies CSE/vector-cover/distance donor methods. Scheme and reducer commits/hashes are preserved in the relevant provenance records. Neither upstream repository is relabeled as original code here.
- The partial reconstruction methods use his unchanged `solution_optimization` branch at commit `2abd2fd8f15dc1c97dd24777515324f865e77504`. The113/141/200 follow-up programs come from this upstream reducer; selective-cut and pooled-form wrappers and population-export instrumentation are distinguished from the external solver. No upstream library sources or binaries are vendored for this update.
- Jean-Guillaume Dumas's [PLinOpt](https://github.com/jgdumas/plinopt) is an external reducer used in the research and optional queue adapters. Its executable/source is not bundled.
- Jean-Guillaume Dumas, Clément Pernet, Alexandre Sedoglavic, Joshua Stapleton and Petr Tichavský, [Fast matrix multiplication via recursive ⟨4×4×4:48⟩ algorithms into practice](https://arxiv.org/abs/2609.12027v2), supplies the collaborative rank48 context and204-operation reference. The source decomposition is not claimed as a new discovery in this repository.
- The rank49 reference is Perminov's pinned `4x4x4_m49_cr159_fv100_cn474_ZT_reduced.json` at commit `f200e684283c0d1a15f0efbc548439ba72fb8382`; no additional ancestry is inferred here. Small scheme certificates preserve their individual source/decomposition provenance, including AlphaTensor ancestry where applicable.
- Schwartz and Vaknin's [Pebbling Game and Alternative Basis for High Performance Matrix Multiplication](https://epubs.siam.org/doi/10.1137/22M1502719) supplies the known alternative-basis2×2 component in the rank336 composition.
- [Kauers and Moosbauer](https://arxiv.org/abs/2212.01175) supply the flip-graph framework; [Perminov](https://arxiv.org/abs/2511.20317) describes ternary-safe transformation primitives predating these experiments.

Upstream notices and licenses included with data/certificates remain applicable. No new blanket license in this release overrides upstream rights. File-level provenance records identify portable adaptations and original source hashes. Arithmetic certificates establish their stated identities and counts; neither those checks nor repository publication establishes literature priority or peer review.
