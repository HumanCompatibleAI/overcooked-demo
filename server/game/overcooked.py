from game.base import NPCGame, NPC
from game.static import MAX_GAME_TIME, AGENT_DIR
from overcooked_ai_py.mdp.actions import Action, Direction
from overcooked_ai_py.mdp.overcooked_mdp import OvercookedGridworld
from overcooked_ai_py.planning.planners import MotionPlanner
from queue import Empty
from time import time
import random, traceback, os, json, math


class OvercookedGame(NPCGame):
    """
    Class for bridging the gap between Overcooked_Env and the Game interface

    Instance variable:
        - max_players (int): Maximum number of players that can be in the game at once
        - mdp (OvercookedGridworld): Controls the underlying Overcooked game logic
        - score (int): Current reward acheived by all players
        - max_time (int): Number of seconds the game should last
        - npc_policies (dict): Maps user_id to policy (Agent) for each AI player
        - npc_state_queues (dict): Mapping of NPC user_ids to LIFO queues for the policy to process
        - curr_tick (int): How many times the game server has called this instance's `tick` method
        - action_to_overcooked_action (dict): Maps action names returned by client to action names used by OvercookedGridworld
            Note that this is an instance variable and not a static variable for efficiency reasons
        - randomized (boolean): Whether the order of the layouts should be randomized
    
    Methods:
        - _curr_game_over: Determines whether the game on the current mdp has ended
    """

    def __init__(self, layouts=["cramped_room"], mdp_params={}, num_players=2, gameTime=30, playerZero='human', playerOne='human', showPotential=False, randomized=False, **kwargs):
        super(OvercookedGame, self).__init__(**kwargs)
        self.show_potential = showPotential
        self.mdp_params = mdp_params
        self.layouts = layouts
        self.max_players = int(num_players)
        self.mdp = None
        self.mp = None
        self.score = 0
        self.phi = 0
        self.max_time = min(int(gameTime), MAX_GAME_TIME)
        self.action_to_overcooked_action = {
            "STAY" : Action.STAY,
            "UP" : Direction.NORTH,
            "DOWN" : Direction.SOUTH,
            "LEFT" : Direction.WEST,
            "RIGHT" : Direction.EAST,
            "SPACE" : Action.INTERACT
        }
        self.curr_tick = 0

        if randomized:
            random.shuffle(self.layouts)

        if playerZero != 'human':
            player_zero_id = playerZero + '_0'
            self._add_player(player_zero_id, idx=0, buff_size=1, is_human=False)

        if playerOne != 'human':
            player_zero_id = playerOne + '_1'
            self._add_player(player_zero_id, idx=1, buff_size=1, is_human=False)
        
    def _is_last_game(self):
        return not self.layouts

    def _curr_game_over(self):
        return time() - self.start_time >= self.max_time

    def _is_full(self):
        return self.num_players >= self.max_players

    def _is_empty(self):
        """
        Game is considered safe to scrap if there are no active players or if there are no humans (spectating or playing)
        """
        return super(OvercookedGame, self)._is_empty() or not self.spectators and not self.human_players

    def _is_ready(self):
        """
        Game is ready to be activated if there are a sufficient number of players and at least one human (spectator or player)
        """
        return super(OvercookedGame, self)._is_ready() and not self._is_empty()

    def _apply_action(self, player_id, action):
        pass

    def _apply_actions(self):
        # Default joint action, as NPC policies and clients probably don't enqueue actions fast 
        # enough to produce one at every tick
        joint_action = [Action.STAY] * len(self.players)

        # Synchronize individual player actions into a joint-action as required by overcooked logic
        for i in range(len(self.players)):
            try:
                block = self.is_npc(player_idx=i) and self.block_for_ai
                joint_action[i] = self.pending_actions[i].get(block=block)
            except Empty:
                pass
        
        # Apply overcooked game logic to get state transition
        prev_state = self.state
        self.state, info = self.mdp.get_state_transition(prev_state, joint_action)
        if self.show_potential:
            self.phi = self.mdp.potential_function(prev_state, self.mp, gamma=0.99)

        # Send next state to all background consumers if needed
        if self.curr_tick % self.ticks_per_ai_action == 0:
            for npc_id in self.npc_policies:
                self.npc_state_queues[npc_id].put(self.state, block=False)

        # Update score based on soup deliveries that might have occured
        curr_reward = sum(info['sparse_reward_by_agent'])
        self.score += curr_reward

        # Return about the current transition
        return prev_state, joint_action, info
        

    def _enqueue_action(self, player_id, action):
        overcooked_action = self.action_to_overcooked_action[action]
        super(OvercookedGame, self)._enqueue_action(player_id, overcooked_action)

    def _reset(self):
        status = super(OvercookedGame, self)._reset()
        if status == self.Status.RESET:
            # Hacky way of making sure game timer doesn't "start" until after reset timeout has passed
            self.start_time += self.reset_timeout / 1000


    def _tick(self):
        self.curr_tick += 1
        return super(OvercookedGame, self)._tick()

    def _activate(self):
        super(OvercookedGame, self)._activate()

        self.curr_layout = self.layouts.pop()
        self.mdp = OvercookedGridworld.from_layout_name(self.curr_layout, **self.mdp_params)
        if self.show_potential:
            self.mp = MotionPlanner.from_pickle_or_compute(self.mdp, counter_goals=[])
        self.state = self.mdp.get_standard_start_state()
        if self.show_potential:
            self.phi = self.mdp.potential_function(self.state, self.mp, gamma=0.99)

            self.start_time = time()
        self.curr_tick = 0
        self.score = 0

        for npc_id in self.npc_players:
            self.npc_state_queues[npc_id].put(self.state)
        


    def _get_state(self):
        state_dict = {}
        state_dict['ood'] = self.mdp.is_off_distribution(self.state) if self.show_potential else None
        state_dict['potential'] = self.phi if self.show_potential else None
        state_dict['state'] = self.state.to_dict()
        state_dict['score'] = self.score
        state_dict['time_left'] = max(self.max_time - (time() - self.start_time), 0)
        return state_dict

    def _to_json(self):
        obj_dict = {}
        obj_dict['terrain'] = self.mdp.terrain_mtx if self._is_active() else None
        obj_dict['state'] = self.get_state() if self._is_active() else None
        return obj_dict

    def _get_policy(self, npc_id, idx=0):
        if npc_id.lower().startswith("ppo"):
            try:
                # Loading rllib agents requires additional helpers
                import ray
                from human_aware_rl.rllib.rllib import PPOAgent
                fpath = os.path.join(AGENT_DIR, self.curr_layout, npc_id)
                agent = PPOAgent.load(fpath)
                agent.set_agent_index(idx)
                agent.stochastic = True
                return agent
            except Exception as e:
                print(traceback.format_exc(), flush=True)
                raise IOError("Error loading Rllib Agent\n{}".format(e.__repr__()))
            finally:
                # Always kill ray after loading agent, otherwise, ray will crash once process exits
                if ray.is_initialized():
                    ray.shutdown()
        elif npc_id.lower().startswith('bc'):
            try:
                # Loading BC agents requires additional helpers
                from human_aware_rl.imitation.behavior_cloning_tf2 import BehaviorCloningAgent
                agent_dir = os.path.join(AGENT_DIR, self.curr_layout, npc_id)
                agent = BehaviorCloningAgent.load(agent_dir)
                agent.set_agent_index(idx)
                agent.stochastic = True
                return agent
            except Exception as e:
                print(traceback.format_exc(), flush=True)
                raise IOError("Error loading BC agent\n{}".format(e.__repr__()))

        else:
            try:
                # Loading vanilla OvercookedAgent
                layout_agent_dir = os.path.join(AGENT_DIR, self.curr_layout, npc_id)
                generic_agent_dir = os.path.join(AGENT_DIR, 'all', npc_id)
                agent_dir = None

                if not os.path.exists(layout_agent_dir) and not os.path.exists(generic_agent_dir):
                    raise FileNotFoundError("Agent {} does not exist!".format(npc_id))

                if not os.path.exists(layout_agent_dir):
                    agent_dir = generic_agent_dir
                else:
                    agent_dir = layout_agent_dir
                
                agent = Agent.load(agent_dir)
                agent.set_agent_index(idx)
                return agent
            except Exception as e:
                print(traceback.format_exc(), flush=True)
                raise IOError("Error loading agent\n{}".format(e.__repr__()))

