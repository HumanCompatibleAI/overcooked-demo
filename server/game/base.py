from abc import ABC, abstractmethod
from queue import Queue, LifoQueue, Empty, Full
from threading import Lock, Thread, Event, Semaphore
from game.utils import SafeGameMethod, GameError
import game

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
    
    class Status:
        DONE = 'done'
        ACTIVE = 'active'
        RESET = 'reset'
        INACTIVE = 'inactive'
        ERROR = 'error'



    def __init__(self, *args, **kwargs):
        """
        players (list): List of IDs of players currently in the game
        spectators (set): Collection of IDs of players that are not allowed to enqueue actions but are currently watching the game
        id (int):   Unique identifier for this game
        pending_actions List[(Queue)]: Buffer of (player_id, action) pairs have submitted that haven't been commited yet
        lock (Lock):    Used to serialize updates to the game state
        is_active(bool): Whether the game is currently being played or not
        fps (int): Number of times `tick` will be called per second
        debug (bool): Whether to print verbose warnings for debugging
        ignore_invalid_actions (bool): Whether to silently fail if client tries to enqueue invalid action. Rasie GameError if false
        """
        self.players = []
        self.spectators = set()
        self.pending_actions = []
        self.id = kwargs.get('id', id(self))
        self.lock = Lock()
        self._is_active_ = False
        self.fps = min(kwargs.get('fps', game.static.MAX_FPS), game.static.MAX_FPS)
        self.debug = kwargs.get('debug', False)
        self.ignore_invalid_actions = kwargs.get('ignore_invalid_actions', True)

    @abstractmethod
    def _is_full(self):
        """
        Returns whether there is room for additional players to join or not
        """
        pass

    @abstractmethod
    def _apply_action(self, player_idx, action):
        """
        Updates the game state by applying a single (player_idx, action) tuple. Subclasses should try to override this method
        if possible
        """
        pass

    def _is_finished(self):
        """
        Returns whether the game has concluded or not
        """
        return self._curr_game_over and self._is_last_game()

    def _is_ready(self):
        """
        Returns whether the game can be started. Defaults to having enough players
        """
        return self.is_full()

    @abstractmethod
    def _is_last_game(self):
        """
        Returns whether the current game is the last game
        """
        pass
    
    @abstractmethod
    def _curr_game_over(self):
        """
        Returns whether the current game is over
        """
        pass

    @SafeGameMethod
    def is_full(self):
        return self._is_full()

    @SafeGameMethod
    def is_finished(self):
        return self._is_finished()

    @SafeGameMethod
    def is_ready(self):
        return self._is_ready()

    def _is_active(self):
        """
        Whether the game is currently being played
        """
        return self._is_active_

    @SafeGameMethod
    def is_active(self):
        return self._is_active()

    @property
    def reset_timeout(self):
        """
        Number of milliseconds to pause game on reset
        """
        return 3000

    def _apply_actions(self):
        """
        Updates the game state by applying each of the pending actions in the buffer. Is called by the tick method. Subclasses
        should override this method if joint actions are necessary. If actions can be serialized, overriding `apply_action` is 
        preferred
        """
        for i in range(len(self.players)):
            try:
                while True:
                    action = self.pending_actions[i].get(block=False)
                    self._apply_action(i, action)
            except Empty:
                pass
    
    def _activate(self):
        """
        Activates the game to let server know real-time updates should start. Provides little functionality but useful as
        a check for debugging
        """
        self._is_active_ = True

    def _deactivate(self):
        """
        Deactives the game such that subsequent calls to `tick` will be no-ops. Used to handle case where game ends but 
        there is still a buffer of client pings to handle
        """
        self._is_active_ = False

    @SafeGameMethod
    def activate(self):
        return self._activate()

    @SafeGameMethod
    def deactivate(self):
        return self._deactivate()

    def _reset(self):
        """
        Restarts the game while keeping all active players by resetting game stats and temporarily disabling `tick`
        """
        if not self._is_active():
            raise ValueError("Inactive Games cannot be reset")
        if self._is_finished():
            return self.Status.DONE
        self._deactivate()
        self._activate()
        return self.Status.RESET

    @SafeGameMethod
    def reset(self):
        return self._reset()

    def _needs_reset(self):
        """
        Returns whether the game should be reset on the next call to `tick`
        """
        return self._curr_game_over() and not self._is_finished()


    def _tick(self):
        """
        Updates the game state by applying each of the pending actions. This is done so that players cannot directly modify
        the game state, offering an additional level of safety and thread security. 

        One can think of "enqueue_action" like calling "git add" and "tick" like calling "git commit"

        Subclasses should try to override `apply_actions` if possible. Only override this method if necessary
        """ 
        if not self._is_active():
            return self.Status.INACTIVE
        if self._needs_reset():
            self._reset()
            return self.Status.RESET

        self._apply_actions()
        return self.Status.DONE if self.is_finished() else self.Status.ACTIVE

    @SafeGameMethod
    def tick(self):
        return self._tick()
    
    def _enqueue_action(self, player_id, action):
        """
        Add (player_id, action) pair to the pending action queue, without modifying underlying game state

        Note: This function IS thread safe

        Returns whether the action was successfully enqueued
        """
        if not self._is_active():
            # Could run into issues with is_active not being thread safe
            return False
        if player_id not in self.players:
            # Only players actively in game are allowed to enqueue actions
            return False

        # Whether current action is valid
        valid = self.is_valid_action(player_id, action)
        if not valid:
            if self.ignore_invalid_actions:
                return False
            else:
                raise GameError("Action {} for player ID {} is invalid for current game state!".format(action, player_id))
        try:
            player_idx = self.players.index(player_id)
            self.pending_actions[player_idx].put(action)
            return True
        except Full:
            return False
    
    @SafeGameMethod
    def enqueue_action(self, player_id, action):
        return self._enqueue_action(player_id, action)

    def _get_state(self):
        """
        Return a JSON compatible serialized state of the game. Note that this should be as minimalistic as possible
        as the size of the game state will be the most important factor in game performance. This is sent to the client
        every frame update.
        """
        return { "players" : self.players }

    @SafeGameMethod
    def get_state(self):
        return self._get_state()

    def _to_json(self):
        """
        Return a JSON compatible serialized state of the game. Contains all information about the game, does not need to
        be minimalistic. This is sent to the client only once, upon game creation
        """
        return self.get_state()

    @SafeGameMethod
    def to_json(self):
        return self._to_json()

    def _is_empty(self):
        """
        Return whether it is safe to garbage collect this game instance
        """
        return not self.num_players

    @SafeGameMethod
    def is_empty(self):
        return self._is_empty()

    def _add_player(self, player_id, idx=None, buff_size=-1, **kwargs):
        """
        Add player_id to the game
        """
        if self._is_full():
            raise ValueError("Cannot add players to full game")
        if self._is_active():
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

    @SafeGameMethod
    def add_player(self, player_id, idx=None, buff_size=-1, **kwargs):
        return self._add_player(player_id, idx, buff_size, **kwargs)

    def _add_spectator(self, spectator_id):
        """
        Add spectator_id to list of spectators for this game
        """
        if spectator_id in self.players:
            raise ValueError("Cannot spectate and play at same time")
        self.spectators.add(spectator_id)

    @SafeGameMethod
    def add_spectator(self, spectator_id):
        return self._add_spectator(spectator_id)

    def _remove_player(self, player_id):
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

    def _remove_spectator(self, spectator_id):
        """
        Removes spectator_id if they are in list of spectators. Returns True if spectator successfully removed, False otherwise
        """
        try:
            self.spectators.remove(spectator_id)
        except ValueError:
            return False
        else:
            return True

    @SafeGameMethod
    def remove_spectator(self, spectator_id):
        return self._remove_spectator(spectator_id)

    @SafeGameMethod
    def remove_player(self, player_id):
        return self._remove_player(player_id)


    def _clear_pending_actions(self):
        """
        Remove all queued actions for all players
        """
        for i, player in enumerate(self.players):
            if player != self.EMPTY:
                queue = self.pending_actions[i]
                queue.queue.clear()

    def _num_players(self):
        return len([player for player in self.players if player != self.EMPTY])

    @property
    @SafeGameMethod
    def num_players(self):
        return self._num_players()

    def _get_data(self):
        """
        Return any game metadata to server driver. Really only relevant for Psiturk code
        """
        return {}

    @SafeGameMethod
    def get_data(self):
        return self._get_data()

    @abstractmethod
    def _is_valid_action(self, player_id, action):
        """
        Returns whether the `action` is valid for `player_id` in the current game state
        """
        pass

    @SafeGameMethod
    def is_valid_action(self, player_id, action):
        return self._is_valid_action(player_id, action)

