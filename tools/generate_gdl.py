"""Generate a finite GDL-I description using only portable relational facts.

No dependency on the Python move generator or its arithmetic implementation.
"""
from pathlib import Path
import argparse

def generate(max_plies=300,score_target=0,horizon_rule='score',ops_mask=31,first_player=0):
    if type(max_plies) is not int or not 1 <= max_plies <= 10000:
        raise ValueError('max_plies must be 1..10000')
    for name,v,hi in (('score_target',score_target,45),('ops_mask',ops_mask,31),('first_player',first_player,1)):
        if type(v) is not int or not 0<=v<=hi: raise ValueError(name)
    if horizon_rule not in ('score','draw'): raise ValueError('horizon_rule')
    out=[f'; cotoan-v2-h{max_plies}-t{score_target}-{horizon_rule}-o{ops_mask}-f{first_player}; GDL-I',
         '(role red)','(role blue)','(opponent red blue)','(opponent blue red)',
         f'(init (control {("red","blue")[first_player]}))','(init (ply 0))']
    for i,op in enumerate(('add','sub','mul','div','mod')):
        if ops_mask & (1<<i): out.append(f'(enabled {op})')
    for q in range(99): out.append(f'(square s{q})')
    for v in range(1,10):
        out.extend([f'(init (cell s{v-1} red {v}))',f'(init (cell s{99-v} blue {v}))'])
        out.extend(f'(within {v} {d})' for d in range(1,v+1))
    out.extend(['(init (cell s13 red 0))','(init (cell s85 blue 0))'])
    for n in range(max_plies): out.append(f'(succ_ply {n} {n+1})')
    out.append(f'(limit {max_plies})')
    if horizon_rule=='score': out.append('score_horizon')
    for v in range(1,10):
        out.append(f'(next_value {v-1} {v})')
        for acc in range(46-v): out.append(f'(add_score {acc} {v} {acc+v})')
    for a in range(46):
        if score_target and a>=score_target: out.append(f'(winning_score {a})')
        for b in range(a): out.append(f'(greater_score {a} {b})')
    for s in range(99):
        for dx,dy in ((0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1)):
            path=[]
            for d in range(1,11):
                x,y=s%9+dx*d,s//9+dy*d
                if not(0<=x<9 and 0<=y<11): break
                t=9*y+x
                out.append(f'(ray s{s} {d} s{t})')
                if path:
                    out.append(f'(first s{s} s{t} s{path[0]})')
                    for m in path: out.append(f'(between s{s} s{t} s{m})')
                path.append(t)
    for a in range(1,10):
        for b in range(10):
            values=[('add',(a+b)%10+1),('mul',(a*b)%10+1)]
            if a>b: values.append(('sub',a-b+1))
            if a>b and b>0: values.extend([('div',a//b+1),('mod',a%b+1)])
            for op,d in values:
                if d>1: out.append(f'(arith {op} {a} {b} {d})')
    out.extend('''
(<= (occupied ?s) (true (cell ?s ?r ?v)))
(<= (blocked ?s ?t) (between ?s ?t ?m) (occupied ?m))
(<= (capblocked ?s ?t) (between ?s ?t ?m) (first ?s ?t ?u) (distinct ?m ?u) (occupied ?m))
(<= (candidate ?r (move ?s ?t)) (true (cell ?s ?r ?a)) (ray ?s ?d ?t) (within ?a ?d) (not (occupied ?t)) (not (blocked ?s ?t)))
(<= (candidate ?r (move ?s ?t)) (true (cell ?s ?r ?a)) (first ?s ?t ?u) (true (cell ?u ?r ?b)) (ray ?s ?d ?t) (arith ?op ?a ?b ?d) (enabled ?op) (opponent ?r ?o) (true (cell ?t ?o ?v)) (not (capblocked ?s ?t)))
(<= (canmove ?r) (candidate ?r ?m))
(<= (alive_value ?r ?v) (true (cell ?s ?r ?v)))
(<= (score_step ?r 0 0) (role ?r))
(<= (score_step ?r ?v ?acc) (score_step ?r ?prev ?acc) (next_value ?prev ?v) (opponent ?r ?o) (alive_value ?o ?v))
(<= (score_step ?r ?v ?sum) (score_step ?r ?prev ?acc) (next_value ?prev ?v) (opponent ?r ?o) (not (alive_value ?o ?v)) (add_score ?acc ?v ?sum))
(<= (score ?r ?sum) (score_step ?r 9 ?sum))
(<= (threshold_reached ?r) (score ?r ?sum) (winning_score ?sum))
(<= threshold_any (threshold_reached ?r))
(<= at_limit (true (ply ?n)) (limit ?n))
(<= (zeroalive ?r) (true (cell ?s ?r 0)))
(<= (winner ?r) (opponent ?r ?o) (zeroalive ?r) (not (zeroalive ?o)))
(<= (winner ?r) (opponent ?r ?o) (zeroalive ?r) (zeroalive ?o) (threshold_reached ?r))
(<= (winner ?r) (opponent ?r ?o) (zeroalive ?r) (zeroalive ?o) (not threshold_any) at_limit score_horizon (score ?r ?a) (score ?o ?b) (greater_score ?a ?b))
(<= (winner ?r) (opponent ?r ?o) (zeroalive ?r) (zeroalive ?o) (not threshold_any) (not at_limit) (true (control ?o)) (not (canmove ?o)))
(<= terminal (winner ?r))
(<= terminal at_limit)
(<= (legal ?r ?m) (true (control ?r)) (candidate ?r ?m) (not terminal))
(<= (legal ?r noop) (true (control ?o)) (opponent ?r ?o) (not terminal))
(<= (vacated ?s) (does ?r (move ?s ?t)))
(<= (landed ?t) (does ?r (move ?s ?t)))
(<= (next (cell ?t ?r ?v)) (does ?r (move ?s ?t)) (true (cell ?s ?r ?v)))
(<= (next (cell ?s ?r ?v)) (true (cell ?s ?r ?v)) (not (vacated ?s)) (not (landed ?s)))
(<= (next (control ?o)) (true (control ?r)) (opponent ?r ?o))
(<= (next (ply ?m)) (true (ply ?n)) (succ_ply ?n ?m))
(<= (goal ?r 100) (winner ?r))
(<= (goal ?r 0) (opponent ?r ?o) (winner ?o))
(<= (goal ?r 50) (role ?r) terminal (not (winner red)) (not (winner blue)))
'''.strip().splitlines())
    return '\n'.join(out)+'\n'

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--max-plies',type=int,default=300)
    ap.add_argument('--score-target',type=int,default=0)
    ap.add_argument('--horizon-rule',choices=('score','draw'),default='score')
    ap.add_argument('--ops-mask',type=int,default=31)
    ap.add_argument('--first-player',type=int,choices=(0,1),default=0)
    ap.add_argument('--output',default='gdl/cotoan.kif');args=ap.parse_args()
    Path(args.output).write_text(generate(args.max_plies,args.score_target,args.horizon_rule,
                                          args.ops_mask,args.first_player),encoding='utf-8')
