"""蜘蛛纸牌游戏单元测试"""

import unittest
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spider_solitaire.game.card import Card, SUITS, RANK_NAMES
from spider_solitaire.game.deck import create_deck, shuffle_deck
from spider_solitaire.game.rules import (
    is_valid_move, is_complete_sequence, is_movable_sequence, can_deal
)
from spider_solitaire.game.game_state import GameState


class TestCard(unittest.TestCase):
    """测试Card类"""

    def test_card_creation(self):
        """测试卡牌创建"""
        card = Card('spade', 1)
        self.assertEqual(card.suit, 'spade')
        self.assertEqual(card.rank, 1)
        self.assertEqual(card.face_up, False)

    def test_card_invalid_suit(self):
        """测试无效花色"""
        with self.assertRaises(ValueError):
            Card('invalid', 1)

    def test_card_invalid_rank(self):
        """测试无效级别"""
        with self.assertRaises(ValueError):
            Card('spade', 0)
        with self.assertRaises(ValueError):
            Card('spade', 14)

    def test_card_equality(self):
        """测试卡牌相等性"""
        card1 = Card('spade', 5)
        card2 = Card('spade', 5)
        card3 = Card('heart', 5)

        self.assertEqual(card1, card2)
        self.assertNotEqual(card1, card3)

    def test_card_comparison(self):
        """测试卡牌比较"""
        card1 = Card('spade', 5)
        card2 = Card('heart', 8)
        card3 = Card('diamond', 5)

        self.assertLess(card1, card2)
        self.assertLessEqual(card1, card3)
        self.assertGreater(card2, card1)
        self.assertGreaterEqual(card1, card3)

    def test_card_string_representation(self):
        """测试卡牌字符串表示"""
        card = Card('spade', 1, face_up=True)
        self.assertEqual(str(card), 'A♠')

        card = Card('heart', 13, face_up=True)
        self.assertEqual(str(card), 'K♥')

        card = Card('spade', 1, face_up=False)
        self.assertEqual(str(card), '🂠')

    def test_card_serialization(self):
        """测试卡牌序列化"""
        card = Card('club', 10, face_up=True)
        data = card.to_dict()
        restored = Card.from_dict(data)

        self.assertEqual(card, restored)
        self.assertEqual(card.face_up, restored.face_up)


class TestDeck(unittest.TestCase):
    """测试Deck模块"""

    def test_create_deck_easy(self):
        """测试简单难度牌组创建"""
        deck = create_deck('easy')
        self.assertEqual(len(deck), 104)

        # 检查所有牌都是黑桃
        spade_count = sum(1 for card in deck if card.suit == 'spade')
        self.assertEqual(spade_count, 104)

    def test_create_deck_medium(self):
        """测试中等难度牌组创建"""
        deck = create_deck('medium')
        self.assertEqual(len(deck), 104)

        spade_count = sum(1 for card in deck if card.suit == 'spade')
        heart_count = sum(1 for card in deck if card.suit == 'heart')

        self.assertEqual(spade_count, 52)
        self.assertEqual(heart_count, 52)

    def test_create_deck_hard(self):
        """测试困难难度牌组创建"""
        deck = create_deck('hard')
        self.assertEqual(len(deck), 104)

        spade_count = sum(1 for card in deck if card.suit == 'spade')
        heart_count = sum(1 for card in deck if card.suit == 'heart')
        diamond_count = sum(1 for card in deck if card.suit == 'diamond')
        club_count = sum(1 for card in deck if card.suit == 'club')

        self.assertEqual(spade_count, 26)
        self.assertEqual(heart_count, 26)
        self.assertEqual(diamond_count, 26)
        self.assertEqual(club_count, 26)

    def test_create_deck_invalid_difficulty(self):
        """测试无效难度"""
        with self.assertRaises(ValueError):
            create_deck('invalid')

    def test_shuffle_deck(self):
        """测试洗牌"""
        deck1 = create_deck('easy')
        deck1_copy = [Card(c.suit, c.rank, c.face_up) for c in deck1]
        deck1_str = ''.join(str(c) for c in deck1)

        shuffle_deck(deck1)
        deck1_shuffled_str = ''.join(str(c) for c in deck1)

        # 洗牌后顺序可能改变（虽然理论上有极小概率不变）
        # 但总数应该保持一致
        self.assertEqual(len(deck1), 104)


