#!/usr/bin/env python3
"""Stdlib read-only check of complete-depth-three data and any witness."""
import importlib.util
import json
import sys
sys.dont_write_bytecode = True
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("depth3_generator", HERE / "search.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
g = json.loads((HERE / "catalogue.json").read_text())
values = g["forms"]
assert len(values) == len(set(values))
roots = set(g["root_indices"])
targets = set(g["target_indices"])
assert {values[i] for i in roots} == {1 << i for i in range(32)}
assert [values[i] for i in g["target_indices"]] == gen.audit.fips_masks()
incoming = {}
for c, a, b in g["all_exact_productions"]:
    assert c not in roots and a != b and values[c] == values[a] ^ values[b]
    assert a not in targets and b not in targets
    incoming.setdefault(c, set()).add((a, b))
    wc, wa, wb = values[c].bit_count(), values[a].bit_count(), values[b].bit_count()
    if c in targets:
        assert wc in (5, 7) and 1 <= wa <= 4 and 1 <= wb <= 4
    elif wc == 2:
        assert wa == wb == 1
    elif wc == 3:
        assert sorted((wa, wb)) == [1, 2]
    elif wc == 4:
        assert wa == wb == 2
    else:
        raise AssertionError("An unsupported helper layer was included")
for i, value in enumerate(values):
    if i in roots:
        continue
    expected = (285 if value.bit_count() == 5 else 35) if i in targets else (1 if value.bit_count() == 2 else 3)
    assert len(incoming[i]) == expected
check = gen.independent_split_check(g)
assert check["all_split_sets_equal"] and check["outputs_checked"] == 32
hint = gen.official_hint(g)
print("Official hint:", gen.audit.verify_witness(g, hint))
path = HERE / "depth3.witness.json"
if path.exists():
    replay = gen.audit.verify_witness(g, json.loads(path.read_text()))
    assert replay["depth"] <= 3
    print("Saved witness:", replay)
assert gen.audit.mix_column([0xdb, 0x13, 0x53, 0x45]) == [0x8e, 0x4d, 0xa1, 0xbc]
print("All exact identities, helper layers, 32 complete output split sets, and FIPS example verified.")
