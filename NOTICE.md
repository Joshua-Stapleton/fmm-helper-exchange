# Attribution and provenance

The research implementations and portable packaging here are associated with Joshua Stapleton's September–October2026 work. This does not assign priority to standard ideas such as common-subexpression elimination, linear transposition, Gaussian elimination, circuit scheduling, weighted matching, local search, CP-SAT, finite-field reduction or signed-permutation symmetry.

Important sources:

- Andrey Perminov's [FastMatrixMultiplication](https://github.com/dronperminov/FastMatrixMultiplication) supplies many exact source decompositions. His [linear-expressions-optimization](https://github.com/dronperminov/linear-expressions-optimization) supplies CSE/vector-cover/distance donor methods. Scheme and reducer commits/hashes are preserved in the relevant provenance records. Neither upstream repository is relabeled as original code here.
- The partial reconstruction methods use his unchanged `solution_optimization` branch at commit `2abd2fd8f15dc1c97dd24777515324f865e77504`. The113/141/200 follow-up programs come from this upstream reducer; selective-cut and pooled-form wrappers and population-export instrumentation are distinguished from the external solver. No upstream library sources or binaries are vendored for this update.
- The October 10 rank 176 5×7×7 results preserve Perminov's original decomposition and use his external reducer for latent maps and partial completions. Shared-residual selection, paid chain scoring, exact pool reconnection and their controls are separate wrappers. Transposition and target factorization are established ideas; no unrestricted novelty claim is made.
- The October11 new-test archive uses six existing Perminov decompositions and unchanged product ranks. Both orientations of pooled linear-circuit search are combined with exact charged transposition; matched restart and paid-chain initialization controls are reported separately. This is a reusable wrapper around established operations, not a claim of a new globally optimal minimizer.
- The October11 helper-pool study calls Perminov's unchanged `solvers-time-limit` code at `21906e043ab0d652b588864893a07199b915a8e7`. His sampler already shares ancestors, prevents cycles and rolls back failed constructions. The complete-target reproduction, prefix-scoring controls and finite-catalogue diagnosis are distinguished from that upstream implementation; MIT attribution accompanies the adapted walk structure. No new addition record is claimed by this study.
- Jean-Guillaume Dumas's [PLinOpt](https://github.com/jgdumas/plinopt) is an external reducer used in the research and optional queue adapters. Its executable/source is not bundled.
- Jean-Guillaume Dumas, Clément Pernet, Alexandre Sedoglavic, Joshua Stapleton and Petr Tichavský, [Fast matrix multiplication via recursive ⟨4×4×4:48⟩ algorithms into practice](https://arxiv.org/abs/2609.12027v2), supplies the collaborative rank48 context and204-operation reference. The source decomposition is not claimed as a new discovery in this repository.
- The rank49 reference is Perminov's pinned `4x4x4_m49_cr159_fv100_cn474_ZT_reduced.json` at commit `f200e684283c0d1a15f0efbc548439ba72fb8382`; no additional ancestry is inferred here. Small scheme certificates preserve their individual source/decomposition provenance, including AlphaTensor ancestry where applicable.
- Schwartz and Vaknin's [Pebbling Game and Alternative Basis for High Performance Matrix Multiplication](https://epubs.siam.org/doi/10.1137/22M1502719) supplies the known alternative-basis2×2 component in the rank336 composition.
- [Kauers and Moosbauer](https://arxiv.org/abs/2212.01175) supply the flip-graph framework; [Perminov](https://arxiv.org/abs/2511.20317) describes ternary-safe transformation primitives predating these experiments.

Upstream notices and licenses included with data/certificates remain applicable. No new blanket license in this release overrides upstream rights. File-level provenance records identify portable adaptations and original source hashes. Arithmetic certificates establish their stated identities and counts; neither those checks nor repository publication establishes literature priority or peer review.

The October 17 study uses Perminov's unmodified `new-improvements` library at
`7c8b59864e000bdc880938428d8a1991ec1f0bea`. Retaining helper vectors as optional
wanted forms, omitting one through eight helpers, and the native vector-cover
solver are his contributions. The API adapter, frozen comparisons, guided
omission heuristics and their negative controls, exact donor provenance,
combination with existing pool reconstruction, and portable certificates are
separate experimental code. The upstream MIT notice is retained under
`methods/linear/reconstruction/vector_targets/toolchain/UPSTREAM_LICENSE`.
The four-addition 4x4x16 W improvement came from the previous frozen bank alone.

The later October 17 pool-policy study separates native omission sizes from
explicit finite-pool exchange radius. It adds bounded multi-start comparisons,
an exact last-replacement dependency filter and restricted-neighborhood
separation controls. The native completions still come from Perminov's
credited unmodified library. Multi-start, dependency analysis, uphill local
search and neighborhood enumeration are established ideas; this release
claims its measured fixed-map improvements and scoped filtering behavior,
without assigning unrestricted algorithmic priority or optimality.

The October12 archive campaign preserves nineteen existing Perminov decompositions and their product ranks. Its batch wrappers combine credited external donor/completion methods, actual weighted HelperPool sampling, exact pooled reconnection and charged linear transposition. Weighted intake explicitly materializes binary terminal sums; it is distinct from the native-boundary replication study. The experiments certify the supplied fixed maps, with no claim of a generally optimal minimizer.

The October12 binary-circuit study preserves NIST's source circuits at
`usnistgov/Circuits` commit `113aec82e939be46ad72522032df90cb4355f46c` and their
embedded attribution. The FIPS197 map is constructed independently for replay.
The GF(2) adapters and selection models are separate research code. XOR
synthesis, CP-SAT and circuit-depth arguments are established ideas; the
complete depth-three normalization is a derived, unmechanized argument with
no priority claim. No improved circuit, global optimum or hardware advantage
was found. See `methods/linear/gf2_mixcolumns_study/SOURCE_NOTICE.md`.
