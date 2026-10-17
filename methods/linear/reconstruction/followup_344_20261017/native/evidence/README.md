# Native check of 3x4x4 V, 17 October 2026

The supplied map has 38 outputs and 16 original inputs. Its header says "was 43". Unmodified pinned LEO vector-cover search found 41 signed binary gates directly, in its fifth scratch draw (seed 1719348). Exact fixed-sign orientation and a literal 41-operation certificate are separate, in the main certificate folder.

Four direct jobs produced 34,429 exactly replayed completions from 34,430 draws in 60.122 seconds of native process time. The 20-second scratch job was followed by exact two-vector omissions, three-vector omissions, and uniform 1..8 vector omissions. The latter jobs each stopped at 10,000 draws before their wall cap. These native omissions remove optional hint vectors; they do not prohibit the solver from reconstructing those vectors.

Transposed search used 10 seconds from scratch (no completion), then 20 seconds from the transposed incumbent (20 completions). The best adjoint had 63 gates and returned to 41 after charging the reverse circuit. It did not improve the original map.

The first 41-gate draw used approximately 0.02222 seconds of summed native sampling and solver time. This excludes startup, JSON output and verification, and must not be described as end-to-end runtime.

Run `python3 -I -B verify.py` to replay the source SMS, representative native witness, and 128 selected exact donor circuits. The full locally audited repeated raw logs are omitted; their SHA256 hashes are recorded. These results concern this fixed linear map, not a complete multiplication tensor or global optimality.
