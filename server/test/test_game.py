from math import exp
import unittest, sys, os, time, random, json
from threading import Thread, Event, Lock

_file_dir = os.path.dirname(os.path.abspath(__file__))
_server_dir = os.path.abspath(os.path.join(_file_dir, '..'))
sys.path.append(_server_dir)
from game.c4 import ConnectFourGame
from game.base import Game, NPC
import game as game_module

class DummyC4NPC(NPC):
    def action(self, _):
        return 0, None

class ConnectFourGameTestWrapper(ConnectFourGame):
    def _get_policy(self, npc_id, idx):
        return DummyC4NPC()

class TestConnectFourGame(unittest.TestCase):

    def setUp(self):
        game_module._configure(100, '.', 60)
        self.async_game = ConnectFourGameTestWrapper(debug=False, fps=30)
        self.sync_game = ConnectFourGameTestWrapper(debug=False, num_games=2)
        self.sync_npc_game = ConnectFourGameTestWrapper(debug=False, playerZero="my_npc")
        self.async_npc_game = ConnectFourGameTestWrapper(debug=False, playerZero="my_npc")
        self.games = [self.async_game, self.sync_game, self.sync_npc_game, self.async_npc_game]
        self.exit_event = Event()

        self.threads = []
        self.threads.append(Thread(target=self._game_loop, args=(self.async_game,)))
        self.threads.append(Thread(target=self._game_loop, args=(self.async_npc_game,)))

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

        successfully_enqueued = True
        uncessfully_enqueued = False
        num_turns = 4

        for i in range(num_turns):
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
        
    def test_several_turns_async(self):
        players = ["player_one", "player_two"]
        for player in players:
            self.async_game.add_player(player)
        self.async_game.activate()

        expected_board = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,1,2,0,0,0]

        successfully_enqueued = True
        unsuccessfully_enqueued = False
        num_turns = 4
        for curr_turn in range(num_turns):
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
                # Ensure player whose turn it is can successfully enqueue action
                successfully_enqueued = self.async_game.enqueue_action(active_player_id, player_action) and successfully_enqueued

                # Ensure inactive player can't enqueue actions
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
        serializable = False

        try:
            json_str = json.dumps(obj)
            serializable = True
        except Exception as e:
            raise e
            serializable = False

        self.assertTrue(serializable)

    def test_full_game_sync(self):
        players = ["player_one", "player_two"]
        for player in players:
            self.sync_game.add_player(player)
        self.sync_game.activate()

        # Play one game to completion
        num_turns = 7
        successfully_enqueued = True
        for curr_turn in range(num_turns):
            player_action = curr_turn % 2
            successfully_enqueued = self.sync_game.enqueue_action(self.sync_game.active_player_id, player_action) and successfully_enqueued
            self.assertEqual(self.sync_game.tick(), self.sync_game.Status.ACTIVE)

        # Verify reset correctly detected
        status = self.sync_game.tick()
        self.assertTrue(successfully_enqueued)
        self.assertEqual(status, self.sync_game.Status.RESET)

        # Play second game to completion
        for curr_turn in range(num_turns):
            last_turn = curr_turn == num_turns - 1
            player_action = curr_turn % 2
            successfully_enqueued = self.sync_game.enqueue_action(self.sync_game.active_player_id, player_action) and successfully_enqueued
            status = self.sync_game.tick()
            
            if not last_turn:
                self.assertEqual(self.sync_game.tick(), self.sync_game.Status.ACTIVE)

        # Verify end game correctly detected
        self.assertTrue(successfully_enqueued)
        self.assertEqual(status, self.sync_game.Status.DONE)

    def _game_loop(self, game):
        while not self.exit_event.is_set() and not game.is_active():
            time.sleep(0.5)
        
        fps = min(game.fps, game_module.static.MAX_FPS)
        status = Game.Status.ACTIVE
        while not self.exit_event.is_set() and status != Game.Status.DONE and status != Game.Status.INACTIVE:
            with game.lock:
                status = game.tick()
            if status == Game.Status.RESET:
                with game.lock:
                    _ = game.get_data()
                time.sleep(game.reset_timeou1000)
            time.sleep(1/fps)


if __name__ == '__main__':
    unittest.main()