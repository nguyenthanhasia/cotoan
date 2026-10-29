"""Evaluate the emitted stratified GDL subset through clingo.

This independent relational execution path is NOT a universal GDL interpreter
or certification by an external GGP competition engine.
"""
import re
import clingo

def parse(text):
    tokens=re.findall(r'\(|\)|[^\s()]+',re.sub(r';[^\n]*','',text))
    stack=[[]]
    for token in tokens:
        if token=='(': stack.append([])
        elif token==')':
            if len(stack)==1: raise ValueError('unmatched closing parenthesis')
            stack[-2].append(stack.pop())
        else: stack[-1].append(token)
    if len(stack)!=1: raise ValueError('unmatched opening parenthesis')
    return stack[0]

def atom(x):
    if isinstance(x,str):
        if x.startswith('?'): return 'V_'+x[1:]
        if not re.fullmatch('[a-z][a-z0-9_]*|[0-9]+',x): raise ValueError(x)
        return x
    if not x: raise ValueError('empty expression')
    return atom(x[0])+'('+','.join(map(atom,x[1:]))+')'

def asp(text):
    result=[]
    for form in parse(text):
        if isinstance(form,list) and form[0]=='<=':
            body=[]
            for item in form[2:]:
                if isinstance(item,list) and item[0]=='not': body.append('not '+atom(item[1]))
                elif isinstance(item,list) and item[0]=='distinct': body.append(atom(item[1])+'!='+atom(item[2]))
                else: body.append(atom(item))
            result.append(atom(form[1])+' :- '+', '.join(body)+'.')
        else: result.append(atom(form)+'.')
    return '\n'.join(result)

def facts(position):
    out=[f'true(control({("red","blue")[position.turn]})).',f'true(ply({position.ply})).']
    for s,c in enumerate(position.board):
        if c: out.append(f'true(cell(s{s},{"red" if c>0 else "blue"},{abs(c)-1})).')
    return '\n'.join(out)

def evaluate(program,position=None,action=None):
    ctl=clingo.Control(['--warn=none','--models=2'])
    extra=facts(position) if position is not None else ''
    if action is not None:
        src,dst=divmod(action,99);r=('red','blue')[position.turn];o=('blue','red')[position.turn]
        extra+=f'\ndoes({r},move(s{src},s{dst})).\ndoes({o},noop).'
    ctl.add('base',[],program+'\n'+extra);ctl.ground([('base',[])])
    models=[]
    with ctl.solve(yield_=True) as handle:
        for model in handle: models.append(set(model.symbols(atoms=True)))
    if len(models)!=1: raise AssertionError('expected one stratified model')
    return models[0]

def legal_actions(symbols,turn):
    role=('red','blue')[turn]
    return sorted(99*int(s.arguments[1].arguments[0].name[1:])+int(s.arguments[1].arguments[1].name[1:])
                  for s in symbols if s.name=='legal' and s.arguments[0].name==role
                  and s.arguments[1].name=='move')

def state_terms(position):
    return set(str(s.arguments[0]) for s in evaluate('true(dummy).',position) if s.name=='true' and str(s.arguments[0])!='dummy')