class OvercookedPsiturk(OvercookedGame):
    """
    Wrapper on OvercookedGame that handles additional housekeeping for Psiturk experiments

    Instance Variables:
        - trajectory (list(dict)): list of state-action pairs in current trajectory
        - psiturk_uid (string): Unique id for each psiturk game instance (provided by Psiturk backend)
            Note, this is not the user id -- two users in the same game will have the same psiturk_uid
        - trial_id (string): Unique identifier for each psiturk trial, updated on each call to reset
            Note, one OvercookedPsiturk game handles multiple layouts. This is how we differentiate

    Methods:
        get_data: Returns the accumulated trajectory data and clears the self.trajectory instance variable
    
    """

    def __init__(self, *args, psiturk_uid='-1', **kwargs):
        super(OvercookedPsiturk, self).__init__(*args, showPotential=False, **kwargs)
        self.psiturk_uid = str(psiturk_uid)
        self.trajectory = []

    def _activate(self):
        """
        Resets trial ID at start of new "game"
        """
        super(OvercookedPsiturk, self)._activate()
        self.trial_id = self.psiturk_uid + str(self.start_time)

    def _apply_actions(self):
        """
        Applies pending actions then logs transition data
        """
        # Apply MDP logic
        prev_state, joint_action, info = super(OvercookedPsiturk, self)._apply_actions()

        # Log data to send to psiturk client
        curr_reward = sum(info['sparse_reward_by_agent'])
        transition = {
            "state" : json.dumps(prev_state.to_dict()),
            "joint_action" : json.dumps(joint_action),
            "reward" : curr_reward,
            "time_left" : max(self.max_time - (time() - self.start_time), 0),
            "score" : self.score,
            "time_elapsed" : time() - self.start_time,
            "cur_gameloop" : self.curr_tick,
            "layout" : json.dumps(self.mdp.terrain_mtx),
            "layout_name" : self.curr_layout,
            "trial_id" : self.trial_id,
            "player_0_id" : self.players[0],
            "player_1_id" : self.players[1],
            "player_0_is_human" : self.players[0] in self.human_players,
            "player_1_is_human" : self.players[1] in self.human_players
        }

        self.trajectory.append(transition)

    def _get_data(self):
        """
        Returns and then clears the accumulated trajectory
        """
        data = { "uid" : self.psiturk_uid  + "_" + str(time()), "trajectory" : self.trajectory }
        self.trajectory = []
        return data

