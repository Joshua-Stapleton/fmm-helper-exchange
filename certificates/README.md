# Exact algorithm and proof certificates

Certificates are also colocated with the methods that generate or verify them:

- Root `certificate_666_587.zip`: ordinary6×6,153 products,587 additions.
- `methods/linear/`: ordinary5×5,93 products,332 additions, plus search witnesses.
- `methods/basis/`: 4×4 alternative169+43; 3×3 fixed-source and finite-transformation lower bounds; smaller canonical-basis results.
- `methods/structure/`: rational pair-span rigidity for fixed rank48/rank49 sources.
- `methods/storage/certificate_204_storage_19/`: ordinary4×4,204 linear operations,48 products; certified output-storage schedule.
- `certificate_8x8_1250_268/`: mixed4×4/2×2 rank336 composition,1250 kernel additions,268 conversion operations including16 halvings;1854 one-level total with products.

The8×8 composition uses the known alternative-basis rank7 component of Schwartz and Vaknin, [Pebbling Game and Alternative Basis for High Performance Matrix Multiplication](https://epubs.siam.org/doi/10.1137/22M1502719). The4×4 source is the collaborative rank48 algorithm, not a new rank discovery here. Run `python3 -B verify.py` inside that certificate folder. It checks both base tensors, every composed linear map and exact ordinary-coordinate examples.

Counts must retain their field, conversion and sign assumptions. Kernel counts are not ordinary-coordinate totals; lower bounds have explicitly limited models.