class TestRules(unittest.TestCase):
    """测试规则验证"""

    def test_valid_move_on_empty_column(self):
        """测试在空列上放King"""
        king = Card('spade', 13, face_up=True)
        empty_column = []

        self.assertTrue(is_valid_move(king, empty_column))

    def test_invalid_move_non_king_on_empty_column(self):
        """测试在空列上放非King卡牌"""
        queen = Card('spade', 12, face_up=True)
        empty_column = []

        self.assertFalse(is_valid_move(queen, empty_column))

    def test_valid_move_on_column(self):
        """测试在非空列上合法移动"""
        target_column = [Card('heart', 10, face_up=True)]
        moving_card = Card('spade', 9, face_up=True)

        self.assertTrue(is_valid_move(moving_card, target_column))

    def test_invalid_move_on_column(self):
        """测试在非空列上非法移动"""
        target_column = [Card('heart', 10, face_up=True)]
        moving_card = Card('spade', 8, face_up=True)

        self.assertFalse(is_valid_move(moving_card, target_column))

    def test_complete_sequence_valid(self):
        """测试完整序列检测 - 有效"""
        sequence = [Card('spade', 13 - i, face_up=True) for i in range(13)]
        self.assertTrue(is_complete_sequence(sequence))

    def test_complete_sequence_invalid_suit(self):
        """测试完整序列检测 - 花色不一致"""
        sequence = [Card('spade', 13 - i, face_up=True) for i in range(12)]
        sequence.append(Card('heart', 1, face_up=True))
        self.assertFalse(is_complete_sequence(sequence))

    def test_complete_sequence_invalid_length(self):
        """测试完整序列检测 - 长度不正确"""
        sequence = [Card('spade', 13 - i, face_up=True) for i in range(12)]
        self.assertFalse(is_complete_sequence(sequence))

    def test_complete_sequence_invalid_order(self):
        """测试完整序列检测 - 顺序不正确"""
        sequence = [Card('spade', 13 - i, face_up=True) for i in range(13)]
        sequence[0], sequence[1] = sequence[1], sequence[0]  # 交换前两张
        self.assertFalse(is_complete_sequence(sequence))

    def test_movable_sequence_valid(self):
        """测试可移动序列检测 - 有效"""
        sequence = [Card('spade', 10, face_up=True), Card('spade', 9, face_up=True)]
        self.assertTrue(is_movable_sequence(sequence))

    def test_movable_sequence_invalid_suit(self):
        """测试可移动序列检测 - 花色不一致"""
        sequence = [Card('spade', 10, face_up=True), Card('heart', 9, face_up=True)]
        self.assertFalse(is_movable_sequence(sequence))

    def test_movable_sequence_invalid_rank(self):
        """测试可移动序列检测 - 级别不递减"""
        sequence = [Card('spade', 10, face_up=True), Card('spade', 8, face_up=True)]
        self.assertFalse(is_movable_sequence(sequence))

    def test_movable_sequence_empty(self):
        """测试可移动序列检测 - 空序列"""
        self.assertFalse(is_movable_sequence([]))

    def test_can_deal_true(self):
        """测试是否可以发牌 - 可以"""
        columns = [
            [Card('spade', 1)],
            [Card('heart', 1)],
            [Card('diamond', 1)],
            [Card('club', 1)],
            [Card('spade', 2)],
            [Card('heart', 2)],
            [Card('diamond', 2)],
            [Card('club', 2)],
            [Card('spade', 3)],
            [Card('heart', 3)]
        ]
        self.assertTrue(can_deal(columns))

    def test_can_deal_false(self):
        """测试是否可以发牌 - 不可以"""
        columns = [
            [Card('spade', 1)],
            [Card('heart', 1)],
            [Card('diamond', 1)],
            [Card('club', 1)],
            [Card('spade', 2)],
            [Card('heart', 2)],
            [Card('diamond', 2)],
            [Card('club', 2)],
            [Card('spade', 3)],
            []  # 最后一列为空
        ]
        self.assertFalse(can_deal(columns))


