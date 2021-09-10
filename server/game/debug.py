from game.base import Game, NPC
from overcooked_ai_py.mdp.actions import Action, Direction
import random

class DummyGame(Game):

    """
    Standin class used to test basic server logic
    """

    def __init__(self, **kwargs):
        super(DummyGame, self).__init__(**kwargs)
        self.counter = 0

    def _is_full(self):
        return self.num_players == 2

    def _apply_action(self, idx, action):
        pass

    def _apply_actions(self):
        self.counter += 1

    def _is_finished(self):
        return self.counter >= 100

    def _get_state(self):
        state = super(DummyGame, self)._get_state()
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

    def _is_full(self):
        return self.num_players == self.max_players

    def _is_finished(self):
        return max(self.counts) >= self.max_count

    def _apply_action(self, player_idx, action):
        if action.upper() == Direction.NORTH:
            self.counts[player_idx] += 1
        if action.upper() == Direction.SOUTH:
            self.counts[player_idx] -= 1

    def _apply_actions(self):
        super(DummyInteractiveGame, self)._apply_actions()
        self.counter += 1

    def _get_state(self):
        state = super(DummyInteractiveGame, self)._get_state()
        state['count'] = self.counter
        for i in range(self.num_players):
            state['player_{}_count'.format(i)] = self.counts[i]
        return state

class BuggyGame(DummyInteractiveGame):
    def __init__(self, *args, buggy_activate=False, buggy_tick=True, buggy_add_player=False, buggy_enqueue_action=False, **kwargs):
        super(BuggyGame, self).__init__(*args, **kwargs)
        self.buggy_activate = buggy_activate
        self.buggy_tick = buggy_tick
        self.buggy_add_player = buggy_add_player
        self.buggy_enqueue_action = buggy_enqueue_action


    def _activate(self):
        super(BuggyGame, self)._activate()
        if self.buggy_activate:
            raise Exception("This is a bug!")

    def _tick(self):
        super(BuggyGame, self)._tick()
        if self.buggy_tick:
            raise Exception("This is a bug!")

    def _add_player(self, *args, **kwargs):
        super(BuggyGame, self)._add_player(*args, **kwargs)
        if self.buggy_add_player:
            raise Exception("This is a bug!")

    def _enqueue_action(self, *args, **kwargs):
        super(BuggyGame, self)._enqueue_action(*args, **kwargs)
        if self.buggy_enqueue_action:
            raise Exception("This is a bug!")

class DummyOvercookedAI(NPC):
    """
    Randomly samples actions. Used for debugging
    """
    def action(self, state):
        [action] = random.sample([Action.STAY, Direction.NORTH, Direction.SOUTH, Direction.WEST, Direction.EAST, Action.INTERACT], 1)
        return action, None

class DummyOvercookedComputeAI(DummyOvercookedAI):
    """
    Performs simulated compute before randomly sampling actions. Used for debugging
    """
    def __init__(self, compute_unit_iters=1e5):
        """
        compute_unit_iters (int): Number of for loop cycles in one "unit" of compute. Number of 
                                    units performed each time is randomly sampled
        """
        super(DummyOvercookedComputeAI, self).__init__()
        self.compute_unit_iters = int(compute_unit_iters)
    
    def action(self, state):
        # Randomly sample amount of time to busy wait
        iters = random.randint(1, 10) * self.compute_unit_iters

        # Actually compute something (can't sleep) to avoid scheduling optimizations
        val = 0
        for i in range(iters):
            # Avoid branch prediction optimizations
            if i % 2 == 0:
                val += 1
            else:
                val += 2
        
        # Return randomly sampled action
        return super(DummyOvercookedComputeAI, self).action(state)
    
class OvercookedStayAI(NPC):
    """
    Always returns "stay" action. Used for debugging
    """
    def action(self, state):
        return Action.STAY, None
