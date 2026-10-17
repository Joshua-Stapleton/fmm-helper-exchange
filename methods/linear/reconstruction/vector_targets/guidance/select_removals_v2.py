#!/usr/bin/env python3
"""Output-only removal score: surviving hints are optional, omissions may recur.

This version preserves the frozen v1 schedules. It compares two finite-pool
reconstruction proxies, neither of which simulates the native solver exactly:
forbid omitted hints; or permit them with a small derivation-priority penalty.
Both prune to original outputs and count a union of shared ancestors.
"""
import argparse
from collections import defaultdict
import heapq
import json
from pathlib import Path
import time
from select_removals import RemovalSelector, canonical, require


class OptionalSurvivorSelector(RemovalSelector):
    def __init__(self, circuit, pool=None, max_abs=1, recreation_penalty_quarters=1):
        super().__init__(circuit, pool)
        require(type(max_abs) is int and max_abs >= 0, "Nonnegative integer max_abs required")
        require(type(recreation_penalty_quarters) is int and recreation_penalty_quarters >= 0,
                "Nonnegative integer penalty required")
        self.max_abs = max_abs
        self.recreation_penalty_quarters = recreation_penalty_quarters
        self.invalid = {i for i, v in enumerate(self.forms) if max_abs and max(map(abs, v)) > max_abs}
        self.original_helpers = {h["form_id"] for h in self.helpers}
        self.original_noninput_targets = self.targets - set(range(self.n))
        self.original_count = len(self.original_helpers | self.original_noninput_targets)

    def _output_closure(self, removed, allow_recreation):
        available = set(range(self.n))
        support = {i: 0 for i in range(self.n)}
        chosen = {}
        blocked = self.invalid | (set() if allow_recreation else removed)
        omitted_mask = sum(1 << i for i in removed)
        original_mask = sum(1 << i for i in self.original_helpers | self.original_noninput_targets)
        remaining = [len({a, b} - available) for _, a, _, b, _ in self.edges]
        queue = []

        def propose(eid):
            o, a, sa, b, sb = self.edges[eid]
            if o in blocked or o in available:
                return
            nodes = support[a] | support[b] | (1 << o)
            recreated = (nodes & omitted_mask).bit_count()
            # Integer quarters make the actual perturbation preference explicit.
            novel = (nodes & ~original_mask).bit_count()
            penalty = self.recreation_penalty_quarters * recreated if allow_recreation else 0
            # Retained hints give a preference, not a requirement. Anchoring
            # derivations to known donor forms preserves global sharing that
            # separately short output derivations can otherwise destroy.
            heapq.heappush(queue, (4 * novel + penalty,
                                  nodes.bit_count(), recreated, o, eid, nodes))

        for eid, count in enumerate(remaining):
            if count == 0:
                propose(eid)
        while queue:
            _, _, _, out, eid, nodes = heapq.heappop(queue)
            if out in available:
                continue
            available.add(out)
            support[out] = nodes
            chosen[out] = self.edges[eid][1:]
            for dep in self.consuming_edges[out]:
                remaining[dep] -= 1
                if remaining[dep] == 0:
                    propose(dep)
        needed = 0
        for out in self.original_noninput_targets & available:
            needed |= support[out]
        used = {i for i in range(self.n, len(self.forms)) if (needed >> i) & 1}
        missing = self.original_noninput_targets - available
        if not missing:
            # Reconnect a required form through two already-live ancestors if
            # that lets another branch disappear. This counts joint sharing;
            # separately shortest derivations can miss it. Two bounded passes,
            # no new form discovery or unconstrained combinatorial search.
            def live_after_rewire(out, production):
                reached, visiting = set(), set()

                def visit(wire):
                    if wire < self.n or wire in reached:
                        return True
                    if wire in visiting:
                        return False
                    visiting.add(wire)
                    a, _, b, _ = production if wire == out else chosen[wire]
                    if not visit(a) or not visit(b):
                        return False
                    visiting.remove(wire)
                    reached.add(wire)
                    return True

                if all(visit(t) for t in self.original_noninput_targets):
                    return reached
                return None

            for _ in range(2):
                changed = False
                references = defaultdict(int)
                for used_out in used:
                    aa, _, bb, _ = chosen[used_out]
                    for parent in {aa, bb}:
                        references[parent] += 1
                for out in sorted(used, reverse=True):
                    if out not in used:
                        continue
                    old_a, _, old_b, _ = chosen[out]
                    droppable = {p for p in {old_a, old_b} if p >= self.n
                                 and p not in self.original_noninput_targets and references[p] == 1}
                    if not droppable:
                        continue
                    for production in sorted(self.productions[out]):
                        if production == chosen[out]:
                            continue
                        a, _, b, _ = production
                        if droppable <= {a, b}:
                            continue
                        if (a >= self.n and a not in used) or (b >= self.n and b not in used):
                            continue
                        trial = live_after_rewire(out, production)
                        if trial is not None and len(trial) < len(used):
                            chosen[out] = production
                            used = trial
                            changed = True
                            references = defaultdict(int)
                            for used_out in used:
                                aa, _, bb, _ = chosen[used_out]
                                for parent in {aa, bb}:
                                    references[parent] += 1
                if not changed:
                    break
            needed = sum(1 << i for i in used)
        used_helpers = used - self.original_noninput_targets
        unused_survivors = (self.original_helpers - removed) - used_helpers
        recreated = removed & used_helpers
        novel = used_helpers - self.original_helpers
        k, d, b, q = len(removed), len(unused_survivors), len(recreated), len(novel)
        gain = None if missing else self.original_count - len(used)
        if not missing:
            require(gain == k + d - b - q, "Output-only helper accounting failed")
        return dict(proxy="recreation_allowed" if allow_recreation else "omissions_forbidden",
                    missing_original_output_forms=len(missing),
                    signed_normalized_gates=len(used) if not missing else None,
                    normalized_gain=gain, unused_surviving_hints_d=d,
                    recreated_omitted_hints_b=b, novel_helper_forms_q=q,
                    recreation_priority_penalty_quarters=self.recreation_penalty_quarters if allow_recreation else 0,
                    survivors_are_optional=True), chosen, needed

    def score(self, native_helper_indices):
        key = tuple(sorted(native_helper_indices))
        require(len(key) == len(set(key)) and 0 < len(key) <= 8,
                "Choose one to eight different native helpers")
        require(all(type(i) is int and 0 <= i < len(self.helpers) for i in key),
                "Native helper index out of range")
        if key in self.score_cache:
            return self.score_cache[key]
        omitted = {self.helpers[i]["form_id"] for i in key}
        proxies = [self._output_closure(omitted, False)[0],
                   self._output_closure(omitted, True)[0]]

        def rank(row):
            return (row["missing_original_output_forms"],
                    row["signed_normalized_gates"] if row["signed_normalized_gates"] is not None else 10**9,
                    row["recreated_omitted_hints_b"], row["novel_helper_forms_q"])

        best = min(proxies, key=rank)
        result = dict(removed_native_helper_indices=list(key),
                      removed_gate_indices_0based=[self.helpers[i]["gate_index_0based"] for i in key],
                      removed_wire_ids=[self.helpers[i]["wire_id"] for i in key],
                      removed_form_ids=sorted(omitted),
                      original_distinct_noninput_forms=self.original_count,
                      proxy_evaluations=proxies, best_proxy=best, priority=list(rank(best)),
                      max_abs_proxy=self.max_abs, heuristic_only=True,
                      rationale=(
                          f"Only original outputs are required in both proxies; surviving hints may disappear. "
                          f"Best proxy {best['proxy']} has {best['signed_normalized_gates']} gates, "
                          f"skips {best['unused_surviving_hints_d']} surviving hints, recreates "
                          f"{best['recreated_omitted_hints_b']} omissions and uses {best['novel_helper_forms_q']} novel helper forms. "
                          "Exact pool identities and acyclic witnesses justify these proxy counts, not native predictions or optimality."))
        self.score_cache[key] = result
        return result

    def select(self, *args, **kwargs):
        result = super().select(*args, **kwargs)
        result.update(schema="perminov-vector-target-removal-selection-v2",
                      score_semantics="only original outputs required; output ancestor union from finite exact pool; compare forbidden omissions and recreation with explicit priority penalty; no hard survivor constraints",
                      max_abs_proxy=self.max_abs,
                      recreation_penalty_quarters=self.recreation_penalty_quarters)
        return result

    def export_proxy(self, native_helper_indices, allow_recreation=True):
        """Materialize and independently replay the chosen output-only DAG."""
        omitted = {self.helpers[i]["form_id"] for i in native_helper_indices}
        report, chosen, needed = self._output_closure(omitted, allow_recreation)
        require(report["missing_original_output_forms"] == 0, "Proxy does not reach all original outputs")
        raw = [tuple(int(i == j) for j in range(self.n)) for i in range(self.n)]
        for a, sa, b, sb in self.circuit["gates"]:
            raw.append(tuple(sa*x+sb*y for x,y in zip(raw[a], raw[b])))
        target = [tuple(s*x for x in raw[w]) for w,s in self.circuit["outputs"]]
        ids = {v:i for i,v in enumerate(self.forms)}
        remap = {i:i for i in range(self.n)}
        values = list(raw[:self.n])
        gates = []
        visiting = set()

        def visit(out):
            if out in remap:
                return remap[out]
            require(out not in visiting, "Proxy witness has a cycle")
            visiting.add(out)
            a, sa, b, sb = chosen[out]
            aa, bb = visit(a), visit(b)
            value = tuple(sa*x+sb*y for x,y in zip(values[aa], values[bb]))
            require(value == self.forms[out], "Proxy witness coefficient replay failed")
            remap[out] = self.n + len(gates)
            gates.append([aa, sa, bb, sb])
            values.append(value)
            visiting.remove(out)
            return remap[out]

        outputs = []
        for row in target:
            form, orientation = canonical(row)
            outputs.append([visit(ids[form]), orientation])
        actual = [tuple(s*x for x in values[w]) for w,s in outputs]
        require(actual == target and len(gates) == report["signed_normalized_gates"],
                "Proxy output replay/count mismatch")
        return dict(inputs=self.n, gates=gates, outputs=outputs,
                    target_matrix=[list(row) for row in target],
                    free_signed_wires=True, additions_signed=len(gates),
                    proxy_report=report)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--circuit", type=Path, required=True)
    p.add_argument("--pool", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", type=int, default=17017)
    p.add_argument("--per-k", type=int, default=2)
    p.add_argument("--max-abs", type=int, default=1)
    args = p.parse_args()
    start = time.perf_counter()
    selector = OptionalSurvivorSelector(json.loads(args.circuit.read_text()),
        json.loads(args.pool.read_text()) if args.pool else None, args.max_abs)
    result = selector.select(seed=args.seed, per_k=args.per_k)
    result.update(circuit_file=str(args.circuit), pool_file=str(args.pool) if args.pool else None,
                  selector_wall_seconds=time.perf_counter() - start)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("eligible_native_helpers", "pool_forms", "pool_productions", "selector_wall_seconds")}))


if __name__ == "__main__":
    main()