class NPCGame(Game):
    """Abstract Class for coordinating computer controlled players (NPCs) with human controlled players

    Instance Variables:
        - ticker_per_ai_action (int): How many frames should pass in between NPC policy forward passes. 
            Note that this is a lower bound; if the policy is computationally expensive the actual frames
            per forward pass can be higher
        - npc_timeout (int): Maximal time after which a random action is enqueued for the NPC
        - npc_players (set(str)): Player IDs for NPC players
        - human_players (set(str)): Player IDs for human players
        - npc_policies (dict): Maps user_id to policy (Agent) for each AI player
        - npc_state_queues (dict): Mapping of NPC user_ids to LIFO queues for the policy to process
    Methods:
        - npc_policy_consumer: Background process that asynchronously computes NPC policy forward passes. One thread
            spawned for each NPC
    Abstract Methods:
        - _get_policy: Accepts a NPC player_id and returns a policy (class that implemts `action` function)
    """

    def __init__(self, ticks_per_ai_action=4, npc_timeout=-1, block_for_ai=False, **kwargs):
        super(NPCGame, self).__init__(**kwargs)
        self.ticks_per_ai_action = ticks_per_ai_action
        self.npc_timeout = npc_timeout
        self.block_for_ai = block_for_ai
        self.npc_players = set()
        self.human_players = set()
        self.npc_state_queues = {}
        self.npc_policies = {}
        self.state = None
        self.threads = []

    def _add_player(self, player_id, idx=None, buff_size=-1, is_human=True):
        super(NPCGame, self)._add_player(player_id, idx=idx, buff_size=buff_size)
        if is_human:
            self.human_players.add(player_id)
        else:
            self.npc_players.add(player_id)

    def _remove_player(self, player_id):
        removed = super(NPCGame, self)._remove_player(player_id)
        if removed:
            if player_id in self.human_players:
                self.human_players.remove(player_id)
            elif player_id in self.npc_players:
                self.npc_players.remove(player_id)
            else:
                raise ValueError("Inconsistent state")

    def npc_policy_consumer(self, policy_id):
        queue = self.npc_state_queues[policy_id]
        policy = self.npc_policies[policy_id]
        while self._is_active():
            state = queue.get()
            # TODO: figure out a pythonic way to set a thread timeout
            # policy_worker = Thread(target=self.policy.action, args=(state,))
            npc_action, _ = policy.action(state)
            self._enqueue_action(policy_id, npc_action)

    def is_npc(self, player_id=None, player_idx=None):
        if player_id is None and player_idx is None:
            raise ValueError("Must provide either player id or index")
        if (player_id is not None) and (player_idx is not None):
            raise ValueError("Must provide iether player id or index, not both")
        if player_idx is not None:
            player_id = self.players[player_idx]
        return player_id in self.npc_players

    def load_npc(self, npc_id):
        npc_idx = self.players.index(npc_id)
        policy_id = '_'.join(npc_id.split('_')[:-1])
        self.npc_policies[npc_id] = self._get_policy(policy_id, idx=npc_idx)
        self.npc_state_queues[npc_id] = LifoQueue()

    def _activate(self):
        super()._activate()

        # Sanity check at start of each game
        if not self.npc_players.union(self.human_players) == set(self.players):
            raise ValueError("Inconsistent State")

        # Load any NPC policies, if necessary
        for npc_id in self.npc_players:
            self.load_npc(npc_id)

        for npc_policy in self.npc_policies:
            t = Thread(target=self.npc_policy_consumer, args=(npc_policy,))
            self.threads.append(t)
            t.start()
            self.npc_policies[npc_policy].reset()

        # Subclasses should consider overriding this method and setting `self.state`

    def _deactivate(self):
        super(NPCGame, self)._deactivate()
        # Ensure the background consumers do not hang
        for npc_policy in self.npc_policies:
            self.npc_state_queues[npc_policy].put(self.state)

        # Wait for all background threads to exit
        for t in self.threads:
            t.join()

        # Clear all action queues
        self._clear_pending_actions()

    @abstractmethod
    def _get_policy(self, npc_id, idx=0):
        pass

    def _is_empty(self):
        """
        Game is considered safe to scrap if there are no active players or if there are no humans (spectating or playing)
        """
        return super(NPCGame, self)._is_empty() or not self.spectators and not self.human_players

    def _is_ready(self):
        """
        Game is ready to be activated if there are a sufficient number of players and at least one human (spectator or player)
        """
        return super(NPCGame, self)._is_ready() and not self._is_empty()

