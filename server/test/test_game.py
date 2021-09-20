from math import e, exp
import unittest, sys, os, time, random, json
from threading import Thread, Event, Lock

_file_dir = os.path.dirname(os.path.abspath(__file__))
_server_dir = os.path.abspath(os.path.join(_file_dir, '..'))
sys.path.append(_server_dir)
from game.c4 import ConnectFourGame, ConnectFourPsiturk
from game.base import Game, NPC
import game as game_module

class DummyC4NPC(NPC):
    def action(self, _):
        return 0, None

class ConnectFourGameTestWrapper(ConnectFourGame):
    def _get_policy(self, npc_id, idx):
        return DummyC4NPC()

    def get_default_action(self, player_id):
        return 3

class ConnectFourPsiturkTestWrapper(ConnectFourPsiturk):
    def _get_policy(self, npc_id, idx):
        return DummyC4NPC()

    def get_default_action(self, player_id):
        return 3

def _game_loop(exit_event, game):
        while not exit_event.is_set() and not game.is_active():
            time.sleep(0.5)
        
        fps = min(game.fps, game_module.static.MAX_FPS)
        status = Game.Status.ACTIVE
        while not exit_event.is_set() and status != Game.Status.DONE and status != Game.Status.INACTIVE:
            with game.lock:
                status = game.tick()
            if status == Game.Status.RESET:
                with game.lock:
                    _ = game.get_data()
                time.sleep(game.reset_timeou1000)
            time.sleep(1/fps)

