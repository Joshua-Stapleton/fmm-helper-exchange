#!/usr/bin/env python3
"""Small exact alias/dependency regressions; optional bounded compiled searches."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("reconstruction_common", HERE/"common.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def tests(with_cpp=False):
    # A negative duplicate helper is used by an output and by a later gate.
    # Removing it must compensate both dependencies, preserving fixed signs.
    source = dict(inputs=3, gates=[[0, 1, 1, 1], [0, -1, 1, -1], [4, 1, 2, 1]],
                  outputs=[[5, 1], [4, -1]])
    expected = [[-1, -1, 1], [1, 1, 0]]
    normalized = api.normalize(source)
    api.require(api.exact_circuit(normalized, 3) == expected and len(normalized["gates"]) == 2,
                "Signed-alias normalization regression")
    removed, lost, kept = api.cut(normalized, (3,))
    api.require(removed == {3, 4} and lost == {3, 4} and not kept,
                "Cut failed to remove dependent gates")
    bad = dict(inputs=2, gates=[[0, 1, 2, 1]], outputs=[[2, 1]])
    try:
        api.normalize(bad)
    except ValueError:
        pass
    else:
        raise ValueError("Forward dependency was accepted")
    signed = api.convert(dict(additions=2, substitutions=[dict(i=0, ai=1, j=1, aj=1)],
                              expressions=[[dict(index=3, value=1), dict(index=2, value=-1)]]),
                         [[1, 1, -1]])
    api.require(len(signed["gates"]) == 2, "Residual expression conversion failed")
    verify = api.module("independent_reconstruction_fixture", HERE/"verify_fixture.py")
    verify.verify()
    with tempfile.TemporaryDirectory(prefix="partial-alias-test-") as temp:
        path = Path(temp)/"partial.txt"
        api.write_partial(path, [[1, 1]], [[0, 1, 1, 1], [0, -1, 1, -1]])
        try:
            api.read_partial(path)
        except ValueError:
            pass
        else:
            raise ValueError("Duplicate signed partial forms were accepted")
    if with_cpp:
        with tempfile.TemporaryDirectory(prefix="reconstruction-test-") as temp:
            temp = Path(temp)
            subprocess.run([sys.executable, "-I", "-B", str(HERE/"rebuild.py"),
                            "--data", str(api.ROOT/"methods/linear/data/toy_exchange_pool.json"),
                            "--out", str(temp/"search"), "--seconds", ".15", "--seed", "32"], check=True)
            result = api.json_read(temp/"search/result.json")
            if "additions_signed" in result:
                api.require(result["exact_map_verified"], "Compiled result was not exactly checked")
            # No optional helpers: the engine must stop safely rather than sample
            # a nonexistent helper during a perturbation.
            pool = api.builder.build_pool(dict(inputs=2, circuits=[dict(name="one_sum",
                gates=[[0, 1, 1, 1]], outputs=[[2, 1]])]))
            api.dump(temp/"no_helpers.json", pool)
            subprocess.run([sys.executable, "-I", "-B", str(HERE/"rebuild.py"),
                            "--data", str(temp/"no_helpers.json"), "--out", str(temp/"no_helpers"),
                            "--seconds", ".15", "--seed", "32"], check=True)
            result = api.json_read(temp/"no_helpers/result.json")
            api.require(result["baseline_additions_signed"] == 1 and "additions_signed" not in result,
                        "Zero-helper pool regression")
    return dict(status="PASS", signed_aliases=True, descendant_cut=True,
                malformed_dag_rejected=True, residual_expression_conversion=True,
                duplicate_partial_forms_rejected=True,
                independent_fixture=True, compiled_search=with_cpp)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-cpp", action="store_true")
    print(json.dumps(tests(parser.parse_args().with_cpp), indent=2))
