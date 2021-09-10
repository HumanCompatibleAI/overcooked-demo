from math import exp
import unittest, sys, os, time, random
from threading import Thread, Event

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
        self.async_game = ConnectFourGame(debug=False)
        self.sync_game = ConnectFourGame(debug=False)
        self.sync_npc_game = ConnectFourGameTestWrapper(debug=False, playerZero="my_npc")
        self.exit_event = Event()
        self.t = Thread(target=self._game_loop, args=())
        self.t.start()

    def tearDown(self):
        if self.async_game.is_active():
            self.async_game.deactivate()
        if self.sync_game.is_active():
            self.sync_game.deactivate()
        if self.sync_npc_game.is_active():
            self.sync_npc_game.deactivate()
        self.exit_event.set()
        self.t.join()

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

        time_between_actions_in_seconds = 5e-1
        successfully_enqueued = True
        num_turns = 4
        for i in range(num_turns):
            active_player_idx = i % len(players)
            active_player_id = players[active_player_idx]
            inactive_player_idx = 1 - active_player_idx
            inactive_player_id = players[inactive_player_idx]
            player_action = i
            
            self.assertEqual(active_player_id, self.async_game.active_player_id)
            self.assertEqual(inactive_player_id, self.async_game.inactive_player_id)
            self.assertEqual(active_player_idx, self.async_game.active_player_idx)
            self.assertEqual(inactive_player_idx, self.async_game.inactive_player_idx)
            successfully_enqueued = self.async_game.enqueue_action(active_player_id, player_action) and successfully_enqueued
            time.sleep(time_between_actions_in_seconds)

        self.assertEqual(self.async_game.board, expected_board)
        self.async_game.deactivate()
        self.assertTrue(successfully_enqueued)

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
        num_nonzeros_expected = sum([int(el != 0) for el in expected_board])
        num_nonzeros_actual = sum([int(el != 0) for el in self.sync_npc_game.board])
        self.assertEqual(num_nonzeros_expected, num_nonzeros_actual)
        self.assertEqual(self.sync_npc_game.board, expected_board)
        self.sync_npc_game.deactivate()

    def _game_loop(self):
        while not self.exit_event.is_set() and not self.async_game.is_active():
            time.sleep(0.5)
        
        fps = min(self.async_game.fps, game_module.static.MAX_FPS)
        status = Game.Status.ACTIVE
        while not self.exit_event.is_set() and status != Game.Status.DONE and status != Game.Status.INACTIVE:
            with self.async_game.lock:
                status = self.async_game.tick()
            if status == Game.Status.RESET:
                with self.async_game.lock:
                    _ = self.async_game.get_data()
                time.sleep(self.async_game.reset_timeou1000)
            time.sleep(1/fps)


if __name__ == '__main__':
    unittest.main()