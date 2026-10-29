import unittest
from dataclasses import replace
from cotoan import rules as r
from tests.test_rules import setup,action

def missing_blue_nine(ply=0):
    b=list(r.initial().board);b[r.square('a11')]=0
    return r.Position(tuple(b),0,ply)

class SettingsTests(unittest.TestCase):
    def test_initial_scores(self): self.assertEqual(r.scores(r.initial()),(0,0))

    def test_score_uses_captured_not_own_remaining_value(self):
        self.assertEqual(r.scores(missing_blue_nine()),(9,0))

    def test_all_512_material_subsets(self):
        for mask in range(512):
            b=list(r.initial().board);expected=0
            for v in range(1,10):
                if mask & (1<<(v-1)): b[99-v]=0;expected+=v
            self.assertEqual(r.scores(r.Position(tuple(b))),(expected,0))

    def test_score_after_capture(self):
        p=setup({'c4':3,'d4':2,'f4':-5,'i11':-2})
        q=r.apply(p,action('c4','f4'))
        self.assertEqual(r.scores(q),(r.scores(p)[0]+4,r.scores(p)[1]))

    def test_quiet_move_score_unchanged(self):
        p=r.initial();self.assertEqual(r.scores(p),r.scores(r.apply(p,action('a1','a2'))))

    def test_threshold_exact(self):
        self.assertEqual(r.result(missing_blue_nine(),r.Config(score_target=9)),(0,'score_target'))

    def test_threshold_below_target_continues(self):
        self.assertIsNone(r.result(missing_blue_nine(),r.Config(score_target=10)))

    def test_threshold_overshoot(self):
        self.assertEqual(r.result(missing_blue_nine(),r.Config(score_target=8)),(0,'score_target'))

    def test_threshold_disabled(self): self.assertIsNone(r.result(missing_blue_nine()))

    def test_horizon_higher_score_wins(self):
        self.assertEqual(r.result(missing_blue_nine(300)),(0,'ply_limit_score'))

    def test_horizon_draw_setting(self):
        self.assertEqual(r.result(missing_blue_nine(300),r.Config(horizon_rule='draw')),(None,'ply_limit_draw'))

    def test_zero_capture_overrides_score_deficit(self):
        b=list(missing_blue_nine(300).board);b[13]=0
        self.assertEqual(r.result(r.Position(tuple(b),0,300),r.Config(score_target=9)),(1,'zero_capture'))

    def test_threshold_overrides_horizon(self):
        cfg=r.Config(score_target=9,horizon_rule='draw')
        self.assertEqual(r.result(missing_blue_nine(300),cfg),(0,'score_target'))

    def test_terminal_has_no_actions(self):
        self.assertEqual(r.legal(missing_blue_nine(),r.Config(score_target=9)),[])

    def test_inconsistent_dual_threshold_rejected(self):
        with self.assertRaises(ValueError): r.result(setup({}),r.Config(score_target=10))

    def test_configuration_roundtrip_and_identity(self):
        cfg=r.Config(score_target=21,ops_mask=5,first_player=1)
        self.assertEqual(r.Config.from_dict(cfg.to_dict()),cfg)
        self.assertNotEqual(cfg.identifier,replace(cfg,horizon_rule='draw').identifier)

    def test_invalid_configurations(self):
        for kwargs in ({'score_target':46},{'score_target':-1},{'score_target':True},
                       {'ops_mask':32},{'first_player':2},{'max_plies':0},{'horizon_rule':'unknown'}):
            with self.assertRaises(ValueError): r.Config(**kwargs)

    def test_disabled_operations(self):
        p=setup({'c4':9,'d4':4,'f4':-5,'i11':-10})
        a=action('c4','f4')
        self.assertIn(a,r.legal(p))
        self.assertNotIn(a,r.legal(p,r.Config(ops_mask=0)))
        self.assertIn(a,r.legal(p,r.Config(ops_mask=1<<3)))

    def test_first_player(self): self.assertEqual(r.initial(1).turn,1)

    def test_score_rotation(self):
        p=missing_blue_nine(300);q=r.rotate_swap(p)
        self.assertEqual(r.scores(q),r.scores(p)[::-1])
        self.assertEqual(r.result(q),(1,'ply_limit_score'))

    def test_horizon_bound(self):
        with self.assertRaises(ValueError): r.result(missing_blue_nine(301))

if __name__=='__main__': unittest.main()
