import unittest
from select_removals_v2 import OptionalSurvivorSelector


class OptionalSelectorTests(unittest.TestCase):
    def setUp(self):
        self.c = dict(inputs=4, gates=[[0,1,1,1],[4,1,2,1],[1,1,2,1],[6,1,3,1]],
                      outputs=[[5,1],[7,1]])

    def test_output_only_proxy_can_abandon_a_surviving_hint(self):
        # Omit t1=x1+x2. A three-gate result recreates t1 and skips
        # surviving hint t0=x0+x1, despite t0 not being explicitly removed.
        s = OptionalSurvivorSelector(self.c)
        row = s.score([1])
        allowed = row['proxy_evaluations'][1]
        self.assertEqual(allowed['signed_normalized_gates'], 3)
        self.assertEqual(allowed['unused_surviving_hints_d'], 1)
        self.assertEqual(allowed['recreated_omitted_hints_b'], 1)
        self.assertEqual(allowed['novel_helper_forms_q'], 0)
        self.assertEqual(allowed['normalized_gain'], 1)

    def test_forbidden_and_allowed_are_distinct_not_assumed_equivalent(self):
        row = OptionalSurvivorSelector(self.c).score([1])
        self.assertGreater(row['proxy_evaluations'][0]['missing_original_output_forms'], 0)
        self.assertEqual(row['proxy_evaluations'][1]['missing_original_output_forms'], 0)

    def test_replay_every_chosen_pool_identity(self):
        s = OptionalSurvivorSelector(self.c)
        removed = {s.helpers[1]['form_id']}
        report, chosen, needed = s._output_closure(removed, True)
        for out, (a,sa,b,sb) in chosen.items():
            value = tuple(sa*x+sb*y for x,y in zip(s.forms[a],s.forms[b]))
            self.assertEqual(value, s.forms[out])
        self.assertTrue(all(o in chosen or o < s.n for o in s.targets))
        self.assertEqual(needed.bit_count(), report['signed_normalized_gates'])

    def test_larger_coefficient_forms_obey_cap(self):
        s = OptionalSurvivorSelector(self.c, max_abs=1)
        report, chosen, needed = s._output_closure({s.helpers[0]['form_id']}, True)
        self.assertFalse(set(chosen) & s.invalid)
        self.assertEqual(report['missing_original_output_forms'], 0)

    def test_export_replays_joint_reconnection(self):
        s = OptionalSurvivorSelector(self.c)
        c = s.export_proxy([1], allow_recreation=True)
        self.assertEqual(c['additions_signed'], 3)
        self.assertEqual(c['target_matrix'], [[1,1,1,0],[0,1,1,1]])


if __name__ == '__main__':
    unittest.main()
