#!/usr/bin/env python3
"""Choose helper vectors to omit from an auxiliary-target reconstruction.

This is a heuristic ordering of experiments, not an SLP lower bound. Native
surviving seeds are optional wanted forms, not required outputs. Scoring uses
a stronger surrogate that requires the surviving seeds; native may skip or
prune them. Indices in
``removed_native_helper_indices`` match new-improvements LEO getIntermediates:
non-unit-support, sign-canonical, non-output vectors, first occurrence only.
The native solver may recreate omitted forms; the finite-pool score instead
forbids them to estimate whether their omission opens a useful reconnection.
Only exact integer vector identities are used. No third-party modules required.
"""
import argparse
from collections import defaultdict
import heapq
import itertools
import json
from pathlib import Path
import random
import time


def canonical(vector):
    vector = tuple(vector)
    first = next((x for x in vector if x), 0)
    if not first:
        raise ValueError("Zero vectors are unsupported")
    sign = 1 if first > 0 else -1
    return tuple(sign * x for x in vector), sign


def require(value, message):
    if not value:
        raise ValueError(message)


class RemovalSelector:
    """Validated donor/pool with cached, deterministic removal scores."""

    def __init__(self, circuit, pool=None):
        self.circuit = circuit
        n = self.n = circuit["inputs"]
        require(type(n) is int and n > 0, "Positive integer input count required")
        values = [tuple(int(i == j) for j in range(n)) for i in range(n)]
        self.forms = list(values)
        ids = {v: i for i, v in enumerate(values)}

        def add_form(vector):
            form, _ = canonical(vector)
            if form not in ids:
                ids[form] = len(self.forms)
                self.forms.append(form)
            return ids[form]

        self.productions = defaultdict(set)
        self.wire_forms = list(range(n))
        self.original_production = {}
        for j, gate in enumerate(circuit["gates"]):
            require(isinstance(gate, list) and len(gate) == 4, "Binary gate required")
            a, sa, b, sb = gate
            require(type(a) is int and type(b) is int and 0 <= a < n + j
                    and 0 <= b < n + j, "Gate references a later/invalid wire")
            require(type(sa) is int and type(sb) is int and sa in (-1, 1)
                    and sb in (-1, 1), "Only integer signs +/-1 supported")
            v = tuple(sa * x + sb * y for x, y in zip(values[a], values[b]))
            values.append(v)
            out = add_form(v)
            self.wire_forms.append(out)
            _, orient = canonical(v)
            _, oa = canonical(values[a])
            _, ob = canonical(values[b])
            aa, bb = self.wire_forms[a], self.wire_forms[b]
            p = (aa, sa * oa * orient, bb, sb * ob * orient)
            if aa > bb:
                p = (bb, p[3], aa, p[1])
            if out >= n and out not in (aa, bb):
                self.productions[out].add(p)
                self.original_production.setdefault(out, p)

        self.targets = set()
        actual = []
        for w, sign in circuit["outputs"]:
            require(type(w) is int and 0 <= w < len(values)
                    and type(sign) is int and sign in (-1, 1), "Invalid output")
            self.targets.add(self.wire_forms[w])
            actual.append([sign * x for x in values[w]])
        require(actual == circuit.get("target_matrix", actual), "Donor map mismatch")
        self.source_forms = set(self.wire_forms[n:]) - set(range(n))

        # Exactly the dense filtered helper indexing used by the native branch.
        self.helpers = []
        seen_helpers = set()
        for j, v in enumerate(values[n:]):
            form = self.wire_forms[n + j]
            if sum(x != 0 for x in v) < 2 or form in self.targets or form in seen_helpers:
                continue
            seen_helpers.add(form)
            self.helpers.append(dict(native_helper_index=len(self.helpers),
                                     gate_index_0based=j, wire_id=n + j,
                                     form_id=form, canonical_coefficients=list(self.forms[form])))

        if pool is None:
            # Small incumbent-only exact algebraic reconnection graph.
            for a, va in enumerate(self.forms):
                for b in range(a, len(self.forms)):
                    vb = self.forms[b]
                    for sa, sb in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                        out = ids.get(tuple(sa * x + sb * y for x, y in zip(va, vb)))
                        if out is not None and out >= n and out not in (a, b):
                            self.productions[out].add((a, sa, b, sb))
            self.pool_origin = "all exact binary productions within donor forms"
        else:
            require(pool["inputs"] == n, "Pool input dimensions differ")
            require(pool.get("target_matrix", actual) == actual, "Pool output map differs")
            translate = []
            for i, v in enumerate(pool["forms"]):
                require(len(v) == n and all(type(x) is int for x in v), "Invalid pool coefficients")
                fv, orientation = canonical(v)
                require(orientation == 1, "Pool forms must be sign-canonical")
                if i < n:
                    require(tuple(v) == values[i], "Pool roots differ")
                translate.append(add_form(fv))
            for out_s, options in pool["productions"].items():
                out = translate[int(out_s)]
                for a, sa, b, sb in options:
                    require(sa in (-1, 1) and sb in (-1, 1), "Invalid pool sign")
                    aa, bb = translate[a], translate[b]
                    require(self.forms[out] == tuple(sa * x + sb * y
                            for x, y in zip(self.forms[aa], self.forms[bb])), "False pool identity")
                    if out >= n and out not in (aa, bb):
                        self.productions[out].add((aa, sa, bb, sb))
            self.pool_origin = "validated supplied exact production pool plus donor identities"

        self.edges = [(o, *p) for o in sorted(self.productions)
                      for p in sorted(self.productions[o])]
        self.consuming_edges = defaultdict(list)
        for eid, (o, a, sa, b, sb) in enumerate(self.edges):
            self.consuming_edges[a].append(eid)
            if a != b:
                self.consuming_edges[b].append(eid)
        self.consumers = defaultdict(set)
        for out, (a, _, b, _) in self.original_production.items():
            self.consumers[a].add(out)
            self.consumers[b].add(out)
        self.score_cache = {}

    def _closure(self, forbidden, mandatory):
        """Exact reachability with a single acyclic, shared-ancestor witness.

        Greedy queue order prefers derivations introducing fewer pool-only
        helpers. The first derivation of a form is frozen. Consequently this
        witness is feasible, but its gate count is not a minimum.
        """
        n = self.n
        available = set(range(n))
        support = {i: 0 for i in range(n)}
        chosen = {}
        remaining = []
        for o, a, _, b, _ in self.edges:
            remaining.append(len({a, b} - available))
        heap = []
        mandatory_mask = sum(1 << o for o in mandatory)

        def propose(eid):
            o, a, sa, b, sb = self.edges[eid]
            if o in forbidden or o in available:
                return
            nodes = support[a] | support[b] | (1 << o)
            optional = (nodes & ~mandatory_mask).bit_count()
            heapq.heappush(heap, (optional, nodes.bit_count(), o, eid, nodes))

        for eid, count in enumerate(remaining):
            if count == 0:
                propose(eid)
        while heap:
            _, _, o, eid, nodes = heapq.heappop(heap)
            if o in available:
                continue
            available.add(o)
            support[o] = nodes
            chosen[o] = self.edges[eid][1:]
            for dep in self.consuming_edges[o]:
                remaining[dep] -= 1
                if remaining[dep] == 0:
                    propose(dep)
        used = 0
        for o in mandatory & available:
            used |= support[o]
        missing = mandatory - available
        return available, chosen, used, missing

    def score(self, native_helper_indices):
        key = tuple(sorted(native_helper_indices))
        require(len(key) == len(set(key)) and 0 < len(key) <= 8,
                "Choose one to eight different native helpers")
        require(all(type(i) is int and 0 <= i < len(self.helpers) for i in key),
                "Native helper index out of range")
        if key in self.score_cache:
            return self.score_cache[key]
        removed = {self.helpers[i]["form_id"] for i in key}
        # Scoring surrogate ONLY: require surviving hint vectors as well as
        # original outputs. Native wanted vectors are optional and may never be
        # built or may be pruned, so this is not a bound on native feasibility.
        retained_helpers = {h["form_id"] for h in self.helpers} - removed
        mandatory = (retained_helpers | self.targets) - set(range(self.n))
        available, chosen, support, missing = self._closure(removed, mandatory)
        boundary = {c for r in removed for c in self.consumers[r] if c not in removed}
        boundary_alternatives = {}
        for out in boundary:
            options = [p for p in self.productions[out]
                       if p[0] not in removed and p[2] not in removed]
            boundary_alternatives[out] = len(options)
        optional = (support & ~sum(1 << o for o in mandatory)).bit_count()
        baseline_mandatory = ({h["form_id"] for h in self.helpers} | self.targets) - set(range(self.n))
        result = dict(
            removed_native_helper_indices=list(key),
            removed_gate_indices_0based=[self.helpers[i]["gate_index_0based"] for i in key],
            removed_wire_ids=[self.helpers[i]["wire_id"] for i in key],
            removed_form_ids=sorted(removed),
            retained_auxiliary_targets=len(retained_helpers),
            survivor_requirement_scope="stronger scoring surrogate only; native survivors are optional hints",
            required_distinct_noninput_forms=len(mandatory),
            missing_required_forms=len(missing),
            missing_original_output_forms=len((self.targets - set(range(self.n))) - available),
            boundary_retained_forms=len(boundary),
            boundary_forms_without_direct_alternative=sum(v == 0 for v in boundary_alternatives.values()),
            direct_alternative_productions=sum(boundary_alternatives.values()),
            # Counts a union, never sum-of-independent ancestor costs.
            greedy_witness_optional_helpers=optional,
            greedy_witness_gates=support.bit_count() if not missing else None,
            greedy_witness_gain_vs_distinct_targets=(len(baseline_mandatory) - support.bit_count())
                if not missing else None,
            omitted_forms_forbidden_in_scoring=True,
            heuristic_only=True)
        result["priority"] = [
            result["missing_original_output_forms"], result["missing_required_forms"],
            optional, result["boundary_forms_without_direct_alternative"],
            result["boundary_retained_forms"], -result["direct_alternative_productions"]]
        result["rationale"] = (
            f"Scoring surrogate: omit {len(key)} helper vectors and require all {len(retained_helpers)} surviving hints plus original outputs. "
            f"Exact pool closure misses {len(missing)} required forms. "
            f"Its greedy acyclic witness uses {optional} pool-only helpers. "
            f"{len(boundary)} retained forms directly consumed omitted helpers; "
            f"{result['boundary_forms_without_direct_alternative']} have no direct alternative in this pool. "
            "Native survivors are optional: unused hints can be skipped or pruned. "
            "This stronger surrogate orders trials; it neither bounds nor predicts native final counts.")
        self.score_cache[key] = result
        return result

    def select(self, k_values=range(1, 9), seed=17017, per_k=2, beam_width=4, expansion_width=16):
        require(per_k > 0 and beam_width > 0 and expansion_width > 0, "Positive search widths required")
        requested = sorted(set(k for k in k_values if 1 <= k <= min(8, len(self.helpers))))
        if not requested:
            return {"guided": [], "random_controls": [], "helpers": self.helpers}
        beam = [()]
        guided = []
        all_indices = list(range(len(self.helpers)))
        for k in range(1, max(requested) + 1):
            candidates = set()
            for base in beam:
                # Cheap structural screen; exact pool closure then ranks the
                # survivors. At k=1 score every helper.
                expansions = []
                for i in all_indices:
                    if i in base:
                        continue
                    group = tuple(sorted((*base, i)))
                    removed = {self.helpers[j]["form_id"] for j in group}
                    boundary = {c for r in removed for c in self.consumers[r] if c not in removed}
                    noalt = sum(not any(a not in removed and b not in removed
                                       for a, _, b, _ in self.productions[o]) for o in boundary)
                    expansions.append(((noalt, len(boundary), group), group))
                shortlist = expansions if k == 1 else sorted(expansions)[:expansion_width]
                candidates.update(group for _, group in shortlist)
            ranked = sorted(candidates, key=lambda g: (self.score(g)["priority"], g))
            beam = ranked[:beam_width]
            if k in requested:
                for rank, group in enumerate(ranked[:per_k], 1):
                    guided.append({**self.score(group), "kind": "guided", "k": k, "rank": rank})
        rng = random.Random(seed)
        controls = []
        for k in requested:
            used = set()
            count = min(per_k, len(list(itertools.combinations(all_indices, k)))
                        if len(all_indices) <= 12 else per_k)
            while len(used) < count:
                group = tuple(sorted(rng.sample(all_indices, k)))
                if group in used:
                    continue
                used.add(group)
                controls.append({**self.score(group), "kind": "seeded_uniform_random", "k": k,
                                 "rank": len(used), "random_seed": seed})
        return dict(schema="perminov-vector-target-removal-selection-v1", seed=seed,
                    raw_binary_donor_gates=len(self.circuit["gates"]),
                    eligible_native_helpers=len(self.helpers), pool_forms=len(self.forms),
                    pool_productions=len(self.edges), pool_origin=self.pool_origin,
                    index_semantics="dense 0-based getIntermediates helper list, not raw gate indices",
                    score_semantics="stronger scoring surrogate: forbid omitted forms and require all surviving hint vectors plus original outputs in finite pool; native can recreate omissions, skip surviving hints and introduce other forms; greedy witness is neither optimum nor native bound",
                    guided=guided, random_controls=controls, helpers=self.helpers)


def select_removals(circuit, k_values=range(1, 9), pool=None, seed=17017, per_k=2, **kwargs):
    return RemovalSelector(circuit, pool).select(k_values, seed, per_k, **kwargs)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--circuit", type=Path, required=True)
    p.add_argument("--pool", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", type=int, default=17017)
    p.add_argument("--per-k", type=int, default=2)
    p.add_argument("--k", default="1,2,3,4,5,6,7,8")
    args = p.parse_args()
    start = time.perf_counter()
    circuit = json.loads(args.circuit.read_text())
    pool = json.loads(args.pool.read_text()) if args.pool else None
    result = select_removals(circuit, map(int, args.k.split(",")), pool, args.seed, args.per_k)
    result.update(circuit_file=str(args.circuit), pool_file=str(args.pool) if args.pool else None,
                  selector_wall_seconds=time.perf_counter() - start)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("eligible_native_helpers", "pool_forms", "pool_productions", "selector_wall_seconds")}))


if __name__ == "__main__":
    main()
