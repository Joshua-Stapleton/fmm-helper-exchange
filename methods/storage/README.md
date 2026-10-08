# Fixed-DAG storage scheduling

`schedule.py` searches topological orders with a bounded beam, keeps outputs live, and reuses an operand buffer only on its last read. It reads a normalized graph from a certificate JSON and exports the schedule plus a physical allocation trace. Arithmetic and dependencies do not change. Bounds refer to immutable external inputs and atomic destructive last-use reuse; there is no recomputation.

The included existing204-operation certificate uses19 writable blocks for its output stage:16 output destinations and3 auxiliary blocks, while48 product blocks remain separate and read-only. It previously needed26 under source order. This is an attained upper bound, not a proof that18 is impossible, and not a full-recursion memory/bandwidth benchmark. Inputs precomputed before products require76 retained non-alias combinations in the specified policy.

```sh
python3 -B methods/storage/certificate_204_storage_19/verify.py
python3 -B methods/storage/schedule.py --width 600 --seconds 30 --seed 30 --out results/schedule
```

The certificate independently checks every read/write, exact maps, unchanged operation counts and4096 tensor identities. The portable search defaults to its P graph, but accepts `--graph other.json`. A new bounded run may return a different schedule or retain source order on timeout. The included C99 kernel implements the saved allocation. Its numerical use requires disjoint product/output/scratch buffers.

The underlying204-operation scheme belongs to the collaborative arXiv:2609.12027 work; this module contributes scheduling/search and explicit allocation evidence. No general novelty is claimed for beam scheduling or last-use register reuse.
