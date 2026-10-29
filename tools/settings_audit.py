"""Public configuration-contract tests across Python, emitted GDL and OpenSpiel.

No private implementation is loaded. All samples and expectations are public.
"""
import json
import random
from pathlib import Path
from dataclasses import replace
import pyspiel
import cotoan.spiel
from cotoan import rules as r
from tests.test_rules import setup,action
from tests.test_settings import missing_blue_nine
from tools.generate_gdl import generate
from tools.gdl_check import asp,evaluate,legal_actions,state_terms

def state_for(game,p):
    s=game.new_initial_state();s.position=p
    return game.deserialize_state(s.serialize())

def fixture_positions(cfg):
    initial=r.initial(cfg.first_player)
    points=missing_blue_nine()
    # Full-material arithmetic capture; a later variant starts with Red at 8.
    cells=list(r.initial().board)
    for src,dst in (('a1','d4'),('b1','c4'),('f11','f4')):
        cells[r.square(dst)]=cells[r.square(src)];cells[r.square(src)]=0
    capture=r.Position(tuple(cells))
    cells[r.square('b11')]=0
    near_target=r.Position(tuple(cells))
    out=[initial,replace(initial,ply=cfg.max_plies),points,r.rotate_swap(points),
         replace(points,ply=cfg.max_plies),replace(r.rotate_swap(points),ply=cfg.max_plies),
         capture,near_target,replace(near_target,ply=cfg.max_plies-1),
         setup({}),setup({},ply=cfg.max_plies),setup({'e2':0},ply=cfg.max_plies)]
    rng=random.Random(20260902)
    p=initial
    for _ in range(cfg.max_plies):
        out.append(p)
        aa=r.legal(p,cfg)
        if not aa: break
        p=r.apply(p,rng.choice(aa),cfg)
    return out

def main():
    base=r.Config(max_plies=12)
    configs=[base,replace(base,horizon_rule='draw'),replace(base,score_target=9),
             replace(base,score_target=21),replace(base,score_target=9,horizon_rule='draw'),
             replace(base,ops_mask=0),replace(base,ops_mask=8),replace(base,ops_mask=16),
             replace(base,first_player=1)]
    rows=[];comparisons=0;transitions=0;rejected=0
    for cfg in configs:
        program=asp(generate(**cfg.to_dict()))
        game=pyspiel.load_game('python_cotoan',cfg.to_dict())
        for i,p in enumerate(fixture_positions(cfg)):
            try: expected=r.result(p,cfg)
            except ValueError:
                assert cfg.score_target and all(v>=cfg.score_target for v in r.scores(p))
                rejected+=1;continue
            s=state_for(game,p)
            symbols=evaluate(program,p)
            aa=r.legal(p,cfg)
            assert legal_actions(symbols,p.turn)==aa==s.legal_actions()
            assert any(x.name=='terminal' for x in symbols)==s.is_terminal()==(expected is not None)
            points={x.arguments[0].name:x.arguments[1].number for x in symbols if x.name=='score'}
            assert points==dict(zip(('red','blue'),r.scores(p)))
            goals={x.arguments[0].name:x.arguments[1].number for x in symbols if x.name=='goal'}
            returns=[0.,0.] if expected is None or expected[0] is None else ([1.,-1.] if expected[0]==0 else [-1.,1.])
            assert s.returns()==returns
            assert goals==({} if expected is None else dict(zip(('red','blue'),[(v+1)*50 for v in returns])))
            assert len(s.observation_tensor(0))==2183
            assert s.observation_tensor(0)[-5:]==[cfg.max_plies,cfg.score_target,int(cfg.horizon_rule=='score'),cfg.ops_mask,cfg.first_player]
            selected=action('c4','f4') if action('c4','f4') in aa else (aa[0] if aa else None)
            if selected is not None:
                root=s.serialize();clone=s.clone()
                assert clone.serialize()==root and clone.legal_actions()==aa
                child=s.child(selected);clone.apply_action(selected)
                q=r.apply(p,selected,cfg)
                assert child.position==clone.position==q and s.serialize()==root
                successor=evaluate(program,p,selected)
                assert {str(x.arguments[0]) for x in successor if x.name=='next'}==state_terms(q)
                transitions+=1
            rows.append({'config':cfg.identifier,'case':i,'position':r.encode(p),
                         'scores':r.scores(p),'result':expected,'selected_action':selected})
            comparisons+=1
        pyspiel.random_sim_test(game,5,True,False)
    # All operation masks, on one public two-witness capture fixture.
    p=setup({'c4':9,'d4':4,'f4':-5,'i11':-10})
    for mask in range(32):
        cfg=replace(base,ops_mask=mask)
        assert legal_actions(evaluate(asp(generate(**cfg.to_dict())),p),p.turn)==r.legal(p,cfg)
    # Score fold checked against all 512 subsets of Blue's nonzero material.
    program=asp(generate(**base.to_dict()))
    for mask in range(512):
        cells=list(r.initial().board);expected=0
        for v in range(1,10):
            if mask & (1<<(v-1)): cells[99-v]=0;expected+=v
        symbols=evaluate(program,r.Position(tuple(cells)))
        points={x.arguments[0].name:x.arguments[1].number for x in symbols if x.name=='score'}
        assert points=={'red':expected,'blue':0}
    # Same board, turn and ply; different settings imply different outcomes.
    p=missing_blue_nine(12)
    a=state_for(pyspiel.load_game('python_cotoan',base.to_dict()),p)
    b=state_for(pyspiel.load_game('python_cotoan',replace(base,horizon_rule='draw').to_dict()),p)
    assert a.observation_tensor(0)[:-5]==b.observation_tensor(0)[:-5]
    assert a.observation_tensor(0)!=b.observation_tensor(0) and a.returns()==[1.,-1.] and b.returns()==[0.,0.]
    try: b.get_game().deserialize_state(a.serialize())
    except ValueError: pass
    else: raise AssertionError('cross-configuration payload accepted')
    game=pyspiel.load_game('python_cotoan',base.to_dict());s=game.new_initial_state()
    s.apply_action(s.legal_actions()[0])
    _,restored=pyspiel.deserialize_game_and_state(pyspiel.serialize_game_and_state(game,s))
    assert restored.serialize()==s.serialize() and restored.history()==s.history()
    result={'status':'passed','seed':20260902,'configurations':len(configs),
            'state_comparisons':comparisons,'selected_successor_comparisons':transitions,
            'rejected_dual_threshold_snapshots':rejected,'operation_masks':32,
            'gdl_material_subsets':512,'openspiel_random_simulations':5*len(configs),
            'observation_size':2183,'config_aliasing':{'same_board_turn_ply':True,'red_score':9,'blue_score':0,
            'score_horizon_returns':[1,-1],'draw_horizon_returns':[0,0],'different_observations':True},
            'scope':'Cross-configuration conformance diagnostics, not playing strength'}
    Path('results/settings-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    Path('examples/settings-conformance.json').write_text(json.dumps({'configs':[c.to_dict() for c in configs],'cases':rows},indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
