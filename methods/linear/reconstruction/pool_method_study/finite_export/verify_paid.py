#!/usr/bin/env python3
"""Independent integer replay for paid partial or complete binary programs."""
import argparse
import hashlib
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(vector):
    sign = next((1 if x > 0 else -1 for x in vector if x), None)
    require(sign is not None, "Zero coefficient vector is not a helper")
    return tuple(sign * x for x in vector), sign


def read_matrix(path):
    path = Path(path)
    if path.suffix.lower() == '.json':
        data = json.loads(path.read_text())
        matrix = data.get('target_matrix') if isinstance(data, dict) else data
    else:
        lines = [line.split() for line in path.read_text().splitlines()
                 if line.strip() and not line.lstrip().startswith('#')]
        require(lines and len(lines[0]) >= 2, "Missing matrix header")
        rows, inputs = map(int, lines[0][:2])
        require(rows > 0 and inputs > 0, "Positive matrix dimensions required")
        matrix = [[0] * inputs for _ in range(rows)]
        if path.suffix.lower() == '.sms':
            seen = set()
            for tokens in lines[1:]:
                require(len(tokens) == 3, "SMS triple required")
                row, column, value = map(int, tokens)
                if (row, column, value) == (0, 0, 0):
                    continue
                require(1 <= row <= rows and 1 <= column <= inputs,
                        "SMS coordinate out of range")
                require((row, column) not in seen, "Duplicate SMS coordinate")
                seen.add((row, column))
                matrix[row - 1][column - 1] = value
        else:
            require(len(lines) == rows + 1, "Wrong dense row count")
            matrix = [list(map(int, line)) for line in lines[1:]]
    require(isinstance(matrix, list) and matrix and isinstance(matrix[0], list)
            and matrix[0], "Nonempty matrix required")
    columns = len(matrix[0])
    for row in matrix:
        require(isinstance(row, list) and len(row) == columns,
                "Rectangular matrix required")
        require(all(type(value) is int for value in row) and any(row),
                "Nonzero integer target rows required")
    return matrix


def replay(data, target=None, budget=None, require_unique=True):
    """Count every stored gate, including unused initial helpers.

    Unit signs are part of the abstract signed-wire model. This verifier does
    not certify that all signs admit a literal program without unary negation.
    """
    inputs = data.get('inputs')
    require(type(inputs) is int and inputs > 0, "Positive integer inputs required")
    gates = data.get('gates')
    require(isinstance(gates, list), "Gate array required")
    if budget is not None:
        require(type(budget) is int and budget >= 0, "Nonnegative gate budget required")
        require(len(gates) <= budget, "Paid program exceeds gate budget")
    values = [tuple(int(i == j) for j in range(inputs)) for i in range(inputs)]
    known = {canonical(vector)[0] for vector in values}
    for index, gate in enumerate(gates):
        wire = inputs + index
        require(isinstance(gate, list) and len(gate) == 4,
                "Each gate must contain two wires and two signs")
        left, sign_left, right, sign_right = gate
        require(type(left) is int and type(right) is int
                and 0 <= left < wire and 0 <= right < wire,
                "Gate has missing, forward or cyclic parent")
        require(type(sign_left) is int and sign_left in (-1, 1)
                and type(sign_right) is int and sign_right in (-1, 1),
                "Gate contains a free nonunit scalar")
        vector = tuple(sign_left * x + sign_right * y
                       for x, y in zip(values[left], values[right]))
        form, _ = canonical(vector)
        if require_unique:
            require(form not in known, "Signed alias is stored as a paid helper")
        known.add(form)
        values.append(vector)
    report = dict(status='PASS',inputs=inputs,paid_initial_gates=len(gates),
                  unique_computed_signed_forms=len(known),
                  model='abstract unit signed wires; strict orientation separate')
    outputs = data.get('outputs')
    if outputs is not None:
        require(isinstance(outputs, list) and outputs, "Nonempty output list required")
        actual = []
        for output in outputs:
            require(isinstance(output, list) and len(output) == 2, "Output pair required")
            wire, sign = output
            require(type(wire) is int and 0 <= wire < len(values)
                    and type(sign) is int and sign in (-1, 1), "Invalid signed output")
            actual.append([sign * coefficient for coefficient in values[wire]])
        if target is not None:
            require(actual == target, "Complete program changes the ordered signed map")
        report['ordered_output_rows'] = len(actual)
        report['complete_exact_map_verified'] = target is not None
    if target is not None:
        require(all(len(row) == inputs for row in target), "Input dimension changed")
        forms = {canonical(row)[0] for row in target}
        report['target_rows'] = len(target)
        report['target_unique_signed_forms'] = len(forms)
        report['covered_target_unique_signed_forms'] = len(forms & known)
        report['covered_target_ordered_rows_up_to_sign'] = sum(
            canonical(row)[0] in known for row in target)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('program', type=Path)
    parser.add_argument('--matrix', type=Path)
    parser.add_argument('--budget', type=int)
    parser.add_argument('--allow-aliases', action='store_true')
    args = parser.parse_args()
    target = read_matrix(args.matrix) if args.matrix else None
    raw = args.program.read_bytes()
    report = replay(json.loads(raw), target, args.budget, not args.allow_aliases)
    report['program_sha256'] = hashlib.sha256(raw).hexdigest()
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