class TurnBasedGame(NPCGame):
    """Abstract class for modifying the default real-time Game logic to support turn-based logic

    Instance Variables:
        - curr_player (str): Player ID of player whose turn it is
        - curr_turn_number (int): Counter of how many turns have passed. Incremented once per turn
        - turn_tokens (dict(str, Semaphore)): Maps player ID to signal of whether it's that players turn.
            Allows parent tick thread to signal child enqueue action threads
        - turn_timeout (int): Maximum amount of seconds allowed for a player to take a turn, after which default
            action is enqueued

    Abtract Methods:
        - _apply_action: Apply a single players action for a single turn, update state
        - get_default_action: Takes player ID and returns default action for that player
    """
    def __init__(self, turn_timeout=10, **kwargs):
        super(TurnBasedGame, self).__init__(**kwargs)
        self.turn_timeout = turn_timeout
        self.curr_player = None
        self.curr_turn_number = -1
        self.turn_tokens = {}
        self.curr_game_number = -1
        self.timeout_thread = None
        self.timeout_exit_event = None

    def _add_player(self, player_id, idx=None, buff_size=-1, is_human=True):
        self.turn_tokens[player_id] = Semaphore(value=0)
        return super(TurnBasedGame, self)._add_player(player_id, idx=idx, buff_size=buff_size, is_human=is_human)
    
    def _activate(self):
        super(TurnBasedGame, self)._activate()
        self.curr_game_number += 1
        self.advance_turn()
        self.timeout_exit_event = Event()
        self.timeout_thread = Thread(target=self.timeout_function, args=())
        self.timeout_thread.start()

    def _deactivate(self):
        super(TurnBasedGame, self)._deactivate()
        self.timeout_exit_event.set()
        self.timeout_thread.join()


    def _enqueue_action(self, player_id, action):
        token_acquired = self.turn_tokens[player_id].acquire(blocking=False)
        if token_acquired:
            # If we got here, it's our turn
            successfully_enqueued = super(TurnBasedGame, self)._enqueue_action(player_id, action)

            # Still our turn if we didn't successfully enqueue
            if not successfully_enqueued:
                self.turn_tokens[player_id].release()
            return successfully_enqueued
        else:
            # This means the semaphore was low (turn token not found) so it's not our turn
            # Log warning and do nothing
            if self.debug:
                if player_id != self.curr_player:
                    print("Warning: Player {} tried to enqueued action when it was {}'s turn!".format(player_id, self.curr_player))
                else:
                    print("Warning: Plyaer {} tried to enqueue multiple actions in their turn!".format(player_id))
            return False

    def _apply_actions(self):
        played_this_turn = []
        for i in range(len(self.players)):
            try:
                action = self.pending_actions[i].get(block=False)
                played_this_turn.append(self.players[i])
                self._apply_action(i, action)
            except Empty:
                pass
        
        # A turn occurred this tick
        if played_this_turn:
            # Basic sanity checking
            if len(played_this_turn) != 1:
                raise RuntimeError("More than one player played this turn!")
            if played_this_turn[0] != self.curr_player:
                raise RuntimeError("Inconsistent state! Player who played this turn was not current player!")
        
            # Update all state pertaining to turn
            self.advance_turn()    

    def advance_turn(self):
        self.curr_turn_number += 1
        self.curr_player = self.get_next_player()
        self.turn_tokens[self.curr_player].release()

        for npc_id in self.npc_players:
            if self.curr_player == npc_id:
                self.npc_state_queues[npc_id].put(self.state)

    def get_next_player(self):
        if not self.curr_player:
            return self.get_start_player()
        return self._get_next_player(self.curr_player)
    
    def _get_next_player(self, curr_player):
        next_idx = (self.players.index(curr_player) + 1) % len(self.players)
        return self.players[next_idx]

    def get_start_player(self):
        return self.players[self.curr_game_number % len(self.players)]

    def timeout_function(self):
        # Local turn state to track changes (or lack thereof)
        prev_player = self.curr_player
        prev_turn_number = self.curr_turn_number

        # Loop until parent thread signals us to stop, waking up every `turn_timeout` seconds
        while not self.timeout_exit_event.wait(timeout=self.turn_timeout):
            if self.curr_player == prev_player and self.curr_turn_number == prev_turn_number:
                # We went through a sleep cycle and no turn advance happened, timeout!
                default_action = self.get_default_action(self.curr_player)
                print("keys inside timeout", self.turn_tokens.keys())
                self._enqueue_action(self.curr_player, default_action)
            else:
                # Update local turn state
                prev_player = self.curr_player
                prev_turn_number = self.curr_turn_number

    @abstractmethod
    def get_default_action(self, player_id):
        pass


class NPC(ABC):
    @abstractmethod
    def action(self, state):
        """
        Abstract method wrapping the NPC policy logic

        Args:
            - state (obj): Current game state, determined by the game class

        Returns:
            tuple(action, infos)
        """
        pass

    def reset(self):
        """
        Resets any necessary state for the policy. Called once per episode
        """
        pass