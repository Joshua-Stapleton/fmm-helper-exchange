#!/usr/bin/env python3
"""Read-only, standard-library replay of the three GF(2) MixColumns studies.

Checks certificates and generated inventories, not CP-SAT lower-bound proofs.
"""
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent

manifest = json.loads((HERE / "FILE_MANIFEST.json").read_text())
assert manifest["file_count"] == len(manifest["files"])
for record in manifest["files"]:
    path = (HERE / record["file"]).resolve()
    assert path.is_relative_to(HERE)
    body = path.read_bytes()
    assert len(body) == record["bytes"]
    assert hashlib.sha256(body).hexdigest() == record["sha256"]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize(value):
    return json.loads(json.dumps(value))


audit = load("mixcolumns_root_audit", HERE / "probe.py")
provenance = json.loads((HERE / "provenance.json").read_text())
assert provenance["commit"] == audit.PIN
export = json.loads((HERE / "EXPORT_PROVENANCE.json").read_text())
for record in export["records"]:
    assert hashlib.sha256((HERE / record["file"]).read_bytes()).hexdigest() == record["export_sha256"]
assert hashlib.sha256((HERE / "sources/NIST_REPOSITORY_README.md").read_bytes()).hexdigest() == export["nist_repository_readme_sha256"]
circuits = []
for row in provenance["sources"]:
    body = (HERE / "sources" / row["file"]).read_bytes()
    assert hashlib.sha256(body).hexdigest() == row["sha256"]
    circuit = audit.parse_ncFF(body.decode())
    circuits.append(circuit)
    print(row["file"], circuit["gate_count"], circuit["depth"], "FIPS map verified")
graph = json.loads((HERE / "catalogue.json").read_text())
assert normalize(audit.catalogue(circuits)) == graph
for name in ("pool_any_depth", "pool_depth3"):
    w = json.loads((HERE / (name + ".witness.json")).read_text())
    actual = audit.verify_witness(graph, w)
    record = json.loads((HERE / (name + ".result.json")).read_text())
    assert actual == record["exact_replay"]
    print(name, actual["gate_count"], actual["depth"], "exact witness verified")

for folder, script in (("target_subsets", "extend.py"), ("complete_depth3", "search.py")):
    generator = load("mixcolumns_" + folder, HERE / folder / script)
    regenerated, inventory = generator.build()  # Read-only default guard.
    supplied = json.loads((HERE / folder / "catalogue.json").read_text())
    assert normalize(regenerated) == supplied
    witness = json.loads((HERE / folder / "depth3.witness.json").read_text())
    actual = audit.verify_witness(supplied, witness)
    record = json.loads((HERE / folder / "depth3.result.json").read_text())
    assert actual == record["exact_replay"]
    assert actual["depth"] <= 3
    if folder == "complete_depth3":
        split_check = generator.independent_split_check(supplied)
        assert split_check == json.loads((HERE / folder / "independent_split_check.json").read_text())
    print(folder, actual["gate_count"], actual["depth"], "inventory and witness verified")

omissions = json.loads((HERE / "MODEL_OMISSIONS.json").read_text())
for row in omissions["omitted_models"]:
    model = Path(row["file"])
    record_path = HERE / model.parent / model.name.replace(".model.pbtxt", ".result.json")
    assert not (HERE / model).exists()
    assert json.loads(record_path.read_text())["model_sha256"] == row["sha256"]

# Load the existing negative semantic controls without adding this directory
# to sys.path or writing an import cache.
sys.modules["probe"] = audit
controls = load("mixcolumns_semantic_controls", HERE / "test_probe.py")
suite = unittest.defaultTestLoader.loadTestsFromModule(controls)
result = unittest.TextTestRunner(verbosity=0).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
print("All three studies pass exact replay and seven semantic controls.")
print("Solver statuses/bounds are preserved records; this replay does not certify UNSAT or optimality.")
