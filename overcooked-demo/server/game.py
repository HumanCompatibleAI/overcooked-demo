from abc import ABC, abstractmethod
from threading import Lock
from queue import Queue, Empty
from overcooked_ai_py.mdp.overcooked_mdp import OvercookedGridworld

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

    def __init__(self, *args, **kwargs):
        """
        players (list): List of IDs of players currently in the game
        id (int):   Unique identifier for this game
        pending_actions (Queue): Buffer of (player_id, action) pairs have submitted that haven't been commited yet
        lock (Lock):    Used to serialize updates to the game state
        is_active(bool): Whether the game is currently being played or not
        """
        self.players = []
        self.pending_actions = Queue()
        self.id = kwargs.get('id', id(self))
        self.lock = Lock()
        self._is_active = False

    @abstractmethod
    def is_full(self):
        """
        Returns whether the game can currently be started. Usually conditioned on correct number of players having joined
        """
        pass

    @abstractmethod
    def apply_action(self, player_id, action):
        """
        Updates the game state by applying a single (player_id, action) tuple. Subclasses should try to override this method
        if possible
        """
        pass


    @abstractmethod
    def is_finished(self):
        """
        Returns whether the game has concluded or not
        """
        pass

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
        try:
            while True:
                player_id, action = self.pending_actions.get(block=False)
                self.apply_action(player_id, action)
        except Empty:
            pass

    def activate(self):
        """
        Activates the game to let server know real-time updates should start. Provides no functionality but useful as
        a check for debugging
        """
        self._is_active = True


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
        self.pending_actions.put((player_id, action))

    def get_state(self):
        """
        Return a JSON compatible serialized state of the game. Note that this should be as minimalistic as possible
        as the size of the game state will be the most important factor in game performance
        """
        return { "players" : self.players }

    def is_empty(self):
        """
        Return whether it is safe to garbage collect this game instance
        """
        return not len(self.players)

    def add_player(self, player_id):
        """
        Add player_id to the game
        """
        if self.is_active:
            raise ValueError("Cannot add players to active games")
        self.players.append(player_id)

    def remove_player(self, player_id):
        """
        Remove player_id from the game
        """
        try:
            self.players.remove(player_id)
        except ValueError:
            return False
        else:
            return True
        


class DummyGame(Game):

    """
    Standin class used to test basic server logic
    """

    def __init__(self, **kwargs):
        super(DummyGame, self).__init__(**kwargs)
        self.counter = 0

    def is_full(self):
        return len(self.players) == 2

    def apply_action(self):
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
        self.num_players = int(kwargs.get('playerZero', 'human') == 'human') + int(kwargs.get('playerOne', 'human') == 'human')
        self.max_count = kwargs.get('max_count', 100)
        self.counter = 0
        self.counts = [0] * self.num_players

    def is_full(self):
        return len(self.players) == self.num_players

    def is_finished(self):
        return max(self.counts) >= self.max_count

    def apply_action(self, player_id, action):
        player_idx = self.players.index(player_id)
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

    


    