#!/usr/bin/env python3
"""Exact paid-composition, signs, inputs, duplicates, and malformed-plan checks."""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile


def check(api_path=None):
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("output_forest", here/"output_forest.py")
    forest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(forest)
    api = forest.load_api(api_path)

    # One paid shared sum, plus two paid reconstruction gates. Originals and
    # duplicate outputs are all present; none of the seeded sums is free.
    target = [[1, 1, 0, 0], [1, 1, 1, 0], [1, 1, 0, 1], [1, 1, 1, 0]]
    plan = [(0, -1, 1, (1, 1, 0, 0), 1),
            (1, 0, 1, (0, 0, 1, 0), 1),
            (2, 0, 1, (0, 0, 0, 1), 1)]
    latent = dict(inputs=4, gates=[[0, 1, 1, 1]], outputs=[[4, 1], [2, 1], [3, 1]])
    candidate, charged, counts = forest.reconstruct_plan(target, plan, latent, api)
    assert counts == dict(latent_additions=1, reconstruction_additions=2,
                          charged_additions=3, normalization_savings=0, additions_signed=3)
    assert len(latent["gates"]) == 1, "Composing must not mutate solver gate counts"
    assert candidate["outputs"][1] == candidate["outputs"][3]
    assert api.exact_circuit(candidate, 4) == target

    # A coefficient-two residual is a real doubling gate, not a free scalar.
    # Three latent gates, plus one output reconstruction, cost four total.
    target2 = [[1, 1, 1], [1, 1, -1]]
    plan2 = [(0, -1, 1, (1, 1, 1), 1), (1, 0, 1, (0, 0, 2), -1)]
    latent2 = dict(inputs=3, gates=[[0, 1, 1, 1], [3, 1, 2, 1], [2, 1, 2, 1]],
                   outputs=[[4, 1], [5, 1]])
    candidate2, charged2, counts2 = forest.reconstruct_plan(target2, plan2, latent2, api)
    assert counts2["latent_additions"] == 3
    assert counts2["reconstruction_additions"] == 1
    assert counts2["charged_additions"] == counts2["additions_signed"] == 4
    assert len(latent2["gates"]) == 3
    assert api.exact_circuit(charged2, 3) == target2

    # Signed aliases preserve required output signs and fixed original roots.
    # This tests the signed representation; strict output negation cost must
    # still be checked separately before any literal-circuit count is claimed.
    signed_target = [[-1, 0], [0, 1], [-1, -1], [1, 1], [1, 1]]
    signed_plan = [(0, -1, 1, (1, 0), 1), (1, -1, 1, (0, 1), 1),
                   (2, 0, 1, (0, 1), 1)]
    signed_latent = dict(inputs=2, gates=[], outputs=[[0, 1], [1, 1]])
    signed, _, signed_counts = forest.reconstruct_plan(signed_target, signed_plan,
                                                      signed_latent, api)
    assert signed_counts["latent_additions"] == 0
    assert signed_counts["reconstruction_additions"] == signed_counts["additions_signed"] == 1
    assert signed["inputs"] == 2
    assert api.exact_circuit(signed, 2) == signed_target

    def reject(target_map, bad_plan, circuit):
        try:
            forest.reconstruct_plan(target_map, bad_plan, circuit, api)
        except ValueError:
            return
        raise AssertionError("Invalid composition was accepted")

    reject(target2, [(0, 1, 1, (0, 0, 2), 1), plan2[1]], latent2)  # cyclic/forward parent
    reject(target2, [plan2[0], plan2[0]], latent2)  # duplicate vertex
    reject(target2, [plan2[0], (1, 0, 1, (0, 0, -2), 1)], latent2)  # noncanonical residual
    reject(target2, [plan2[0], (1, 0, 1, (0, 0, 2), 1)], latent2)  # wrong signed identity
    reject(target2, plan2, dict(inputs=4, gates=latent2["gates"], outputs=latent2["outputs"]))
    reject(target2, plan2, dict(inputs=3, gates=latent2["gates"], outputs=[[4, 1], [5, -1]]))

    # Graph construction and selected rooted plans are deterministic for the
    # same seeds. Complete a toy latent map naively to verify each whole plan.
    graph = forest.prepare_graph(target, api)
    for seed in (0, 1, 8800, 8804):
        p = forest.make_plan(target, seed, .12, .15, api, graph)
        assert p == forest.make_plan(target, seed, .12, .15, api, graph)
        rows = forest.latent_forms(p)
        gates, outputs = [], []
        for row in rows:
            terms = [(i, x) for i, x in enumerate(row) if x]
            assert all(x in (-1, 1) for _, x in terms)
            wire, sign = terms[0]
            for right, right_sign in terms[1:]:
                gates.append([wire, sign, right, right_sign])
                wire, sign = 4 + len(gates) - 1, 1
            outputs.append([wire, sign])
        c, _, _ = forest.reconstruct_plan(target, p,
                                          dict(inputs=4, gates=gates, outputs=outputs), api)
        assert api.exact_circuit(c, 4) == target
    # Refuse malformed budgets/seeds before any file or external solver access.
    base_args = dict(api=api_path, trials=1, timeout=1.0, seconds=1.0,
                     seed=0, savings=.01, slack=4)
    for changes in (dict(trials=0), dict(timeout=float("inf")),
                    dict(seconds=float("nan")), dict(seed=-1),
                    dict(seed=2**32-1, trials=2), dict(savings=-.01),
                    dict(slack=-2)):
        arguments = argparse.Namespace(**{**base_args, **changes})
        try:
            forest.run(arguments)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid parameter was accepted")
    # No overwrites: refusal happens before compilation or driver execution.
    with tempfile.TemporaryDirectory(prefix="output-forest-test-") as directory:
        directory = Path(directory)
        matrix = directory/"matrix.json"
        matrix.write_text(json.dumps([[1, 0], [0, 1]]))
        marker = directory/"keep.txt"
        marker.write_text("keep")
        arguments = argparse.Namespace(**base_args, matrix=matrix, out=directory)
        try:
            forest.run(arguments)
        except FileExistsError:
            pass
        else:
            raise AssertionError("Existing output directory was overwritten")
        assert marker.read_text() == "keep"
    print("PASS: charged chains, coefficient-two residuals, unchanged latent gates, signs, roots, duplicates, exact identities, cycle rejection, deterministic plans, finite budgets, seeds, no overwrites")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", type=Path, help="Defaults to sibling common.py")
    check(parser.parse_args().api)
