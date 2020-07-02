from abc import ABC, abstractmethod
from threading import Lock
from queue import Queue, Empty, Full
from time import time
from overcooked_ai_py.mdp.overcooked_mdp import OvercookedGridworld
from overcooked_ai_py.mdp.overcooked_env import OvercookedEnv
from overcooked_ai_py.mdp.actions import Action, Direction

class Game(ABC):

    """
    Class representing a game object. Coordinates the simultaneous actions of arbitrary
    number of players. Override this base class in order to use. 

    Players can post actions to a `pending_actions` queue, and driver code can call `tick` to apply these actions.


    It should be noted that most operations in this class are not on their own thread safe. Thus, client code should
    acquire `self.lock` before making any modifications to the instance. 

    One important exception to the above rule is `enqueue_actions` which is thread safe out of the box
    """

    # Possible TODO: create a static list of IDs used by the class so far to verify id uniqueness
    # This would need to be serialized, however, which might cause too great a performance hit to 
    # be worth it

    EMPTY = 'EMPTY'

    def __init__(self, *args, **kwargs):
        """
        players (list): List of IDs of players currently in the game
        id (int):   Unique identifier for this game
        pending_actions List[(Queue)]: Buffer of (player_id, action) pairs have submitted that haven't been commited yet
        lock (Lock):    Used to serialize updates to the game state
        is_active(bool): Whether the game is currently being played or not
        """
        self.players = []
        self.pending_actions = []
        self.id = kwargs.get('id', id(self))
        self.lock = Lock()
        self._is_active = False

    @abstractmethod
    def is_full(self):
        """
        Returns whether there is room for additional players to join or not
        """
        pass

    @abstractmethod
    def apply_action(self, player_idx, action):
        """
        Updates the game state by applying a single (player_idx, action) tuple. Subclasses should try to override this method
        if possible
        """
        pass


    @abstractmethod
    def is_finished(self):
        """
        Returns whether the game has concluded or not
        """
        pass

    def is_ready(self):
        """
        Returns whether the game can be started. Defaults to having enough players
        """
        return self.is_full()

    @property
    def is_active(self):
        """
        Whether the game is currently being played
        """
        return self._is_active

    def apply_actions(self):
        """
        Updates the game state by applying each of the pending actions in the buffer. Is called by the tick method. Subclasses
        should override this method if joint actions are necessary. If actions can be serialized, overriding `apply_action` is 
        preferred
        """
        for i in range(len(self.players)):
            try:
                while True:
                    action = self.pending_actions[i].get(block=False)
                    self.apply_action(i, action)
            except Empty:
                pass

    def activate(self):
        """
        Activates the game to let server know real-time updates should start. Provides little functionality but useful as
        a check for debugging
        """
        self._is_active = True

    def deactivate(self):
        """
        Deactives the game such that subsequent calls to `tick` will be no-ops. Used to handle case where game ends but 
        there is still a buffer of client pings to handle
        """
        self._is_active = False


    def tick(self):
        """
        Updates the game state by applying each of the pending actions. This is done so that players cannot directly modify
        the game state, offering an additional level of safety and thread security. 

        One can think of "enqueue_action" like calling "git add" and "tick" like calling "git commit"

        Subclasses should try to override `apply_actions` if possible. Only override this method if necessary
        """ 
        if not self.is_active:
            raise ValueError("Can only tick on games that are actively being played")
        self.apply_actions()
        return self.is_finished()
    
    def enqueue_action(self, player_id, action):
        """
        Add (player_id, action) pair to the pending action queue, without modifying underlying game state

        Note: This function IS thread safe
        """
        if not self.is_active:
            raise ValueError("Cannot act in games that are inactive")
        if player_id not in self.players:
            raise ValueError("Invalid player ID")
        try:
            player_idx = self.players.index(player_id)
            self.pending_actions[player_idx].put(action)
        except Full:
            pass

    def get_state(self):
        """
        Return a JSON compatible serialized state of the game. Note that this should be as minimalistic as possible
        as the size of the game state will be the most important factor in game performance. This is sent to the client
        every frame update.
        """
        return { "players" : self.players }

    def to_json(self):
        """
        Return a JSON compatible serialized state of the game. Contains all information about the game, does not need to
        be minimalistic. This is sent to the client only once, upon game creation
        """
        return self.get_state()

    def is_empty(self):
        """
        Return whether it is safe to garbage collect this game instance
        """
        return not len(self.players)

    def add_player(self, player_id, idx=None, buff_size=-1):
        """
        Add player_id to the game
        """
        if self.is_full():
            raise ValueError("Cannot add players to full game")
        if self.is_active:
            raise ValueError("Cannot add players to active games")
        if not idx and self.EMPTY in self.players:
            idx = self.players.index(self.EMPTY)
        elif not idx:
            idx = len(self.players)
        
        padding = max(0, idx - len(self.players) + 1)
        for _ in range(padding):
            self.players.append(self.EMPTY)
            self.pending_actions.append(self.EMPTY)
        
        self.players[idx] = player_id
        self.pending_actions[idx] = Queue(maxsize=buff_size)

    def remove_player(self, player_id):
        """
        Remove player_id from the game
        """
        try:
            idx = self.players.index(player_id)
            self.players[idx] = self.EMPTY
            self.pending_actions[idx] = self.EMPTY
        except ValueError:
            return False
        else:
            return True

    @property
    def num_players(self):
        return len([player for player in self.players if player != self.EMPTY])
        


