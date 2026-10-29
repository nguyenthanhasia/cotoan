import unittest
from cotoan import rules as r

def setup(pieces,turn=0,ply=0):
    b=[0]*99;b[13]=1;b[85]=-1
    for q,code in pieces.items(): b[r.square(q) if isinstance(q,str) else q]=code
    return r.Position(tuple(b),turn,ply)

def action(a,b): return 99*r.square(a)+r.square(b)

class RuleTests(unittest.TestCase):
    def test_initial(self):
        p=r.initial();self.assertEqual(sum(c!=0 for c in p.board),20)
        self.assertEqual(r.perft(p,1),87);self.assertEqual(r.perft(p,2),7457)
    def test_square_roundtrip(self):
        for q in range(99): self.assertEqual(r.square(r.label(q)),q)
    def test_square_invalid(self):
        for q in ('a0','a12','j1','A1','a01','e2x',''):
            with self.assertRaises(ValueError): r.square(q)
    def test_quiet_distance(self):
        p=setup({'c4':3,'i11':-3})
        self.assertIn(action('c4','e6'),r.legal(p));self.assertNotIn(action('c4','f7'),r.legal(p))
    def test_quiet_block(self):
        p=setup({'c4':5,'d4':-3,'i11':-2})
        self.assertNotIn(action('c4','d4'),r.legal(p));self.assertNotIn(action('c4','e4'),r.legal(p))
    def test_zero_immobile(self):
        self.assertFalse(any(a//99==13 for a in r.moves(setup({'i11':-2}))))
    def test_zero_support(self):
        p=setup({'d2':3,'g2':-4})
        self.assertIn(action('d2','g2'),r.legal(p))
    def test_zero_capture(self):
        p=setup({'e7':3,'e8':2,'i11':-3})
        q=r.apply(p,action('e7','e10'))
        self.assertEqual(r.result(q),(0,'zero_capture'));self.assertEqual(q.board[r.square('e8')],2)
    def test_capture_support_persists(self):
        p=setup({'c4':3,'d4':2,'f4':-5,'i11':-2})
        q=r.apply(p,action('c4','f4'));self.assertEqual(q.board[r.square('d4')],2)
        self.assertEqual(q.board[r.square('f4')],3);self.assertEqual(q.board[r.square('c4')],0)
    def test_capture_block(self):
        p=setup({'c4':3,'d4':2,'e4':-6,'f4':-5})
        self.assertNotIn(action('c4','f4'),r.legal(p))
    def test_guard_and_modulo(self):
        self.assertEqual(r.arithmetic(9,9),{9:['add'],2:['mul']})
        self.assertEqual(r.arithmetic(8,3)[3],['div','mod'])
        self.assertNotIn('div',sum(r.arithmetic(2,0).values(),[]))
    def test_no_move_loss(self): self.assertEqual(r.result(setup({})),(1,'no_legal_move'))
    def test_horizon_draw(self): self.assertEqual(r.result(r.initial(),1),None)
    def test_horizon_reached(self):
        p=r.Position(r.initial().board,0,4);self.assertEqual(r.result(p,4),(None,'ply_limit_score'))
    def test_terminal_priority(self):
        p=setup({'e10':0},ply=4);self.assertEqual(r.result(p,4),(0,'zero_capture'))
        self.assertEqual(r.result(setup({},ply=4),4),(None,'ply_limit_score'))
    def test_json_roundtrip(self): self.assertEqual(r.decode(r.encode(r.initial())),r.initial())
    def test_invalid_identity(self):
        with self.assertRaises(ValueError): setup({'c4':2,'d4':2})
    def test_invalid_zero(self):
        with self.assertRaises(ValueError): setup({'e2':0,'d2':1})
    def test_invalid_action(self):
        for a in (-1,9801,True,9.0):
            with self.assertRaises(ValueError): r.apply(r.initial(),a)
    def test_rotation(self): self.assertEqual(r.rotate_swap(r.rotate_swap(r.initial())),r.initial())

if __name__=='__main__': unittest.main()
