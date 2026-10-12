#!/usr/bin/env python3
import copy
import unittest

import target_walk as m


def graph(inputs, forms, productions, outputs):
    weights = {key:[1. for _ in rows] for key,rows in productions.items()}
    return dict(inputs=inputs, forms=forms, productions=productions,
                outputs=outputs,
                target_matrix=[[sign*x for x in forms[index]] for index,sign in outputs],
                production_weights=dict(weighted=copy.deepcopy(weights),uniform=copy.deepcopy(weights)))


class TargetWalkTest(unittest.TestCase):
    def test_shared_ancestor_paid_once(self):
        data = graph(4, [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1],
                         [1,1,0,0],[1,1,1,0],[1,1,0,1]],
                     {'4':[[0,1,1,1]],'5':[[4,1,2,1]],'6':[[4,1,3,1]]},
                     [[5,1],[6,1],[5,-1]])
        _,_,prods,_ = m.validate_graph(data)
        for seed in range(10):
            program, stats = m.draw_program(data,prods,'weighted',seed)
            self.assertEqual(len(program['gates']),3)
            self.assertEqual(stats['failed_targets'],[])
            m.audit.replay(program,data['target_matrix'])

    def test_cycle_rollback_then_valid_alternative(self):
        data = graph(3, [[1,0,0],[0,1,0],[0,0,1],[1,1,0],[1,0,1],[0,1,-1]],
                     {'3':[[4,1,5,1],[0,1,1,1]],'4':[[0,1,2,1]],'5':[[3,1,4,-1]]},
                     [[3,1]])
        _,_,prods,_ = m.validate_graph(data)
        program, stats = m.draw_program(data,prods,'weighted',1)
        self.assertEqual(len(program['gates']),1)
        self.assertGreater(stats['cycle_rejections'],0)
        self.assertGreater(stats['rolled_back_gates'],0)
        m.audit.replay(program,data['target_matrix'])

    def test_step_limit_censors_walk(self):
        data = graph(3, [[1,0,0],[0,1,0],[0,0,1],[1,1,0],[1,0,1],[0,1,-1]],
                     {'3':[[4,1,5,1],[0,1,1,1]],'4':[[0,1,2,1]],'5':[[3,1,4,-1]]},
                     [[3,1]])
        _,_,prods,_ = m.validate_graph(data)
        program, stats = m.draw_program(data,prods,'weighted',1,max_steps=1)
        self.assertIsNone(program)
        self.assertEqual(stats['failed_targets'],[0])

    def test_missing_identity_and_nonunit_rejected(self):
        data = graph(2,[[1,0],[0,1],[1,1]],{'2':[[0,1,1,1]]},[[2,1]])
        broken = copy.deepcopy(data)
        broken['productions']['2'][0][1] = 2
        with self.assertRaises(ValueError):
            m.validate_graph(broken)
        broken = copy.deepcopy(data)
        broken['forms'][2] = [1,-1]
        with self.assertRaises(ValueError):
            m.validate_graph(broken)


if __name__ == '__main__':
    unittest.main()
