# Attribution and scope

The source circuits are the original NIST Circuit File Format files from [usnistgov/Circuits](https://github.com/usnistgov/Circuits/tree/113aec82e939be46ad72522032df90cb4355f46c/data/slp/aes/aes-mixcols), pinned at commit `113aec82e939be46ad72522032df90cb4355f46c`. Their embedded NIST attribution and comments are unchanged. `sources/NIST_REPOSITORY_README.md` preserves the pinned repository introduction. `provenance.json` records immutable URLs and source SHA-256 hashes.

The repository root at that commit contains `.gitignore`, `README.md`, `data` and `src`; no root license file was present. This study does not invent a license for the upstream material or override upstream rights. These donor circuits are not claimed as Joshua Stapleton's discoveries.

The Python GF(2) adapters, reconstruction models and benchmark packaging accompany Joshua Stapleton's October 2026 work. XOR minimization, shared-expression optimization, finite-catalogue reconstruction and CP-SAT are established ideas; no general novelty claim is made. The complete-depth-three normalization argument is explained as a derived argument for this experiment, not a mechanized theorem or claim of research priority.

The benchmark results establish exact identities and witnessed operation counts in their stated models. They establish no new circuit record, global optimality, hardware runtime/energy improvement. OR-Tools is an optional external dependency for rerunning searches; neither its implementation nor a solver binary is bundled. Default verification independently checks upper-bound circuits and generator inventories, not a solver's UNSAT/optimality proof.
