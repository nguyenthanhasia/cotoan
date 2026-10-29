"""Deterministic diagnostics of action duplication and horizon aliasing.

Uses public fixtures and an explicit legal cycle. These are representation
diagnostics, not agent-strength or runtime-performance experiments.
Run from the repository root: python -m tools.representation_audit
"""
from fractions import Fraction
from pathlib import Path
import json
from cotoan import rules as r

def move(src,dst):
    return 99*r.square(src)+r.square(dst)

def multiplicity(position,horizon):
    actions=r.legal(position,horizon)
    witnesses=r.moves(position)
    counts={action:max(1,len(witnesses[action])) for action in actions}
    total=sum(counts.values())
    tv=sum((abs(Fraction(k,total)-Fraction(1,len(actions))) for k in counts.values()),Fraction(0))/2 if actions else Fraction(0)
    return counts,total,tv

def main():
    fixtures=json.loads(Path('examples/conformance.json').read_text())
    horizon=fixtures['max_plies']; rows=[]
    for case in fixtures['cases']:
        p=r.decode(case['position'])
        if r.result(p,horizon) is not None: continue
        counts,total,tv=multiplicity(p,horizon)
        rows.append({'case_id':case['id'],'endpoint_actions':len(counts),'witness_actions':total,
                     'duplicated_endpoint_actions':sum(k>1 for k in counts.values()),
                     'total_variation_exact':str(tv),'total_variation':float(tv)})
    # Figure 3D: an isolated demonstration with a surviving remote Blue 9.
    b=[0]*99;b[13]=1;b[85]=-1;b[98]=-10
    b[r.square('c4')]=9;b[r.square('d4')]=4;b[r.square('f4')]=-5
    example=r.Position(tuple(b))
    counts,total,tv=multiplicity(example,300)
    selected=move('c4','f4')
    assert counts[selected]==2
    assert {op for _,op,_ in r.moves(example)[selected]}=={'div','mod'}
    probability={'endpoint_uniform':str(Fraction(1,len(counts))),
                 'witness_uniform':str(Fraction(counts[selected],total)),
                 'endpoint_actions':len(counts),'witness_actions':total}
    assert Fraction(probability['endpoint_uniform'])!=Fraction(probability['witness_uniform'])
    # One four-ply cycle returns to the initial board and Red to move.
    cycle=[move('a1','a2'),move('i11','i10'),move('a2','a1'),move('i10','i11')]
    current=r.initial(); states={0:current}
    for ply in range(1,301):
        current=r.apply(current,cycle[(ply-1)%4],300)
        if ply in (3,4,299,300): states[ply]=current
    assert states[4].board==states[0].board and states[4].turn==states[0].turn
    assert states[3].board==states[299].board and states[3].turn==states[299].turn
    assert r.result(states[3],300) is None and r.result(states[299],300) is None
    assert r.legal(states[3],300)==r.legal(states[299],300)
    early=r.apply(states[3],cycle[3],300);late=r.apply(states[299],cycle[3],300)
    assert early.board==late.board and early.turn==late.turn
    assert r.result(early,300) is None and r.result(late,300)==(None,'ply_limit_score')
    result={'status':'passed','scope':'representation diagnostics, not playing strength',
            'profile':r.DEFAULT_CONFIG.identifier,
            'fixture_horizon':horizon,'nonterminal_fixture_positions':len(rows),
            'positions_with_duplicate_witnesses':sum(row['duplicated_endpoint_actions']>0 for row in rows),
            'endpoint_action_total':sum(row['endpoint_actions'] for row in rows),
            'witness_action_total':sum(row['witness_actions'] for row in rows),
            'duplicated_endpoint_action_total':sum(row['duplicated_endpoint_actions'] for row in rows),
            'max_total_variation':max(row['total_variation'] for row in rows),
            'figure_3d_probabilities':probability,
            'reachable_aliasing':{'cycle':['a1-a2','i11-i10','a2-a1','i10-i11'],
                                 'compared_plies':[3,299],'same_board_and_turn':True,
                                 'both_nonterminal':True,'same_legal_actions':True,
                                 'common_next_action':'i10-i11','successor_plies':[4,300],
                                 'early_successor_terminal':False,'late_successor_terminal':True,
                                 'late_successor_result':'equal-score draw at ply limit'},
            'per_fixture':rows}
    Path('results/representation-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='per_fixture'},indent=2))

if __name__=='__main__': main()
