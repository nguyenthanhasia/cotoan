"""Original OpenSpiel adapter; import this module to register python_cotoan.

Contract follows OpenSpiel's public Game, State and PyObserver interfaces.
The rule logic is contained in rules.py, not copied from another game.
"""
import json
import numpy as np
import pyspiel
from open_spiel.python.observation import IIGObserverForPublicInfoGame
from . import rules

GAME_TYPE=pyspiel.GameType(
    short_name='python_cotoan',long_name='Vietnamese Mathematical Chess configuration family v2',
    dynamics=pyspiel.GameType.Dynamics.SEQUENTIAL,
    chance_mode=pyspiel.GameType.ChanceMode.DETERMINISTIC,
    information=pyspiel.GameType.Information.PERFECT_INFORMATION,
    utility=pyspiel.GameType.Utility.ZERO_SUM,
    reward_model=pyspiel.GameType.RewardModel.TERMINAL,
    min_num_players=2,max_num_players=2,
    provides_information_state_string=True,provides_information_state_tensor=False,
    provides_observation_string=True,provides_observation_tensor=True,
    parameter_specification=rules.DEFAULT_CONFIG.to_dict())

class CoToanGame(pyspiel.Game):
    def __init__(self,params=None):
        params=params or {}
        self.config=rules.Config(**params)
        self.max_plies=self.config.max_plies
        info=pyspiel.GameInfo(num_distinct_actions=9801,max_chance_outcomes=0,num_players=2,
                             min_utility=-1,max_utility=1,utility_sum=0,max_game_length=self.max_plies)
        super().__init__(GAME_TYPE,info,params)

    def new_initial_state(self): return CoToanState(self)

    def make_py_observer(self,iig_obs_type=None,params=None):
        if iig_obs_type is None or (iig_obs_type.public_info and not iig_obs_type.perfect_recall):
            return CoToanObserver(params)
        return IIGObserverForPublicInfoGame(iig_obs_type,params)

    def deserialize_state(self,text):
        data=json.loads(text)
        if set(data)!={'format','config','position'} or data['format']!='cotoan-spiel-state-v2':
            raise ValueError('serialization format')
        if rules.Config.from_dict(data['config'])!=self.config: raise ValueError('configuration mismatch')
        state=CoToanState(self)
        state.position=rules.decode(data['position'])
        rules.result(state.position,self.config)  # validate bounds and threshold consistency
        return state

class CoToanState(pyspiel.State):
    def __init__(self,game):
        super().__init__(game)
        self.position=rules.initial(game.config.first_player)

    def current_player(self):
        return pyspiel.PlayerId.TERMINAL if self.is_terminal() else self.position.turn

    def _legal_actions(self,player):
        if player!=self.current_player(): return []
        return rules.legal(self.position,self.get_game().config)

    def _apply_action(self,action):
        self.position=rules.apply(self.position,action,self.get_game().config)

    def _action_to_string(self,player,action):
        src,dst=divmod(action,99)
        return f'(move {rules.label(src)} {rules.label(dst)})'

    def is_terminal(self): return rules.result(self.position,self.get_game().config) is not None

    def returns(self):
        end=rules.result(self.position,self.get_game().config)
        if end is None or end[0] is None: return [0.,0.]
        return [1.,-1.] if end[0]==0 else [-1.,1.]

    def serialize(self):
        return json.dumps({'format':'cotoan-spiel-state-v2','config':self.get_game().config.to_dict(),
                           'position':rules.encode(self.position)},sort_keys=True,separators=(',',':'))

    def __str__(self): return self.serialize()

class CoToanObserver:
    def __init__(self,params=None):
        if params: raise ValueError('no observation parameters')
        self.tensor=np.zeros(22*11*9+5,dtype=np.float32)
        self.dict={'planes':self.tensor[:-5].reshape(22,11,9),'config':self.tensor[-5:]}

    def set_from(self,state,player):
        del player  # absolute-color representation
        self.tensor.fill(0)
        planes=self.dict['planes']
        for q,c in enumerate(state.position.board):
            if c: planes[(0 if c>0 else 10)+abs(c)-1,q//9,q%9]=1
        planes[20].fill(state.position.turn)
        # Unnormalized integer budget and horizon retain exact Markov state.
        planes[21].fill(state.get_game().max_plies-state.position.ply)
        cfg=state.get_game().config
        self.dict['config'][:]=[cfg.max_plies,cfg.score_target,int(cfg.horizon_rule=='score'),
                               cfg.ops_mask,cfg.first_player]

    def string_from(self,state,player):
        del player
        return str(state)

pyspiel.register_game(GAME_TYPE,CoToanGame)
