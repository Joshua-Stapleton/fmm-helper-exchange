"""Independent exact controls for the portable transformation methods."""
import itertools
import random
import unittest
from fractions import Fraction as Q
from sparse_identity import candidates, counts, determinant, dense, inverse_circuit
from ternary_shears import identity, product, self_test, verify_standard_tensor
from transforms import canonical_columns, two_shear_endpoints, sandwich_shear, transfer_matrix
from matching import optimal_disjoint_shears
from symmetry import find


def independent_inverse(m):
    n = len(m)
    a = [[Q(x) for x in row]+[Q(i == j) for j in range(n)] for i, row in enumerate(m)]
    det = Q(1)
    for j in range(n):
        p = next((i for i in range(j, n) if a[i][j]), None)
        if p is None:
            return Q(0), None
        if p != j:
            a[p], a[j] = a[j], a[p]
            det = -det
        q = a[j][j]
        det *= q
        a[j] = [x/q for x in a[j]]
        for i in range(n):
            if i != j:
                q = a[i][j]
                a[i] = [x-q*y for x, y in zip(a[i], a[j])]
    return det, [row[n:] for row in a]


class Controls(unittest.TestCase):
    def test_tiny_update_complete_n4(self):
        for r in (1, 2, 3):
            histogram = {0: 0, 1: 0, 2: 0}
            for edges in candidates(4, r):
                matrix = dense(4, edges)
                det, inv = independent_inverse(matrix)
                self.assertEqual(det, determinant(edges))
                histogram[det] += 1
                circuit = inverse_circuit(4, edges)
                self.assertEqual(circuit is not None, det == 1)
                if circuit:
                    wires = identity(4)
                    for a, b, s in circuit['nodes']:
                        wires.append([x+s*y for x, y in zip(wires[a], wires[b])])
                    self.assertEqual([wires[i] for i in circuit['outputs']], inv)
            expected = counts(4)[r-1]
            self.assertEqual(histogram, {d: expected['det'+str(d)] for d in (0, 1, 2)})

    def test_ternary_and_two_order_controls(self):
        self.assertEqual(self_test()['status'], 'PASS')
        m = [[1, 1, -1], [1, -1, 1], [1, -1, 0]]
        a, b = {'destination': 0, 'donors': [(1, 1)]}, {'destination': 0, 'donors': [(2, 1)]}
        found = two_shear_endpoints(m, a, b)
        self.assertEqual(len(found), 2)
        self.assertTrue(all(not f['intermediate_ternary'] for f in found))
        for f in found:
            self.assertEqual(product(f['matrix'], f['inverse']), m)

    def test_signed_column_quotient(self):
        m = [[1, -1, 0], [2, 3, 0], [-1, 0, 0]]
        want = canonical_columns(m)['matrix']
        for p in itertools.permutations(range(3)):
            for s in itertools.product((-1, 1), repeat=3):
                altered = [[s[j]*row[p[j]] for j in range(3)] for row in m]
                self.assertEqual(canonical_columns(altered)['matrix'], want)

    def test_paired_isotropy(self):
        source = {'shape': [2, 2, 2], 'u': [], 'v': [], 'w': []}
        for i, j, k in itertools.product(range(2), repeat=3):
            for side, pos in [('u', i*2+j), ('v', j*2+k), ('w', k*2+i)]:
                source[side].append([int(c == pos) for c in range(4)])
        self.assertEqual(verify_standard_tensor(source), 64)
        for axis, i, s in itertools.product(range(3), range(2), (-1, 1)):
            result, _ = sandwich_shear(source, axis, i, 1-i, s)
            self.assertEqual(verify_standard_tensor(result), 64)
            recovered, _ = sandwich_shear(result, axis, i, 1-i, -s)
            self.assertEqual(recovered, source)

    def test_matching_against_bruteforce(self):
        rng = random.Random(8199)
        for _ in range(12):
            matrix = [[rng.choice((-2, -1, 0, 1, 2)) for j in range(4)] for i in range(3)]
            for pairs in (0, 1, 2):
                for ternary_only in (False, True):
                    before = sum(bool(x) for row in matrix for x in row)
                    scores = []
                    # Enumerating ordered directed edges is deliberately redundant.
                    directed = [(i, j, s) for i in range(4) for j in range(4) if i != j for s in (-1, 1)]
                    for chosen in itertools.combinations(directed, pairs):
                        flat = [i for edge in chosen for i in edge[:2]]
                        if len(set(flat)) != 2*pairs:
                            continue
                        inv = identity(4)
                        for i, j, s in chosen:
                            inv[i][j] = -s
                        out = product(matrix, inv)
                        if ternary_only and any(x not in (-1, 0, 1) for row in out for x in row):
                            continue
                        scores.append(before-sum(bool(x) for row in out for x in row))
                    got = optimal_disjoint_shears(matrix, pairs, ternary_only)
                    self.assertEqual(None if got is None else got['saving'], max(scores) if scores else None)

    def test_symmetry_full_replay(self):
        a = [[1, 1, 0], [0, 1, -1], [2, 0, 1], [0, 0, 0]]
        p, s, rp, rs = [2, 0, 1], [-1, 1, -1], [2, 0, 3, 1], [1, -1, 1, -1]
        b = [[rs[i]*s[j]*a[rp[i]][p[j]] for j in range(3)] for i in range(4)]
        result = find(a, b)
        self.assertEqual(result['status'], 'EQUIVALENT')
        self.assertEqual(transfer_matrix(a, result), b)
        b[0][0] += 100
        self.assertNotEqual(find(a, b)['status'], 'EQUIVALENT')


if __name__ == '__main__':
    unittest.main()