class OvercookedTutorial(OvercookedGame):

    """
    Wrapper on OvercookedGame that includes additional data for tutorial mechanics, most notably the introduction of tutorial "phases"

    Instance Variables:
        - curr_phase (int): Indicates what tutorial phase we are currently on
        - phase_two_score (float): The exact sparse reward the user must obtain to advance past phase 2
        - phase_one_cook_time (int): Number of timesteps required to cook soup in first phase
    """

    # Lis of all currently supported tutorial layouts and what phase they correspond to
    LAYOUT_TO_PHASE = {
        'tutorial_0' : 0,
        'tutorial_1' : 1,
        'tutorial_2' : 2,
        'tutorial_3' : 3
    }
    

    def __init__(self, layouts=["tutorial_0"], mdp_params={}, playerZero='human', playerOne='AI', phaseTwoScore=15, phaseOneCookTime=45, **kwargs):
        if not set(layouts).issubset(self.LAYOUT_TO_PHASE):
            raise ValueError("One or more layouts is not currently supported as a valid tutorial layout!")
        self.phase_two_score = phaseTwoScore
        self.phase_one_cook_time = phaseOneCookTime
        self.phase_two_finished = False
        super(OvercookedTutorial, self).__init__(layouts=layouts, mdp_params=mdp_params, playerZero=playerZero, playerOne=playerOne, **kwargs)
        self.show_potential = False
        self.max_time = 0
        self.max_players = 2
        self.curr_phase = -1

    @property
    def reset_timeout(self):
        return 1

    def _curr_game_over(self):
        if self.curr_phase == 0:
            return self.score > 0
        elif self.curr_phase == 1:
            return self.score > 0
        elif self.curr_phase == 2:
            return self.phase_two_finished
        elif self.curr_phase == 3:
            return self.score >= float('inf')
        return False

    def _activate(self):
        super(OvercookedTutorial, self)._activate()
        self.curr_phase = self.LAYOUT_TO_PHASE[self.curr_layout]

    def _get_policy(self, *args, **kwargs):
        return TutorialAI(self.LAYOUT_TO_PHASE, self.layouts, self.ticks_per_ai_action, self.phase_one_cook_time)

    def _apply_actions(self):
        """
        Apply regular MDP logic with retroactive score adjustment tutorial purposes
        """
        prev_state, joint_action, info = super(OvercookedTutorial, self)._apply_actions()

        human_reward, ai_reward = info['sparse_reward_by_agent']

        # We only want to keep track of the human's score in the tutorial
        self.score -= ai_reward

        # Phase two requires a specific reward to complete
        if self.curr_phase == 2:
            self.score = 0
            if human_reward == self.phase_two_score:
                self.phase_two_finished = True

        return prev_state, joint_action, human_reward