class DummyGame(Game):

    """
    Standin class used to test basic server logic
    """

    def __init__(self, **kwargs):
        super(DummyGame, self).__init__(**kwargs)
        self.counter = 0

    def is_full(self):
        return self.num_players == 2

    def apply_action(self, idx, action):
        pass

    def apply_actions(self):
        self.counter += 1

    def is_finished(self):
        return self.counter >= 100

    def get_state(self):
        state = super(DummyGame, self).get_state()
        state['count'] = self.counter
        return state


class DummyInteractiveGame(Game):

    """
    Standing class used to test interactive components of the server logic
    """

    def __init__(self, **kwargs):
        super(DummyInteractiveGame, self).__init__(**kwargs)
        self.max_players = int(kwargs.get('playerZero', 'human') == 'human') + int(kwargs.get('playerOne', 'human') == 'human')
        self.max_count = kwargs.get('max_count', 30)
        self.counter = 0
        self.counts = [0] * self.max_players

    def is_full(self):
        return self.num_players == self.max_players

    def is_finished(self):
        return max(self.counts) >= self.max_count

    def apply_action(self, player_idx, action):
        if action.upper() == 'UP':
            self.counts[player_idx] += 1
        if action.upper() == 'DOWN':
            self.counts[player_idx] -= 1

    def apply_actions(self):
        super(DummyInteractiveGame, self).apply_actions()
        self.counter += 1

    def get_state(self):
        state = super(DummyInteractiveGame, self).get_state()
        state['count'] = self.counter
        for i in range(self.num_players):
            state['player_{}_count'.format(i)] = self.counts[i]
        return state

    
class OvercookedGame(Game):
    """
    Class for bridging the gap between Overcooked_Env and the Game interface
    """

    def __init__(self, layout="cramped_room", mdp_params={}, **kwargs):
        super(OvercookedGame, self).__init__()
        self.max_players = kwargs.get('num_players', 2)
        self.mdp = OvercookedGridworld.from_layout_name(layout, **mdp_params)
        self.score = 0
        self.max_time = kwargs.get("gameTime", 60)
        self.npc_policies = {}
        self.action_to_overcooked_action = {
            "STAY" : Action.STAY,
            "UP" : Direction.NORTH,
            "DOWN" : Direction.SOUTH,
            "LEFT" : Direction.WEST,
            "RIGHT" : Direction.EAST,
            "SPACE" : Action.INTERACT
        }

        player_zero = kwargs.get('playerZero', 'human')
        player_one = kwargs.get('playerOne', 'human')

        if player_zero != 'human':
            player_zero_id = player_zero + '_0'
            self.add_player(player_zero_id, idx=0, buff_size=1)
            self.npc_policies[player_zero_id] = self.get_policy(player_zero)

        if player_one != 'human':
            player_one_id = player_one + '_1'
            self.add_player(player_one_id, idx=1, buff_size=1)
            self.npc_policies[player_one_id] = self.get_policy(player_one)


    def is_full(self):
        return self.num_players >= self.max_players

    def is_finished(self):
        return time() - self.start_time >= self.max_time

    def apply_action(self, player_id, action):
        pass

    def apply_actions(self):
        joint_action = [Action.STAY] * len(self.players)

        for i in range(len(self.players)):
            try:
                joint_action[i] = self.pending_actions[i].get(block=False)
            except Empty:
                pass

        self.state, info = self.mdp.get_state_transition(self.state, joint_action)

        self.score += sum(info['sparse_reward_by_agent'])

    def enqueue_action(self, player_id, action):
        overcooked_action = self.action_to_overcooked_action[action]
        super(OvercookedGame, self).enqueue_action(player_id, overcooked_action)


    def tick(self):
        for npc in self.npc_policies:
            npc_action, _ = self.npc_policies[npc].action(self.state)
            self.enqueue_action(npc, npc_action)
        return super(OvercookedGame, self).tick()

    def activate(self):
        super(OvercookedGame, self).activate()
        self.state = self.mdp.get_standard_start_state()
        self.start_time = time()

    def get_state(self):
        state_dict = {}
        state_dict['state'] = self.state.to_dict()
        state_dict['score'] = self.score
        state_dict['time'] = time() - self.start_time
        return state_dict

    def to_json(self):
        obj_dict = {}
        obj_dict['terrain'] = self.mdp.terrain_mtx
        obj_dict['state'] = self.get_state()
        return obj_dict

    def get_policy(self, npc_id):
        # TODO
        return None



class DummyOvercookedGame(OvercookedGame):
    """
    Class that hardcodes the AI to always STAY. Used for debugging
    """
    
    def __init__(self, layout="cramped_room", **kwargs):
        super(DummyOvercookedGame, self).__init__(layout, playerZero='human', playerOne='AI')

    def get_policy(self, _):
        class DummyAI():
            def action(self, state):
                return 'STAY', None
        return DummyAI()
    

    