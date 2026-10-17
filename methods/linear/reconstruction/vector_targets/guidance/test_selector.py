#!/usr/bin/env python3
"""Small exact examples for removal indexing, closure and shared ancestors."""
import unittest
from select_removals import RemovalSelector, select_removals


def circuit(n, gates, outputs):
    return dict(inputs=n, gates=gates, outputs=outputs)


class SelectorTests(unittest.TestCase):
    def test_native_helper_filter_and_dense_indices(self):
        # t0=x0-x1, y=-t0+x2, t2=-t0 (alias), t3=2*x0,
        # t4=t0+x3. Native helper indices 0,1 refer to t0,t4.
        c = circuit(4, [[0, 1, 1, -1], [4, -1, 2, 1],
                        [1, 1, 0, -1], [0, 1, 0, 1], [4, 1, 3, 1]], [[5, 1]])
        s = RemovalSelector(c)
        self.assertEqual([h["native_helper_index"] for h in s.helpers], [0, 1])
        self.assertEqual([h["gate_index_0based"] for h in s.helpers], [0, 4])
        self.assertEqual(s.score([1])["removed_wire_ids"], [8])

    def test_required_output_is_not_silently_lost(self):
        # Omitting t0=x0+x1 leaves the original output y=t0+x2 required.
        c = circuit(3, [[0, 1, 1, 1], [3, 1, 2, 1]], [[4, 1]])
        score = RemovalSelector(c).score([0])
        self.assertEqual(score["missing_original_output_forms"], 1)
        self.assertEqual(score["missing_required_forms"], 1)
        self.assertIsNone(score["greedy_witness_gates"])

    def test_alternative_production_recovers_without_removed_helper(self):
        # t0=x0+x1; y0=t0+x2; t2=x1+x2; y1=t2+x3.
        # Replacing y0 by x0+t2 removes t0: four gates become three.
        c = circuit(4, [[0, 1, 1, 1], [4, 1, 2, 1],
                        [1, 1, 2, 1], [6, 1, 3, 1]], [[5, 1], [7, 1]])
        score = RemovalSelector(c).score([0])
        self.assertEqual(score["retained_auxiliary_targets"], 1)
        self.assertEqual(score["missing_required_forms"], 0)
        self.assertEqual(score["greedy_witness_gates"], 3)
        self.assertEqual(score["greedy_witness_gain_vs_distinct_targets"], 1)
        self.assertEqual(score["boundary_forms_without_direct_alternative"], 0)

    def test_shared_ancestor_is_counted_once(self):
        # y0=(x0+x1)+x2; y1=(x0+x1)+x3. Reconstructing them
        # jointly uses three gates, whereas independent chains sum to four.
        c = circuit(4, [[0, 1, 1, 1], [4, 1, 2, 1], [4, 1, 3, 1]], [[5, 1], [6, 1]])
        s = RemovalSelector(c)
        mandatory = set(s.wire_forms[4:])
        available, chosen, used, missing = s._closure(set(), mandatory)
        self.assertFalse(missing)
        self.assertEqual(used.bit_count(), 3)
        self.assertEqual(len(chosen), 3)

    def test_linked_removal_keeps_other_auxiliaries_as_targets(self):
        c = circuit(5, [[0, 1, 1, 1], [5, 1, 2, 1], [6, 1, 3, 1],
                        [7, 1, 4, 1]], [[8, 1]])
        s = RemovalSelector(c)
        score = s.score([0, 1])
        self.assertEqual(score["retained_auxiliary_targets"], 1)
        self.assertEqual(score["missing_required_forms"], 2)
        self.assertEqual(score["missing_original_output_forms"], 1)
        self.assertEqual(score["boundary_retained_forms"], 1)

    def test_exact_pool_identities_reject_corruption(self):
        c = circuit(3, [[0, 1, 1, 1], [3, 1, 2, 1]], [[4, 1]])
        pool = dict(inputs=3, forms=[[1,0,0],[0,1,0],[0,0,1],[1,1,0]],
                    productions={"3": [[0,1,2,1]]})
        with self.assertRaisesRegex(ValueError, "False pool identity"):
            RemovalSelector(c, pool)

    def test_random_controls_are_reproducible_and_match_k(self):
        c = circuit(5, [[0, 1, 1, 1], [5, 1, 2, 1], [6, 1, 3, 1],
                        [7, 1, 4, 1]], [[8, 1]])
        a = select_removals(c, [1, 2, 3], seed=401, per_k=2)
        b = select_removals(c, [1, 2, 3], seed=401, per_k=2)
        self.assertEqual(a, b)
        self.assertEqual([r["k"] for r in a["guided"]], [r["k"] for r in a["random_controls"]])
        for row in a["guided"] + a["random_controls"]:
            self.assertEqual(len(row["removed_native_helper_indices"]), row["k"])


if __name__ == "__main__":
    unittest.main()