class TestConnectFourGame(unittest.TestCase):

    TestCls = ConnectFourGameTestWrapper

    def setUp(self):
        game_module._configure(100, '.', 60)
        self.async_game = self.TestCls(debug=False, fps=30)
        self.sync_game = self.TestCls(debug=False, num_games=2)
        self.sync_npc_game = self.TestCls(debug=False, playerZero="my_npc")
        self.async_npc_game = self.TestCls(debug=False, playerZero="my_npc")
        self.games = [self.async_game, self.sync_game, self.sync_npc_game, self.async_npc_game]
        self.exit_event = Event()

        self.threads = []
        self.threads.append(Thread(target=_game_loop, args=(self.exit_event, self.async_game,)))
        self.threads.append(Thread(target=_game_loop, args=(self.exit_event, self.async_npc_game,)))

        for t in self.threads:
            t.start()

    def tearDown(self):
        # Deactivate all active games
        for game in self.games:
            if game.is_active():
                game.deactivate()

        # Signal all game loop threads to exit
        self.exit_event.set()
        
        # Join all game loop threads
        for t in self.threads:
            t.join()

    def test_initialization(self):
        self.assertFalse(self.sync_game.is_ready())
        self.assertFalse(self.sync_game.is_active())
        self.assertFalse(self.sync_game.is_full())
        self.assertTrue(self.sync_game.is_empty())

        self.sync_game.add_player("player_one")
        self.assertFalse(self.sync_game.is_ready())
        self.assertFalse(self.sync_game.is_active())
        self.assertFalse(self.sync_game.is_full())
        self.assertFalse(self.sync_game.is_empty())

        self.sync_game.add_player("player_two")
        self.assertTrue(self.sync_game.is_ready())
        self.assertFalse(self.sync_game.is_active())
        self.assertTrue(self.sync_game.is_full())
        self.assertFalse(self.sync_game.is_empty())

    def test_idle_async_game_loop(self):
        self.async_game.add_player("player_one")
        self.async_game.add_player("player_two")
        self.async_game.activate()

        time.sleep(3)
        self.async_game.deactivate()

    def test_several_turns_sync(self):
        players = ["player_one", "player_two"]
        for player in players:
            self.sync_game.add_player(player)
        self.sync_game.activate()

        expected_board = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,1,2,0,0,0]
        boards = []

        successfully_enqueued = True
        uncessfully_enqueued = False
        num_turns = 4

        for i in range(num_turns):
            boards.append(self.sync_game.board)
            # Alternate who is the active player each turn
            active_player_idx = i % len(players)
            active_player_id = players[active_player_idx]
            inactive_player_idx = 1 - active_player_idx
            inactive_player_id = players[inactive_player_idx]
            player_action = i
            
            # State consistency check
            self.assertEqual(active_player_id, self.sync_game.active_player_id)
            self.assertEqual(inactive_player_id, self.sync_game.inactive_player_id)
            self.assertEqual(active_player_idx, self.sync_game.active_player_idx)
            self.assertEqual(inactive_player_idx, self.sync_game.inactive_player_idx)

            # Ensure player whose turn it is can successfully enqueue action
            successfully_enqueued = self.sync_game.enqueue_action(active_player_id, player_action) and successfully_enqueued

            # Ensure inactive player can't enqueue actions
            uncessfully_enqueued = self.sync_game.enqueue_action(inactive_player_id, player_action) or uncessfully_enqueued

            # Ensure active player can't enqueue multiple actions
            uncessfully_enqueued = self.sync_game.enqueue_action(active_player_id, player_action) or uncessfully_enqueued

            status = self.sync_game.tick()
            self.assertEqual(status, Game.Status.ACTIVE)

        self.assertTrue(successfully_enqueued)
        self.assertFalse(uncessfully_enqueued)
        self.assertEqual(self.sync_game.board, expected_board)
        self.sync_game.deactivate()

        return boards
        
    def test_several_turns_async(self):
        players = ["player_one", "player_two"]
        for player in players:
            self.async_game.add_player(player)
        self.async_game.activate()

        boards = []
        expected_board = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,1,2,0,0,0]

        successfully_enqueued = True
        unsuccessfully_enqueued = False
        num_turns = 4
        for curr_turn in range(num_turns):
            boards.append(self.async_game.board)
            # Alternate who is the active player each turn
            active_player_idx = curr_turn % len(players)
            active_player_id = players[active_player_idx]
            inactive_player_idx = 1 - active_player_idx
            inactive_player_id = players[inactive_player_idx]
            player_action = curr_turn
            
            # Turn state validation
            self.assertEqual(active_player_id, self.async_game.active_player_id)
            self.assertEqual(inactive_player_id, self.async_game.inactive_player_id)
            self.assertEqual(active_player_idx, self.async_game.active_player_idx)
            self.assertEqual(inactive_player_idx, self.async_game.inactive_player_idx)

            # Grab game lock to ensure tick can't happen between these calls
            with self.async_game.lock:
                # Ensure inactive player can't enqueue actions
                unsuccessfully_enqueued = self.async_game.enqueue_action(inactive_player_id, player_action) or unsuccessfully_enqueued

                # Ensure player whose turn it is can successfully enqueue action
                successfully_enqueued = self.async_game.enqueue_action(active_player_id, player_action) and successfully_enqueued

                # Ensure inactive player still can't enqueue actions
                unsuccessfully_enqueued = self.async_game.enqueue_action(inactive_player_id, player_action) or unsuccessfully_enqueued

                # Ensure active player can't enqueue multiple actions
                unsuccessfully_enqueued = self.async_game.enqueue_action(active_player_id, player_action) or unsuccessfully_enqueued

            # Busy-wait for turn to be propogated
            while self.async_game.curr_turn_number <= curr_turn:
                time.sleep(1/self.async_game.fps)

        self.assertEqual(self.async_game.board, expected_board)
        self.async_game.deactivate()
        self.assertTrue(successfully_enqueued)
        self.assertFalse(unsuccessfully_enqueued)

        return boards

    def test_several_turns_ai_async(self):
        player_id = "player_one"
        self.async_npc_game.add_player(player_id)
        self.async_npc_game.activate()

        expected_board = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,2,0,0,0,0,0,0,1,2,0,0,0,0,0]

        num_turns = 4
        successfully_enqueued = True
        unsuccessfully_enqueued = False
        for curr_turn in range(num_turns):
            with self.async_npc_game.lock:
                player_action = curr_turn // 2
                we_are_active = self.async_npc_game.active_player_id == player_id
                if we_are_active:
                    successfully_enqueued = self.async_npc_game.enqueue_action(player_id, player_action) and successfully_enqueued
                
                unsuccessfully_enqueued = self.async_npc_game.enqueue_action(player_id, player_action) or unsuccessfully_enqueued

            # Busy-wait for turn to be propogated
            while self.async_npc_game.curr_turn_number <= curr_turn:
                time.sleep(1/self.async_npc_game.fps)

        self.assertTrue(successfully_enqueued)
        self.assertFalse(unsuccessfully_enqueued)
        num_nonzeros_expected = sum([int(el != 0) for el in expected_board])
        num_nonzeros_actual = sum([int(el != 0) for el in self.async_npc_game.board])
        self.assertEqual(num_nonzeros_expected, num_nonzeros_actual)
        self.assertEqual(self.async_npc_game.board, expected_board)
        self.async_npc_game.deactivate()

    def test_several_turns_ai_sync(self):
        player_id = "player_one"
        self.sync_npc_game.add_player(player_id)
        self.sync_npc_game.activate()

        expected_board = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,2,0,0,0,0,0,0,1,2,0,0,0,0,0]

        num_turns = 2
        curr_turn = 0
        successfully_enqueued = True
        unsuccessfully_enqueued = False
        while curr_turn < num_turns:
            player_action = curr_turn
            we_are_active = self.sync_npc_game.active_player_id == player_id
            if we_are_active:
                successfully_enqueued = self.sync_npc_game.enqueue_action(player_id, player_action) and successfully_enqueued
                curr_turn += 1
            
            unsuccessfully_enqueued = self.sync_npc_game.enqueue_action(player_id, player_action) or unsuccessfully_enqueued
            self.sync_npc_game.tick()

        self.assertTrue(successfully_enqueued)
        self.assertFalse(unsuccessfully_enqueued)
        self.assertEqual(self.sync_npc_game.board, expected_board)
        self.sync_npc_game.deactivate()

    def test_invalid_actions(self):
        players = ["player_one", "player_two"]
        for player in players:
            self.sync_game.add_player(player)
        self.sync_game.activate()

        valid_actions = [0, "0", self.sync_game.config['columns']-1, str(self.sync_game.config['columns']-1)]
        invalid_actions = [-1, self.sync_game.config['columns'], "-2", str(self.sync_game.config['columns'])]

        successfully_enqueued = True
        unsuccessfully_enqueued = False
        for i in range(len(valid_actions)):
            # Alternate who is the active player each turn
            active_player_idx = i % len(players)
            active_player_id = players[active_player_idx]
            valid_action = valid_actions[i]
            invalid_action = invalid_actions[i]

            unsuccessfully_enqueued = self.sync_game.enqueue_action(active_player_id, invalid_action) or unsuccessfully_enqueued
            successfully_enqueued = self.sync_game.enqueue_action(active_player_id, valid_action) and successfully_enqueued
            self.sync_game.tick()

        self.assertTrue(successfully_enqueued)
        self.assertFalse(unsuccessfully_enqueued)

        for _ in range(self.sync_game.config['rows'] - 2):
            self.sync_game.enqueue_action(self.sync_game.active_player_id, 0)
            self.sync_game.tick()

        self.assertFalse(self.sync_game.enqueue_action(self.sync_game.active_player_id, 0))
        self.assertTrue(self.sync_game.enqueue_action(self.sync_game.active_player_id, 1))
    
    def test_json_serializability(self):
        players = ["player_one", "player_two"]
        for player in players:
            self.sync_game.add_player(player)
        self.sync_game.activate()

        obj = self.sync_game.to_json()
        self.assert_JSON_serializable(obj)

    def test_full_game_sync(self):
        players = ["player_one", "player_two"]
        for player in players:
            self.sync_game.add_player(player)
        self.sync_game.activate()

        # Play one game to completion
        self._play_game_sync(7)

        # Verify reset correctly detected
        status = self.sync_game.tick()
        self.assertEqual(status, self.sync_game.Status.RESET)

        # Play second game to completion
        _, statuses = self._play_game_sync(7)

        # Verify end game correctly detected
        self.assertEqual(statuses[-1], self.sync_game.Status.DONE)

    def test_turn_timeout_sync(self):
        self.sync_game.turn_timeout = 0.2
        players = ["mario", "luigi"]
        for player in players:
            self.sync_game.add_player(player)
        self.sync_game.activate()

        # Play a couple turns
        boards, statuses = self._play_game_sync(num_turns=2)
        for status in statuses:
            self.assertEqual(self.sync_game.Status.ACTIVE, status)

        # Ensure active player has switched
        boards.append(self.sync_game.board)
        active_player = self.sync_game.active_player_id
        time.sleep(self.sync_game.turn_timeout * 5)
        self.sync_game.tick()
        self.assertNotEqual(active_player, self.sync_game.active_player_id)


        # Play a few more turns to make sure everything works
        new_boards, statuses = self._play_game_sync(num_turns=2)
        boards.extend(new_boards)
        for status in statuses:
            self.assertEqual(self.sync_game.Status.ACTIVE, status)

        expected_board = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,1,0,0,0,0,0,1,2,0,1,0,0,0]
        self.assertEqual(self.sync_game.board, expected_board)
        self.sync_game.deactivate()

        return boards

    def test_full_game_even_length_sync(self):
        players = ["player_one", "player_two"]
        for player in players:
            self.sync_game.add_player(player)
        self.sync_game.activate()

        def turn_func(turn_num):
            if turn_num == 6:
                return 3
            else:
                return turn_num % 2

        # Play one game to completion
        self._play_game_sync(turn_func=turn_func, num_turns=8)

        # Verify reset correctly detected
        status = self.sync_game.tick()
        self.assertEqual(status, self.sync_game.Status.RESET)

        # Play second game to completion
        _, statuses = self._play_game_sync(7)

        # Verify end game correctly detected
        self.assertEqual(statuses[-1], self.sync_game.Status.DONE)

    def assert_JSON_serializable(self, obj):
        serialized = False
        try:
            json.dumps(obj)
            serialized = True
        except Exception:
            pass
        self.assertTrue(serialized)

    def _play_game_sync(self, num_turns=7, turn_func=None):
        if not turn_func:
            turn_func = lambda i : i % 2
        boards = []
        successfully_enqueued = True
        unsuccessfully_enqueued = False
        statuses = []
        for curr_turn in range(num_turns):
            boards.append(self.sync_game.board)
            player_action = turn_func(curr_turn)
            unsuccessfully_enqueued = self.sync_game.enqueue_action(self.sync_game.inactive_player_id, player_action) or unsuccessfully_enqueued
            successfully_enqueued = self.sync_game.enqueue_action(self.sync_game.active_player_id, player_action) and successfully_enqueued
            unsuccessfully_enqueued = self.sync_game.enqueue_action(self.sync_game.inactive_player_id, player_action) or unsuccessfully_enqueued
            unsuccessfully_enqueued = self.sync_game.enqueue_action(self.sync_game.active_player_id, player_action) or unsuccessfully_enqueued
            status = self.sync_game.tick()
            statuses.append(status)

        self.assertTrue(successfully_enqueued)
        self.assertFalse(unsuccessfully_enqueued)
        
        return boards, statuses

