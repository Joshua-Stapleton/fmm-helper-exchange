#!/usr/bin/env python3
"""Small exact controls and portable regressions; optional C++/OR-Tools tests."""
import argparse
import copy
import itertools
import json
from pathlib import Path
import tempfile
from common import core, closure, frontier
from enrich import enrich
from orient import matrix, transpose
from independent_verify import verify

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-cpp", action="store_true")
    parser.add_argument("--with-solvers", action="store_true")
    args = parser.parse_args()
    checks = []
    for path in sorted((HERE / "data").glob("*pool.json")):
        _, _, incumbent, witness = core.load(path)
        checks.append(dict(check="exact_pool", name=path.name, incumbent=len(incumbent),
                           witness=None if witness is None else len(witness)))
    toy, prods, incumbent, _ = core.load(HERE / "data/toy_exchange_pool.json")
    targets = {o for o, _ in toy["outputs"]}
    ready, _ = closure(toy, prods, set())
    boundary = frontier(ready, prods)
    assert not targets <= ready and boundary
    optional = sorted(set(range(toy["inputs"], len(toy["forms"]))) - targets)
    feasible = 0
    best = 100
    for bits in itertools.product((0, 1), repeat=len(optional)):
        hs = {h for h, bit in zip(optional, bits) if bit}
        reached, raw = closure(toy, prods, hs)
        if targets <= reached:
            assert hs & boundary  # Independent complete small cut check.
            feasible += 1
            best = min(best, len(core.audit(raw, toy, prods)))
    assert best == 3 and feasible > 0
    checks.append(dict(check="all_toy_helper_subsets", minimum=best, feasible=feasible))
    c = dict(inputs=2, gates=[[0, 1, 1, 1], [0, 1, 1, -1]], outputs=[[2, 1], [3, -1]])
    assert matrix(transpose(c)) == list(map(list, zip(*matrix(c))))
    assert matrix(transpose(transpose(c))) == matrix(c)
    checks.append(dict(check="signed_transpose", status="PASS"))
    with tempfile.TemporaryDirectory(prefix="fmm-linear-test-") as temporary:
        temp = Path(temporary)
        for mode in ("shared", "linked"):
            d, report = enrich(toy, 8, 200, mode)
            path = temp / (mode + ".json")
            path.write_text(json.dumps(d))
            core.load(path)
            assert report["added_forms"] > 0
        broken = copy.deepcopy(toy)
        out = next(iter(broken["productions"]))
        broken["productions"][out][0][1] *= -1
        bad = temp / "corrupted.json"
        bad.write_text(json.dumps(broken))
        try:
            core.load(bad)
        except ValueError:
            checks.append(dict(check="reject_corrupt_production", status="PASS"))
        else:
            raise AssertionError("Corrupt production was accepted")
        if args.with_cpp:
            from search import search
            result = search(HERE / "data/toy_exchange_pool.json", temp / "plateau", 1, 8, 3)
            assert result.get("additions_signed") == 3
            result = search(HERE / "data/toy_pool.json", temp / "beam", 1, 8, 3, "beam")
            assert "BEAM_COMPLETE_4_FOR_3" in result["diagnostic"]
            checks.append(dict(check="cpp_search_controls", status="PASS"))
        if args.with_solvers:
            from reachability import optimize, valid_cut
            result = optimize(HERE / "data/toy_exchange_pool.json", temp / "cuts", 10)
            assert result["status"] == "FOUND" and result["additions_signed"] == 3
            for cut in json.loads((temp / "cuts/cuts.json").read_text()):
                valid_cut(toy, prods, cut)
            result = optimize(HERE / "data/toy_pool.json", temp / "infeasible", 10)
            assert result["status"] == "FINITE_POOL_INFEASIBLE"
            from orient import orient
            candidates = {s: json.loads((HERE / "data" / ("5"+s+"_candidate.json")).read_text()) for s in "uvw"}
            oriented = orient(dict(u=candidates["u"], v=candidates["v"], w=transpose(candidates["w"])))
            assert [len(oriented[s]["nodes"]) for s in "uvw"] == [87, 88, 157]
            checks.append(dict(check="joint_orientation_332", status="EXACT_SIGN_COMPENSATION_PASS"))
    checks.append(dict(check="independent_literal_tensor", result=verify(HERE / "certificate_555_332")))
    print(json.dumps(dict(status="PASS", checks=checks), indent=2))


if __name__ == "__main__":
    main()
