"""Executable rules for the cotoan-v2 configuration family."""
from dataclasses import dataclass, asdict
import json
import re

OPS = ('add', 'sub', 'mul', 'div', 'mod')
DIRS = ((0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1))

@dataclass(frozen=True)
class Config:
    max_plies: int = 300
    score_target: int = 0  # zero disables threshold victory
    horizon_rule: str = 'score'
    ops_mask: int = 31  # add, sub, mul, div, mod in bits 0..4
    first_player: int = 0

    def __post_init__(self):
        for name,lo,hi in (('max_plies',1,10000),('score_target',0,45),
                           ('ops_mask',0,31),('first_player',0,1)):
            v=getattr(self,name)
            if type(v) is not int or not lo<=v<=hi: raise ValueError(name)
        if self.horizon_rule not in ('score','draw'): raise ValueError('horizon_rule')

    @property
    def ops(self): return tuple(op for i,op in enumerate(OPS) if self.ops_mask & (1<<i))

    @property
    def identifier(self):
        return (f'cotoan-v2-h{self.max_plies}-t{self.score_target}-'
                f'{self.horizon_rule}-o{self.ops_mask}-f{self.first_player}')

    def to_dict(self): return asdict(self)

    @classmethod
    def from_dict(cls,data):
        if not isinstance(data,dict) or set(data)!=set(cls.__dataclass_fields__):
            raise ValueError('configuration keys')
        return cls(**data)

DEFAULT_CONFIG=Config()

def configuration(value=DEFAULT_CONFIG):
    """An integer is a v2 horizon shorthand, not the old v1 draw profile."""
    if type(value) is int: return Config(max_plies=value)
    if not isinstance(value,Config): raise ValueError('configuration')
    return value

def square(name):
    if not isinstance(name,str) or not re.fullmatch(r'[a-i](?:[1-9]|10|11)',name):
        raise ValueError('square must be a1..i11')
    return 9*(int(name[1:])-1)+ord(name[0])-97

def label(q):
    if type(q) is not int or not 0<=q<99: raise ValueError('square index')
    return chr(97+q%9)+str(q//9+1)

@dataclass(frozen=True)
class Position:
    board: tuple
    turn: int = 0
    ply: int = 0
    def __post_init__(self):
        if not isinstance(self.board,tuple) or len(self.board)!=99: raise ValueError('board length/type')
        if any(type(c) is not int or not -10<=c<=10 for c in self.board): raise ValueError('cell code')
        pieces=[c for c in self.board if c]
        if len(set(pieces))!=len(pieces): raise ValueError('duplicate piece identity')
        if 1 in pieces and self.board[13]!=1: raise ValueError('red zero anchor')
        if -1 in pieces and self.board[85]!=-1: raise ValueError('blue zero anchor')
        if 1 not in pieces and -1 not in pieces: raise ValueError('both zeros absent')
        if type(self.turn) is not int or self.turn not in (0,1): raise ValueError('turn')
        if type(self.ply) is not int or self.ply<0: raise ValueError('ply')

def initial(first_player=0):
    b=[0]*99
    for v in range(1,10): b[v-1],b[99-v]=v+1,-v-1
    b[13],b[85]=1,-1
    return Position(tuple(b),first_player)

def arithmetic(a,b,ops=OPS):
    result={}
    for op in ops:
        if op=='add': length=(a+b)%10+1
        elif op=='mul': length=(a*b)%10+1
        elif op=='sub' and a>b: length=a-b+1
        elif op=='div' and a>b>0: length=a//b+1
        elif op=='mod' and a>b>0: length=a%b+1
        else: continue
        if length>1: result.setdefault(length,[]).append(op)
    return result

def at(q,dx,dy,d):
    x,y=q%9+dx*d,q//9+dy*d
    return y*9+x if 0<=x<9 and 0<=y<11 else None

def moves(pos,ops=OPS):
    """Geometrical actions, independent of terminal adjudication.

    Maps action IDs to tuples of (support square, operation, distance).
    Quiet moves have an empty witness list. Duplicates are collapsed.
    """
    sign=1 if pos.turn==0 else -1
    found={}
    for src,code in enumerate(pos.board):
        if sign*code<=1: continue
        a=abs(code)-1
        for dx,dy in DIRS:
            for d in range(1,a+1):
                dst=at(src,dx,dy,d)
                if dst is None or pos.board[dst]: break
                found[99*src+dst]=[]
            support=at(src,dx,dy,1)
            if support is None or sign*pos.board[support]<=0: continue
            for d,operations in arithmetic(a,abs(pos.board[support])-1,ops).items():
                dst=at(src,dx,dy,d)
                if dst is None or sign*pos.board[dst]>=0: continue
                if any(pos.board[at(src,dx,dy,k)] for k in range(2,d)): continue
                found.setdefault(99*src+dst,[]).extend((support,op,d) for op in operations)
    return found

def scores(pos):
    """Captured-value totals (Red, Blue), derived from occupancy, not history."""
    red_material=sum(c-1 for c in pos.board if c>0)
    blue_material=sum(-c-1 for c in pos.board if c<0)
    return (45-blue_material,45-red_material)

def result(pos,max_plies=DEFAULT_CONFIG):
    cfg=configuration(max_plies)
    if pos.ply>cfg.max_plies: raise ValueError('ply exceeds horizon')
    if 1 not in pos.board: return (1,'zero_capture')
    if -1 not in pos.board: return (0,'zero_capture')
    points=scores(pos)
    if cfg.score_target:
        reached=[p for p in (0,1) if points[p]>=cfg.score_target]
        if len(reached)>1: raise ValueError('both scores meet target: inconsistent snapshot')
        if reached: return (reached[0],'score_target')
    if pos.ply==cfg.max_plies:
        if cfg.horizon_rule=='draw': return (None,'ply_limit_draw')
        winner=None if points[0]==points[1] else int(points[1]>points[0])
        return (winner,'ply_limit_score')
    if not moves(pos,cfg.ops): return (1-pos.turn,'no_legal_move')
    return None

def legal(pos,max_plies=DEFAULT_CONFIG):
    cfg=configuration(max_plies)
    if result(pos,cfg) is not None: return []
    return sorted(moves(pos,cfg.ops))

def apply(pos,action,max_plies=DEFAULT_CONFIG):
    if type(action) is not int or action not in legal(pos,max_plies): raise ValueError('illegal action')
    src,dst=divmod(action,99)
    b=list(pos.board);b[dst],b[src]=b[src],0
    return Position(tuple(b),1-pos.turn,pos.ply+1)

def encode(pos):
    return {'board':list(pos.board),'turn':pos.turn,'ply':pos.ply}

def decode(data):
    if not isinstance(data,dict) or set(data)!={'board','turn','ply'}: raise ValueError('position keys')
    if not isinstance(data['board'],list): raise ValueError('board type')
    return Position(tuple(data['board']),data['turn'],data['ply'])

def rotate_swap(pos):
    return Position(tuple(-c for c in pos.board[::-1]),1-pos.turn,pos.ply)

def perft(pos,depth,max_plies=DEFAULT_CONFIG):
    if type(depth) is not int or depth<0: raise ValueError('depth')
    if depth==0: return 1
    actions=legal(pos,max_plies)
    if depth==1: return len(actions)
    return sum(perft(apply(pos,a,max_plies),depth-1,max_plies) for a in actions)