class OvercookedTutorialPsiturk(OvercookedTutorial):


    def __init__(self, *args, psiturk_uid='-1', **kwargs):
        super(OvercookedTutorialPsiturk, self).__init__(*args, **kwargs)
        self.psiturk_uid = str(psiturk_uid)
        self.trajectory = []

    def _activate(self):
        """
        Resets trial ID at start of new "game"
        """
        super(OvercookedTutorialPsiturk, self)._activate()
        self.trial_id = self.psiturk_uid + '_tutorial_' + str(self.start_time)

    def _apply_actions(self):
        """
        Applies pending actions then logs transition data
        """
        # Apply MDP logic
        prev_state, joint_action, human_reward = super(OvercookedTutorialPsiturk, self)._apply_actions()

        # Log data to send to psiturk client
        transition = {
            "state" : json.dumps(prev_state.to_dict()),
            "joint_action" : json.dumps(joint_action),
            "reward" : human_reward,
            "time_left" : max(self.max_time - (time() - self.start_time), 0),
            "score" : self.score,
            "time_elapsed" : time() - self.start_time,
            "cur_gameloop" : self.curr_tick,
            "layout" : json.dumps(self.mdp.terrain_mtx),
            "layout_name" : self.curr_layout,
            "trial_id" : self.trial_id,
            "player_0_id" : self.players[0],
            "player_1_id" : self.players[1],
            "player_0_is_human" : self.players[0] in self.human_players,
            "player_1_is_human" : self.players[1] in self.human_players
        }

        self.trajectory.append(transition)

    def _get_data(self):
        """
        Returns and then clears the accumulated trajectory
        """
        data = { "uid" : self.psiturk_uid  + "_" + str(time()), "tutorial_trajectory" : self.trajectory }
        self.trajectory = []
        return data

class TutorialAI(NPC):

    COOK_SOUP_ACTIONS = [
        # Grab first onion
        Direction.WEST,
        Direction.WEST,
        Direction.WEST,
        Action.INTERACT,

        # Place onion in pot
        Direction.EAST,
        Direction.NORTH,
        Action.INTERACT,

        # Grab second onion
        Direction.WEST,
        Action.INTERACT,

        # Place onion in pot
        Direction.EAST,
        Direction.NORTH,
        Action.INTERACT,

        # Grab third onion
        Direction.WEST,
        Action.INTERACT,

        # Place onion in pot
        Direction.EAST,
        Direction.NORTH,
        Action.INTERACT,

        # Cook soup
        Action.INTERACT
    ]

    GRAB_PLATE_ACTIONS = [
        # Grab plate
        Direction.EAST,
        Direction.SOUTH,
        Action.INTERACT,
        Direction.WEST,
        Direction.NORTH,
    ]

    DELIVER_SOUP_ACTIONS = [
        # Deliver soup
        Action.INTERACT,
        Direction.EAST,
        Direction.EAST,
        Direction.EAST,
        Action.INTERACT,
        Direction.WEST
    ]

    COOK_SOUP_COOP_LOOP = [
        # Grab first onion
        Direction.WEST,
        Direction.WEST,
        Direction.WEST,
        Action.INTERACT,

        # Place onion in pot
        Direction.EAST,
        Direction.SOUTH,
        Action.INTERACT,

        # Move to start so this loops
        Direction.EAST,
        Direction.EAST,

        # Pause to make cooperation more real time
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY
    ]

    def __init__(self, layout_to_phase_map, layouts=['tutorial_0'], ticks_per_action=8, soup_cook_time=45):
        if ticks_per_action <= 0 or soup_cook_time <= 0:
            raise ValueError("Ticks per action and soup cook time must both be >= 0!")
        self.layout_to_phase = layout_to_phase_map
        self.layouts = layouts.copy()
        self.curr_layout = None
        self.curr_phase = -1
        self.curr_tick = -1
        self._build_cooking_loop(ticks_per_action, soup_cook_time)

        
    def _build_cooking_loop(self, ticks_per_action, soup_cook_time):
        # Calculate number of "STAY" actions necessary to wait for soup to cook
        grab_plate_ticks = 2 * (ticks_per_action - 1) + len(self.GRAB_PLATE_ACTIONS) * ticks_per_action
        cook_ticks_remaining = max(0, soup_cook_time - grab_plate_ticks)
        num_noops = math.ceil(cook_ticks_remaining / ticks_per_action)

        # Concatenate all Cooking routines
        self.WAIT_TO_COOK_ACTIONS = [Action.STAY] * num_noops
        self.COOK_SOUP_LOOP = [*self.COOK_SOUP_ACTIONS, *self.GRAB_PLATE_ACTIONS, *self.WAIT_TO_COOK_ACTIONS, *self.DELIVER_SOUP_ACTIONS]

    def action(self, state):
        self.curr_tick += 1
        if self.curr_phase == 0:
            return self.COOK_SOUP_LOOP[self.curr_tick % len(self.COOK_SOUP_LOOP)], None
        elif self.curr_phase == 2:
            return self.COOK_SOUP_COOP_LOOP[self.curr_tick % len(self.COOK_SOUP_COOP_LOOP)], None
        return Action.STAY, None

    def reset(self):
        self.curr_layout = self.layouts.pop()
        self.curr_phase = self.layout_to_phase[self.curr_layout]
        self.curr_tick = -1