class TestConnectFourPsiturk(TestConnectFourGame):

    TestCls = ConnectFourPsiturkTestWrapper

    def test_several_turns_sync(self):
        expected_boards = super(TestConnectFourPsiturk, self).test_several_turns_sync()

        # Verify data correctness
        expected_0_actions = [0, None, 2, None]
        expected_1_actions = [None, 1, None, 3]
        expected_winner = -1
        data = self.sync_game.get_data()['trajectory']
        self._verify_data_correctness(data, expected_boards, expected_winner, expected_0_actions, expected_1_actions)
        
    def test_several_turns_async(self):
        expected_boards = super(TestConnectFourPsiturk, self).test_several_turns_async()

        # Verify data correctness
        expected_0_actions = [0, None, 2, None]
        expected_1_actions = [None, 1, None, 3]
        expected_winner = -1
        data = self.async_game.get_data()['trajectory']
        self._verify_data_correctness(data, expected_boards, expected_winner, expected_0_actions, expected_1_actions)

    def test_turn_timeout_sync(self):
        expected_boards = super(TestConnectFourPsiturk, self).test_turn_timeout_sync()
        
        # Verify data correctness
        expected_0_actions = [0, None, 3, None, 1]
        expected_1_actions = [None, 1, None, 0, None]
        timeout_timesteps = [2]
        expected_winner = -1
        data = self.sync_game.get_data()['trajectory']
        self._verify_data_correctness(data, expected_boards, expected_winner, expected_0_actions, expected_1_actions, timeout_timesteps)

    def test_full_game_sync(self):
        players = ["player_one", "player_two"]
        for player in players:
            self.sync_game.add_player(player)
        self.sync_game.activate()

        # Play one game to completion
        expected_boards, _ = self._play_game_sync(num_turns=7)

        # Verify reset correctly detected
        status = self.sync_game.tick()
        self.assertEqual(status, self.sync_game.Status.RESET)

        # Verify data correctness
        expected_0_actions = [0, None, 0, None, 0, None, 0]
        expected_1_actions = [None, 1, None, 1, None, 1, None]
        expected_winner = 0
        data = self.sync_game.get_data()['trajectory']
        first_trial_id = self._verify_data_correctness(data, expected_boards, expected_winner, expected_0_actions, expected_1_actions)

        # Play second game to completion
        expected_boards, statuses = self._play_game_sync(num_turns=7)

        # Verify end game correctly detected
        self.assertEqual(statuses[-1], self.sync_game.Status.DONE)

        # Verify data correctness
        expected_0_actions = [0, None, 0, None, 0, None, 0]
        expected_1_actions = [None, 1, None, 1, None, 1, None]
        expected_winner = 0
        data = self.sync_game.get_data()['trajectory']
        second_trial_id = self._verify_data_correctness(data, expected_boards, expected_winner, expected_0_actions, expected_1_actions)
        self.assertNotEqual(first_trial_id, second_trial_id)
    
    def _verify_data_correctness(self, data, expected_boards, expected_winner, expected_0_actions, expected_1_actions, timeout_timesteps=[]):
        # Basic param verification
        assert len(expected_0_actions) == len(expected_1_actions) and len(expected_1_actions) == len(expected_boards)
        assert expected_winner in [-1, 0, 1]

        # Ensure data is json serializable
        self.assert_JSON_serializable(data)

        # Ensure every timestep captured
        num_turns = len(expected_boards)
        self.assertEqual(len(data), num_turns)

        # Schema correctness
        expected_keys = set(["state", "joint_action", "time_elapsed", "curr_turn_time", "curr_turn_number", "was_turn_timeout", "trial_id", "player_0_id", "player_1_id", "player_0_is_human", "player_1_is_human", "player_0_played_this_turn", "player_1_played_this_turn", "player_0_reward", "player_1_reward"])
        actual_keys = set(data[0].keys())
        self.assertEqual(expected_keys, actual_keys)

        # Ensure proper timeouts were logged
        timeouts = [transition['was_turn_timeout'] for transition in data]
        for timestep in timeout_timesteps:
            self.assertTrue(timeouts[timestep])

        # Ensure correct player won
        expected_reward_0 = 1
        expected_reward_1 = -1
        if expected_winner == -1:
            expected_reward_0 = expected_reward_1 = 0
        elif expected_winner == 1:
            expected_reward_0, expected_reward_1 = expected_reward_1, expected_reward_0
        
        self.assertEqual(data[-1]['player_0_reward'], expected_reward_0)
        self.assertEqual(data[-1]['player_1_reward'], expected_reward_1)
        self.assertEqual(sum([trans['player_0_reward'] for trans in data]), expected_reward_0)
        self.assertEqual(sum([trans['player_1_reward'] for trans in data]), expected_reward_1)

        # Ensure metadata correct
        trial_id = data[0]['trial_id']
        self.assertTrue(all([trans['trial_id'] == trial_id for trans in data]))
        self.assertTrue(all([trans['player_0_is_human'] for trans in data]))
        self.assertTrue(all([trans['player_1_is_human'] for trans in data]))

        even_turns = []
        odd_turns = []
        for i in range(num_turns):
            if i%2 == 0:
                even_turns.append(data[i])
            else:
                odd_turns.append(data[i])
        self.assertTrue(all([trans['player_0_played_this_turn'] for trans in even_turns]))
        self.assertTrue(all([not trans['player_1_played_this_turn'] for trans in even_turns]))
        self.assertTrue(all([trans['player_1_played_this_turn'] for trans in odd_turns]))
        self.assertTrue(all([not trans['player_0_played_this_turn'] for trans in odd_turns]))

        # Ensure actions correctly logged
        actual_0_actions = [json.loads(trans['joint_action'])[0] for trans in data]
        actual_1_actions = [json.loads(trans['joint_action'])[1] for trans in data]
        self.assertEqual(expected_0_actions, actual_0_actions)
        self.assertEqual(expected_1_actions, actual_1_actions)

        def _parse_board(state):
            state = json.loads(state)
            p0_obs, p1_obs = state[0]['observation'], state[1]['observation']

            return p0_obs['board'] if 'board' in p0_obs else p1_obs['board']

        actual_boards = [_parse_board(trans['state']) for trans in data]

        self.assertEqual(len(expected_boards), len(actual_boards))

        for i, board_tuple in enumerate(zip(expected_boards, actual_boards)):
            expected_board, actual_board = board_tuple
            self.assertEqual(expected_board, actual_board)

        return trial_id


if __name__ == '__main__':
    unittest.main()