#!/usr/bin/env python3
"""Exact paid transposition, magnitude, original signs and parameter controls."""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile


def check(solvers=False):
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("adjoint_pool", here/"adjoint_pool.py")
    method = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(method)
    # A single paid WT sum becomes two paid W sums. All return accumulations
    # count; the original input roots and row order are preserved.
    original = [[1, 1, 0], [0, 1, 1]]
    adjoint = method.transpose_matrix(original)
    donor = dict(inputs=2, gates=[[0, 1, 1, 1]], outputs=[[0, 1], [2, 1], [1, 1]])
    result = method.paid_transpose(donor, adjoint)
    assert result["inputs"] == 3 and len(result["gates"]) == 2
    assert method.api.exact_circuit(result, 3) == original
    assert len(donor["gates"]) == 1, "Transposition must not mutate saved donors"
    back = method.paid_transpose(result, original)
    assert method.api.exact_circuit(back, 2) == adjoint

    # A real coefficient two is built by doubling. Neither normalization nor
    # transposition may projectively identify 2*x with x or make scaling free.
    magnitude_adjoint = [[2, 0], [1, -1], [0, 1]]
    magnitude_original = method.transpose_matrix(magnitude_adjoint)
    magnitude_donor = dict(inputs=2, gates=[[0, 1, 0, 1], [0, 1, 1, -1]],
                           outputs=[[2, 1], [3, 1], [1, 1]])
    magnitude_result = method.paid_transpose(magnitude_donor, magnitude_adjoint)
    assert len(magnitude_result["gates"]) == 3
    assert method.api.exact_circuit(magnitude_result, 3) == magnitude_original
    assert magnitude_result["target_matrix"] == [[2, 1, 0], [0, -1, 1]]

    def reject(callback):
        try:
            callback()
        except ValueError:
            return
        raise AssertionError("Malformed input was accepted")

    bank = dict(inputs=2, circuits=[donor])
    prepared, target, direct = method.prepare_bank(bank, original, result)
    assert target == adjoint and direct["target_matrix"] == original
    assert len(prepared["circuits"]) == 2
    reject(lambda: method.prepare_bank(dict(inputs=3, circuits=[donor]), original))
    reject(lambda: method.prepare_bank(dict(inputs=2, circuits=[]), original))
    reject(lambda: method.checked(dict(donor, inputs=True), adjoint))
    reject(lambda: method.checked(dict(donor, target_matrix=[[1, 0], [0, 1], [1, 1]]), adjoint))
    reject(lambda: method.checked(dict(donor, gates=[[3, 1, 1, 1]]), adjoint))
    reject(lambda: method.checked(dict(donor, outputs=[[0, -1], [2, 1], [1, 1]]), adjoint))
    reject(lambda: method.prepare_bank(bank, original, dict(result, outputs=[[3, -1], [4, 1]])))
    reject(lambda: method.paid_transpose(dict(inputs=2, gates=[], outputs=[[0, 1]]), [[1, 0]]))

    with tempfile.TemporaryDirectory(prefix="adjoint-pool-test-") as temporary:
        folder = Path(temporary)
        matrix_path, bank_path, candidate_path = (folder/name for name in ("original.json", "bank.json", "candidate.json"))
        matrix_path.write_text(json.dumps(original))
        bank_path.write_text(json.dumps(bank))
        candidate_path.write_text(json.dumps(result))
        defaults = dict(matrix=matrix_path, donors=bank_path, candidate=candidate_path,
                        out=folder/"result", backend="python", binary=None, compiler=None,
                        search_seconds=0.0, seed=0, width=10, orient_seconds=None)
        for changes in (dict(search_seconds=float("nan")), dict(search_seconds=-1),
                        dict(search_seconds=float("inf")), dict(seed=-1), dict(seed=2**32),
                        dict(width=0), dict(width=True), dict(orient_seconds=0),
                        dict(orient_seconds=float("inf")), dict(backend="unknown"),
                        dict(binary=folder/"binary")):
            reject(lambda changes=changes: method.run(argparse.Namespace(**dict(defaults, **changes))))
            assert not (folder/"result").exists(), "Invalid parameters created an output directory"
        report = method.run(argparse.Namespace(**defaults))
        saved = json.loads((folder/"result/best_candidate.json").read_text())
        assert report["additions_signed"] == 2 and report["basis_change"] is False
        assert report["search"]["status"] == "DISABLED"
        assert report["relation_binary_build_seconds"] == 0
        assert report["exact_ordered_original_map_verified"] is True
        assert method.api.exact_circuit(saved, 3) == original
        before = (folder/"result/summary.json").read_bytes()
        reject(lambda: method.run(argparse.Namespace(**defaults)))
        assert (folder/"result/summary.json").read_bytes() == before, "Existing output was overwritten"
        if solvers:
            literal, text, orientation = method.orient_fixed(result, original, 2)
            assert orientation["exact_original_map_verified"] and literal is not None
            assert orientation["binary_additions"] == 2
            assert orientation["unary_negations"] == orientation["nonunit_scalars"] == orientation["unused_gates"] == 0
            assert method.api.exact_circuit(literal, 3) == original and text.count(":=") == 4
            doubling = dict(inputs=1, gates=[[0, 1, 0, 1]], outputs=[[1, 1]])
            literal, text, orientation = method.orient_fixed(doubling, [[2]], 2)
            assert literal is not None and orientation["binary_additions"] == 1
            assert method.api.exact_circuit(literal, 1) == [[2]]
            assert text == "t0:=i0+i0;\no0:=t0;\n"
            assert orientation["unary_negations"] == orientation["nonunit_scalars"] == 0
            negative_output = dict(inputs=2, gates=[[0, 1, 1, -1]], outputs=[[2, -1]])
            literal, text, orientation = method.orient_fixed(negative_output, [[-1, 1]], 2)
            assert literal is not None and method.api.exact_circuit(literal, 2) == [[-1, 1]]
            assert text == "t0:=i1-i0;\no0:=t0;\n"
            assert orientation["binary_additions"] == 1
            impossible = dict(inputs=1, gates=[], outputs=[[0, -1]])
            literal, text, orientation = method.orient_fixed(impossible, [[-1]], 2)
            assert literal is text is None and orientation["status"] == "INFEASIBLE"
    return dict(status="PASS", controls="Paid transpose, magnitudes, fixed signs, cycles, dimensions, invalid parameters, no overwrite",
                standard_library_only=not solvers, optional_fixed_sign_tests=solvers)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solvers", "--solver", dest="solvers", action="store_true", help="Also test optional OR-Tools fixed-sign feasibility")
    print(json.dumps(check(parser.parse_args().solvers), indent=2))
