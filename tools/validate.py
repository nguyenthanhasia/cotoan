"""Public validation; every sampled position and result can be regenerated.

Run from the repository root: python -m tools.validate
"""
import json,random,platform,unittest
from pathlib import Path
from cotoan import rules as r
from tests.test_rules import setup
from tools.generate_gdl import generate
from tools.gdl_check import asp,evaluate,legal_actions,state_terms

def direct_actions(p):
    """Independent exhaustive source/destination predicate, not ray generation."""
    out=[];sgn=1 if p.turn==0 else -1
    for s,c in enumerate(p.board):
        if sgn*c<=1: continue
        a=abs(c)-1
        for t,tc in enumerate(p.board):
            dx,dy=t%9-s%9,t//9-s//9
            L=max(abs(dx),abs(dy))
            if L==0 or (dx and dy and abs(dx)!=abs(dy)): continue
            ux=(dx>0)-(dx<0);uy=(dy>0)-(dy<0)
            line=[s+k*(ux+9*uy) for k in range(1,L)]
            if tc==0:
                okay=L<=a and all(p.board[q]==0 for q in line)
            elif sgn*tc<0 and L>1 and sgn*p.board[line[0]]>0:
                b=abs(p.board[line[0]])-1
                distances={(a+b)%10+1,(a*b)%10+1}
                if a>b: distances.add(a-b+1)
                if a>b>0: distances.update({a//b+1,a%b+1})
                okay=L in distances and all(p.board[q]==0 for q in line[1:])
            else: okay=False
            if okay: out.append(99*s+t)
    return sorted(out)

def synthetic(rng):
    b=[0]*99;b[13]=1;b[85]=-1
    cells=[q for q in range(99) if q not in (13,85)];rng.shuffle(cells)
    for c in list(range(2,11))+list(range(-10,-1)):
        if rng.random()<0.72: b[cells.pop()]=c
    return r.Position(tuple(b),rng.randrange(2),rng.randrange(12))

def compare_gdl(program,p,horizon,action=None):
    symbols=evaluate(program,p,action)
    assert legal_actions(symbols,p.turn)==r.legal(p,horizon)
    terminal=any(s.name=='terminal' for s in symbols)
    outcome=r.result(p,horizon)
    assert terminal==(outcome is not None)
    goals={s.arguments[0].name:s.arguments[1].number for s in symbols if s.name=='goal'}
    points={s.arguments[0].name:s.arguments[1].number for s in symbols if s.name=='score'}
    assert points==dict(zip(('red','blue'),r.scores(p)))
    if terminal:
        expected={'red':50,'blue':50} if outcome[0] is None else dict(zip(('red','blue'),(100,0) if outcome[0]==0 else (0,100)))
        assert goals==expected
    else:
        assert goals=={}
        other=('blue','red')[p.turn]
        assert any(str(s)==f'legal({other},noop)' for s in symbols)
    if action is not None:
        successor=r.apply(p,action,horizon)
        assert {str(s.arguments[0]) for s in symbols if s.name=='next'}==state_terms(successor)

def main():
    import pyspiel,clingo,numpy as np
    import cotoan.spiel
    from open_spiel.python.algorithms import mcts
    suite=unittest.defaultTestLoader.discover('tests')
    tested=unittest.TextTestRunner(verbosity=1).run(suite)
    assert tested.wasSuccessful()
    rng=random.Random(20260901);positions=[];transitions=0
    for _ in range(10):
        p=r.initial()
        for _ in range(30):
            positions.append(p);aa=r.legal(p)
            if not aa: break
            p=r.apply(p,rng.choice(aa));transitions+=1
    positions += [synthetic(rng) for _ in range(300)]
    actions_compared=0
    for p in positions:
        aa=direct_actions(p);assert aa==sorted(r.moves(p));actions_compared+=len(aa)
        rotated=r.rotate_swap(p)
        assert sorted(99*(98-a//99)+(98-a%99) for a in aa)==sorted(r.moves(rotated))
        assert r.decode(r.encode(p))==p
    program=asp(generate(12))
    assert Path('gdl/cotoan.kif').read_text()==generate(300)
    compare_gdl(asp(generate(300)),r.initial(),300,9)
    # Check generated initial facts without supplying the Python initial state.
    initial_terms={str(s.arguments[0]) for s in evaluate(program) if s.name=='init'}
    assert initial_terms==state_terms(r.initial())
    selected=[p for p in positions[:50] if p.ply<12]+positions[-40:]
    selected += [setup({}),setup({'e10':0},ply=12),setup({},ply=12),r.Position(r.initial().board,0,12),
                 setup({'e7':3,'e8':2,'i11':-3}),setup({'d2':3,'g2':-4})]
    gdl_transitions=0;fixtures=[]
    for i,p in enumerate(selected):
        aa=r.legal(p,12);a=rng.choice(aa) if aa else None
        compare_gdl(program,p,12,a)
        gdl_transitions+=a is not None
        fixtures.append({'id':i,'position':r.encode(p),'legal_actions':aa,'selected_action':a,
                         'result':r.result(p,12)})
    # All 90 arithmetic value pairs, including unreachable equal identities,
    # are compared as static facts, not represented as illegal board states.
    symbols=evaluate(program)
    for a in range(1,10):
        for b in range(10):
            actual={(s.arguments[0].name,s.arguments[3].number) for s in symbols
                    if s.name=='arith' and s.arguments[1].number==a and s.arguments[2].number==b}
            expected={(op,d) for d,ops in r.arithmetic(a,b).items() for op in ops}
            assert actual==expected
    game=pyspiel.load_game('python_cotoan(max_plies=12)')
    pyspiel.random_sim_test(game,20,True,False)
    s=game.new_initial_state()
    for _ in range(12):
        if s.is_terminal(): break
        assert sum(s.legal_actions_mask())==len(s.legal_actions())
        text=pyspiel.serialize_game_and_state(game,s)
        _,restored=pyspiel.deserialize_game_and_state(text)
        assert restored.serialize()==s.serialize() and restored.history()==s.history()
        assert restored.observation_tensor()==s.observation_tensor()
        s.apply_action(rng.choice(s.legal_actions()))
    evaluator=mcts.RandomRolloutEvaluator(n_rollouts=1,random_state=np.random.RandomState(7))
    bot=mcts.MCTSBot(game,1.4,8,evaluator,solve=False,random_state=np.random.RandomState(7))
    mcts_action=bot.step(game.new_initial_state());assert mcts_action in game.new_initial_state().legal_actions()
    summary={'profile':r.DEFAULT_CONFIG.identifier,'seed':20260901,'python':platform.python_version(),
             'open_spiel':pyspiel.__version__,'clingo':clingo.__version__,'unit_tests':tested.testsRun,
             'predicate_positions':len(positions),'predicate_legal_actions':actions_compared,
             'sampled_transitions':transitions,'rotation_positions':len(positions),
             'gdl_positions':len(selected),'gdl_transitions':gdl_transitions,'gdl_arithmetic_pairs':90,
             'committed_gdl_and_default_horizon_check':True,
             'openspiel_random_simulations':20,'openspiel_test_horizon':12,'mcts_smoke_simulations':8,
             'perft':{'1':r.perft(r.initial(),1),'2':r.perft(r.initial(),2)},
             'status':'passed','scope':'conformance tests, not agent-strength experiments'}
    Path('results/validation.json').write_text(json.dumps(summary,indent=2)+'\n')
    Path('examples/conformance.json').write_text(json.dumps({'config':r.Config(max_plies=12).to_dict(),
                                                           'max_plies':12,'cases':fixtures},indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
