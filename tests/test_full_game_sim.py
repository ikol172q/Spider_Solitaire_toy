"""完整蜘蛛纸牌游戏模拟测试 - 验证游戏逻辑端到端正确"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spider_solitaire.game.game_state import GameState
from spider_solitaire.game.card import Card


class TestInitialGameState(unittest.TestCase):

    def test_easy_104_cards(self):
        game = GameState('easy')
        game.new_game('easy')
        total = sum(len(c) for c in game.columns) + len(game.stock)
        self.assertEqual(total, 104)

    def test_medium_104_cards(self):
        game = GameState('medium')
        game.new_game('medium')
        total = sum(len(c) for c in game.columns) + len(game.stock)
        self.assertEqual(total, 104)

    def test_hard_104_cards(self):
        game = GameState('hard')
        game.new_game('hard')
        total = sum(len(c) for c in game.columns) + len(game.stock)
        self.assertEqual(total, 104)

    def test_column_counts(self):
        game = GameState('easy')
        game.new_game('easy')
        for i in range(4):
            self.assertEqual(len(game.columns[i]), 6)
        for i in range(4, 10):
            self.assertEqual(len(game.columns[i]), 5)

    def test_stock_50_cards(self):
        game = GameState('easy')
        game.new_game('easy')
        self.assertEqual(len(game.stock), 50)

    def test_top_cards_face_up(self):
        game = GameState('easy')
        game.new_game('easy')
        for i, col in enumerate(game.columns):
            self.assertTrue(col[-1].face_up, f"Column {i} top card should be face up")

    def test_score_starts_500(self):
        game = GameState('easy')
        game.new_game('easy')
        self.assertEqual(game.score, 500)


class TestScoreFormula(unittest.TestCase):

    def test_move_deducts_1(self):
        game = GameState('easy')
        game.new_game('easy')
        initial = game.score
        # Find any valid move
        moves = game.get_all_possible_moves()
        if moves:
            f, ci, t, _ = moves[0]
            game.move_cards(f, ci, t)
            self.assertEqual(game.score, initial - 1)

    def test_complete_adds_100(self):
        game = GameState('easy')
        game.columns = [[Card('spade', 13 - i, face_up=True) for i in range(13)]] + [[] for _ in range(9)]
        game.score = 400
        game.check_complete(0)
        self.assertEqual(game.score, 500)
        self.assertEqual(len(game.completed), 1)

    def test_deal_deducts_1(self):
        game = GameState('easy')
        game.new_game('easy')
        initial = game.score
        game.deal_row()
        self.assertEqual(game.score, initial - 1)


class TestUndoRestoresState(unittest.TestCase):

    def test_undo_restores_columns(self):
        game = GameState('easy')
        game.new_game('easy')
        moves = game.get_all_possible_moves()
        if moves:
            cols_before = [len(c) for c in game.columns]
            score_before = game.score
            f, ci, t, _ = moves[0]
            game.move_cards(f, ci, t)
            game.undo()
            cols_after = [len(c) for c in game.columns]
            self.assertEqual(cols_before, cols_after)
            self.assertEqual(game.score, score_before)

    def test_undo_after_deal(self):
        game = GameState('easy')
        game.new_game('easy')
        stock_before = len(game.stock)
        game.deal_row()
        self.assertEqual(len(game.stock), stock_before - 10)
        game.undo()
        self.assertEqual(len(game.stock), stock_before)


class TestMoveToEmptyColumn(unittest.TestCase):

    def test_any_card_to_empty(self):
        game = GameState('easy')
        game.columns = [
            [],
            [Card('spade', 5, face_up=True)],
        ] + [[Card('spade', 1, face_up=True)] for _ in range(8)]
        game.history = []
        result = game.move_cards(1, 0, 0)
        self.assertTrue(result)
        self.assertEqual(len(game.columns[0]), 1)

    def test_sequence_to_empty(self):
        game = GameState('easy')
        game.columns = [
            [],
            [Card('spade', 6, face_up=True), Card('spade', 5, face_up=True)],
        ] + [[Card('spade', 1, face_up=True)] for _ in range(8)]
        game.history = []
        result = game.move_cards(1, 0, 0)
        self.assertTrue(result)
        self.assertEqual(len(game.columns[0]), 2)


class TestDealRowCompletion(unittest.TestCase):

    def test_deal_triggers_check_complete(self):
        """发牌后如果形成K→A应自动收集"""
        game = GameState('easy')
        # 构造：列0有K到2的12张牌
        game.columns = [
            [Card('spade', 13 - i, face_up=True) for i in range(12)],  # K到2
        ] + [[Card('spade', 7, face_up=True)] for _ in range(9)]
        # stock.pop() 取最后一个元素，col_idx=0 第一个 pop
        # 所以 stock[-1] 被发到 col 0，需要 A♠ 在最后
        game.stock = [Card('spade', 3, face_up=False) for _ in range(9)] + [Card('spade', 1, face_up=False)]
        game.completed = []
        game.score = 400
        game.history = []
        game.deal_row()
        # A♠ 被发到列0，形成K→A，自动收集
        self.assertEqual(len(game.completed), 1, "Should auto-complete K→A after deal")


class TestGameSimulation(unittest.TestCase):

    def _simulate(self, difficulty='easy', max_iters=500):
        game = GameState(difficulty)
        game.new_game(difficulty)
        for _ in range(max_iters):
            if game.is_won():
                break
            moves = game.get_all_possible_moves()
            if moves:
                f, ci, t, _ = moves[0]
                game.move_cards(f, ci, t)
            elif len(game.stock) >= 10 and all(game.columns):
                game.deal_row()
            else:
                break
        return game

    def test_easy_simulation_no_crash(self):
        game = self._simulate('easy')
        self.assertGreaterEqual(len(game.completed), 0)

    def test_medium_simulation_no_crash(self):
        game = self._simulate('medium')
        self.assertGreaterEqual(len(game.completed), 0)

    def test_hard_simulation_no_crash(self):
        game = self._simulate('hard')
        self.assertGreaterEqual(len(game.completed), 0)

    def test_card_conservation(self):
        """模拟过程中卡牌总数始终为104"""
        game = GameState('easy')
        game.new_game('easy')
        for _ in range(100):
            total = sum(len(c) for c in game.columns) + len(game.stock) + len(game.completed) * 13
            self.assertEqual(total, 104, f"Card conservation violated: {total}")
            moves = game.get_all_possible_moves()
            if moves:
                f, ci, t, _ = moves[0]
                game.move_cards(f, ci, t)
            elif len(game.stock) >= 10 and all(game.columns):
                game.deal_row()
            else:
                break


if __name__ == '__main__':
    unittest.main()
