import json
from game.base import TurnBasedGame
from kaggle_environments import make
from enum import Enum
from time import time
import numpy as np

class ConnectFourGame(TurnBasedGame):

    # Flags
    class PlayerStatus(Enum):
        ACTIVE = 'ACTIVE'
        INACTIVE = 'INACTIVE'
        DONE = 'DONE'

    def __init__(self, base_params={}, playerZero='human', playerOne='human', num_games=2, npc_wait_time=2, **kwargs):
        super(ConnectFourGame, self).__init__(**kwargs)
        self.base_env_params = base_params
        self.npc_wait_time = int(npc_wait_time)
        self.num_games = int(num_games)
        self.max_players = 2
        self.base_env = None

        if playerZero != 'human':
            player_zero_id = playerZero + '_0'
            self._add_player(player_zero_id, idx=0, buff_size=1, is_human=False)

        if playerOne != 'human':
            player_zero_id = playerOne + '_1'
            self._add_player(player_zero_id, idx=1, buff_size=1, is_human=False)

    @property
    def config(self):
        return self.base_env.configuration

    @property
    def board_shape(self):
        return (self.config['rows'], self.config['columns'])

    @property
    def active_player_idx(self):
        try:
            return self.player_statuses.index(self.PlayerStatus.ACTIVE)
        except Exception:
            return -1

    @property
    def active_player_id(self):
        return None if self.active_player_idx == -1 else self.players[self.active_player_idx]

    @property
    def inactive_player_idx(self):
        try:
            return self.player_statuses.index(self.PlayerStatus.INACTIVE)
        except Exception:
            return -1

    @property
    def inactive_player_id(self):
        return None if self.inactive_player_idx == -1 else self.players[self.inactive_player_idx]

    @property
    def board(self):
        if not self.base_env:
            return None
        p0_obs, p1_obs = [obs['observation'] for obs in self.state]
        if 'board' in p0_obs:
            return p0_obs['board']
        if 'board' in p1_obs:
            return p1_obs['board']
        raise ValueError("`board` not found in either player observation!")
    
    @property
    def board_as_grid(self):
        return np.array(self.board, np.int).reshape(*self.board_shape).tolist()

    @property
    def open_columns(self):
        return np.argwhere(np.array(self.board_as_grid[0]) == 0).flatten().tolist()

    @property
    def player_statuses(self):
        if not self.base_env:
            raise ValueError("Game must be activated before player statuses are determined")
        return [self.PlayerStatus(pi['status']) for pi in self.base_env.state]

    @property
    def state(self):
        if not self.base_env:
            return None
        return self.base_env.state

    @state.setter
    def state(self, val):
        if not hasattr(self, 'base_env') or not self.base_env:
            return
        self.base_env.state = val

    def get_player_status(self, player_id=None, player_idx=None):
        if player_id is None and player_idx is None:
            raise ValueError("Either one of `player_id` or `player_idx` must be provided!")
        if player_id is not None and player_idx is not None:
            raise ValueError("Both player_id and player_idx were provided, please provided either!")
        if player_idx is None:
            player_idx = self.players.index(player_id)
        return self.player_statuses[player_idx]

    def get_default_action(self, player_id):
        ret = np.random.choice(self.open_columns)
        return ret

    def advance_turn(self):
        super(ConnectFourGame, self).advance_turn()
        if self.active_player_id and self.curr_player != self.active_player_id:
            raise RuntimeError("Inconsistent state! Active player={} but current player={}".format(self.active_player_id, self.curr_player))

    def _curr_game_over(self):
        return any([status == self.PlayerStatus.DONE for status in self.player_statuses])

    def _is_last_game(self):
        return self.curr_game_number + 1 == self.num_games

    def _is_full(self):
        return self.num_players == self.max_players

    def _is_valid_action(self, player_id, action):
        int_action = self.tryParseAction(action)
        return int_action in self.open_columns

    def tryParseAction(self, action):
        """
        Convert `action` (could be string or int-like) to int action base_env can handle
        Returns -1 if action is invalid type
        """
        try:
            int_action = int(action)
        except Exception:
            int_action = -1
        finally:
            return int_action


    def _apply_action(self, player_idx, action):
        # State sanity check
        if not self.get_player_status(player_idx=player_idx) == self.PlayerStatus.ACTIVE:
            raise ValueError("Apply action called for player_idx={} but that player is not active!".format(player_idx))
        
        # Type conversion + check
        int_action = self.tryParseAction(action)
        if action == -1:
            raise ValueError("Action {} provided was invalid!".format(action))

        # Convert to joint action required by base env
        joint_action = [0] * self.num_players
        joint_action[player_idx] = int_action

        # Do the thing
        self.base_env.step(joint_action)

    def _activate(self):
        self.base_env = make('connectx', self.base_env_params)
        self.base_env.reset()

        # Here we call the super class _activate at the end as it relies on `self.state` being set
        super()._activate()

    def _to_json(self):
        obj_dict = {}
        obj_dict['base_env_config'] = self.config
        obj_dict['state'] = self._get_state()
        return obj_dict

    def _get_state(self):
        state_dict = {}
        state_dict['board'] = self.board
        state_dict['open_columns'] = self.open_columns
        state_dict['active_player_id'] = self.active_player_id
        state_dict['turn_time_remaining'] = self.turn_timeout - self.curr_turn_time
        return state_dict

    def _get_policy(self, npc_id, idx):
        # TODO
        return None

class ConnectFourPsiturk(ConnectFourGame):

    def __init__(self, *args, psiturk_uid='-1', **kwargs):
        super(ConnectFourPsiturk, self).__init__(*args, **kwargs)
        self.psiturk_uid = str(psiturk_uid)
        self.trajectory = []

    def _activate(self):
        """
        Resets trial ID at start of new "game"
        """
        super(ConnectFourPsiturk, self)._activate()
        self.start_time = time.now()
        self.trial_id = self.psiturk_uid + str(self.start_time)

    def _apply_actions(self):
        """
        Applies pending actions then logs transition data
        """
        # Apply MDP logic
        prev_state, joint_action, info = super(ConnectFourPsiturk, self)._apply_actions()

        # Log data to send to psiturk client
        if any(info['played_this_turn']):
            transition = self._get_transition(prev_state, joint_action, info)
            self.trajectory.append(transition)

    def _get_transition(self, state, joint_action, info):
        transition = {
            "state" : json.dumps(state),
            "joint_action" : json.dumps(joint_action),
            "time_elapsed" : time() - self.start_time,
            "curr_turn_time" : info["curr_turn_time"],
            "curr_turn_number" : info['curr_turn_number'],
            "was_turn_timeout" : info["was_turn_timeout"],
            "trial_id" : self.trial_id,
            "player_0_id" : self.players[0],
            "player_1_id" : self.players[1],
            "player_0_is_human" : self.players[0] in self.human_players,
            "player_1_is_human" : self.players[1] in self.human_players,
            "player_0_played_this_turn" : info['played_this_turn'][0],
            "player_1_played_this_turn" : info['played_this_turn'][1]
        }
        return transition

    def _get_data(self):
        """
        Returns and then clears the accumulated trajectory
        """
        data = { "uid" : self.psiturk_uid  + "_" + str(time()), "trajectory" : self.trajectory }
        self.trajectory = []
        return data