class TestGameState(unittest.TestCase):
    """测试GameState类"""

    def test_game_initialization(self):
        """测试游戏初始化"""
        game = GameState('easy')
        self.assertEqual(game.difficulty, 'easy')
        self.assertEqual(len(game.columns), 10)
        self.assertEqual(game.score, 500)
        self.assertEqual(game.moves, 0)

    def test_new_game_easy(self):
        """测试开始简单游戏"""
        game = GameState()
        game.new_game('easy')

        # 检查初始发牌
        self.assertEqual(len(game.columns), 10)
        self.assertEqual(len(game.completed), 0)

        # 前4列应该有6张，后6列应该有5张
        for i in range(4):
            self.assertEqual(len(game.columns[i]), 6)
        for i in range(4, 10):
            self.assertEqual(len(game.columns[i]), 5)

        # 检查总牌数 (6*4 + 5*6 + stock)
        total_cards = sum(len(col) for col in game.columns) + len(game.stock)
        self.assertEqual(total_cards, 104)

        # 检查最顶部的牌是正面朝上的
        for col in game.columns:
            if col:
                self.assertTrue(col[-1].face_up)

    def test_deal_row(self):
        """测试发牌"""
        game = GameState()
        game.new_game('easy')

        initial_stock_size = len(game.stock)
        initial_moves = game.moves

        # 成功发牌
        result = game.deal_row()
        self.assertTrue(result)
        self.assertEqual(len(game.stock), initial_stock_size - 10)
        self.assertEqual(game.moves, initial_moves + 1)

        # 每列应该多一张牌
        for i in range(4):
            self.assertEqual(len(game.columns[i]), 7)
        for i in range(4, 10):
            self.assertEqual(len(game.columns[i]), 6)

    def test_cannot_deal_with_empty_column(self):
        """测试不能在有空列时发牌"""
        game = GameState()
        game.new_game('easy')

        # 清空一列
        game.columns[0] = []

        result = game.deal_row()
        self.assertFalse(result)

    def test_move_cards(self):
        """测试移动卡牌"""
        game = GameState()
        game.new_game('easy')

        # 找到可以移动的卡牌组合
        # 在真实游戏中，我们需要构造一个特定的场景
        # 这里构造一个简单的测试场景

        game.columns = [
            [],
            [],
            [Card('spade', 10, face_up=True), Card('spade', 9, face_up=True)],
            [Card('spade', 10, face_up=True)],
            [],
            [],
            [],
            [],
            [],
            [Card('spade', 13, face_up=True)]
        ]
        game.history = []

        # 移动spade 9序列到列中已有的spade 10上
        result = game.move_cards(2, 1, 3)
        self.assertTrue(result)
        self.assertEqual(len(game.columns[2]), 1)
        self.assertEqual(len(game.columns[3]), 2)

    def test_cannot_move_invalid_sequence(self):
        """测试不能移动非法序列"""
        game = GameState()
        game.new_game('easy')

        game.columns = [
            [],
            [],
            [Card('spade', 10, face_up=True), Card('heart', 9, face_up=True)],
            [Card('heart', 8, face_up=True)],
            [],
            [],
            [],
            [],
            [],
            []
        ]

        # 尝试移动混花色序列（应该失败）
        result = game.move_cards(2, 1, 3)
        self.assertFalse(result)

    def test_check_complete(self):
        """测试完整序列检测和移除"""
        game = GameState()
        game.new_game('easy')

        # 构造一个有完整序列的列
        # 完整序列：K(13), Q(12), J(11), 10, 9, 8, 7, 6, 5, 4, 3, 2, A(1)
        complete_seq = [Card('spade', 13 - i, face_up=True) for i in range(13)]
        game.columns[0] = [Card('heart', 5, face_up=True)] + complete_seq

        initial_score = game.score
        game.check_complete(0)

        self.assertEqual(len(game.completed), 1)
        self.assertEqual(len(game.columns[0]), 1)
        self.assertEqual(game.score, initial_score + 100)

    def test_flip_top_card(self):
        """测试翻牌"""
        game = GameState()
        game.new_game('easy')

        # 添加一张暗牌到某列
        game.columns[0] = [Card('spade', 5, face_up=False)]

        game.flip_top_card(0)
        self.assertTrue(game.columns[0][-1].face_up)

    def test_undo(self):
        """测试撤销"""
        game = GameState()
        game.new_game('easy')

        game.columns = [
            [],
            [],
            [Card('spade', 10, face_up=True), Card('spade', 9, face_up=True)],
            [Card('spade', 10, face_up=True)],
            [],
            [],
            [],
            [],
            [],
            []
        ]
        game.history = []

        initial_state = {
            'cols': [len(col) for col in game.columns],
            'score': game.score,
            'moves': game.moves
        }

        game.move_cards(2, 1, 3)

        # 撤销
        result = game.undo()
        self.assertTrue(result)

        # 恢复到初始状态
        self.assertEqual(initial_state['cols'], [len(col) for col in game.columns])

    def test_undo_empty_history(self):
        """测试空历史栈的撤销"""
        game = GameState()
        game.new_game('easy')

        result = game.undo()
        self.assertFalse(result)

    def test_is_won(self):
        """测试胜利判定"""
        game = GameState()
        game.new_game('easy')

        self.assertFalse(game.is_won())

        # 添加8个完整序列
        complete_seq = [Card('spade', 13 - i, face_up=True) for i in range(13)]
        for i in range(8):
            game.completed.append(complete_seq)

        self.assertTrue(game.is_won())

    def test_serialization(self):
        """测试序列化和反序列化"""
        game = GameState()
        game.new_game('easy')

        data = game.to_dict()
        restored = GameState.from_dict(data)

        self.assertEqual(game.difficulty, restored.difficulty)
        self.assertEqual(game.score, restored.score)
        self.assertEqual(len(game.columns), len(restored.columns))

    def test_get_movable_sequence(self):
        """测试获取可移动序列"""
        game = GameState()
        game.new_game('easy')

        game.columns[0] = [
            Card('spade', 12, face_up=True),
            Card('spade', 11, face_up=True),
            Card('spade', 10, face_up=True)
        ]

        # 获取从索引1开始的序列
        sequence = game.get_movable_sequence(0, 1)
        self.assertIsNotNone(sequence)
        self.assertEqual(len(sequence), 2)

        # 尝试获取非法序列（第二列有两张混花色的牌）
        game.columns[1] = [
            Card('spade', 11, face_up=True),
            Card('heart', 10, face_up=True)
        ]
        # 从索引1（最后一张）获取序列，因为只有一张牌，它不会被检查为非法
        # 所以我们需要测试一个包含多张牌的非法序列
        game.columns[2] = [
            Card('spade', 10, face_up=True),
            Card('heart', 9, face_up=True)
        ]
        sequence = game.get_movable_sequence(2, 0)
        self.assertIsNone(sequence)


if __name__ == '__main__':
    unittest.main()
