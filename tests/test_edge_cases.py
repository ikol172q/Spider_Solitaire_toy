"""边界情况和回归测试

覆盖开发过程中遇到的 Bug，防止回归：
- 空列规则（任何牌可放入空列，不只是 K）
- 发牌前空列检查
- RANK_NAMES 显示正确性
- 序列化/反序列化完整性
- 胜利判定精确性
"""

import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import Counter
from spider_solitaire.game.card import Card, SUITS, RANK_NAMES
from spider_solitaire.game.deck import create_deck, ALL_SUITS
from spider_solitaire.game.rules import is_valid_move, can_deal, is_complete_sequence, is_movable_sequence
from spider_solitaire.game.game_state import GameState


class TestEmptyColumnRule(unittest.TestCase):
    """回归测试：空列规则（曾经只允许 K，修正为任何牌）"""

    def test_ace_on_empty(self):
        self.assertTrue(is_valid_move(Card('spade', 1, True), []))

    def test_five_on_empty(self):
        self.assertTrue(is_valid_move(Card('heart', 5, True), []))

    def test_king_on_empty(self):
        self.assertTrue(is_valid_move(Card('club', 13, True), []))

    def test_sequence_on_empty(self):
        """序列也可以移到空列"""
        seq = [Card('spade', 5, True), Card('spade', 4, True)]
        self.assertTrue(is_valid_move(seq, []))

    def test_single_card_sequence_on_empty(self):
        seq = [Card('diamond', 7, True)]
        self.assertTrue(is_valid_move(seq, []))


class TestDealWithEmptyColumns(unittest.TestCase):
    """回归测试：有空列时不能发牌"""

    def test_one_empty_column(self):
        cols = [[Card('spade', 1)] for _ in range(9)] + [[]]
        self.assertFalse(can_deal(cols))

    def test_all_empty(self):
        cols = [[] for _ in range(10)]
        self.assertFalse(can_deal(cols))

    def test_first_column_empty(self):
        cols = [[]] + [[Card('spade', 1)] for _ in range(9)]
        self.assertFalse(can_deal(cols))

    def test_middle_column_empty(self):
        cols = [[Card('spade', 1)] for _ in range(10)]
        cols[5] = []
        self.assertFalse(can_deal(cols))

    def test_all_filled(self):
        cols = [[Card('spade', 1)] for _ in range(10)]
        self.assertTrue(can_deal(cols))


class TestRankNames(unittest.TestCase):
    """RANK_NAMES 显示字符串正确性"""

    def test_ace_display(self):
        self.assertEqual(RANK_NAMES[1], 'A')

    def test_jack_display(self):
        """回归：J 曾经渲染像 I，确认数据层是 'J'"""
        self.assertEqual(RANK_NAMES[11], 'J')

    def test_queen_display(self):
        self.assertEqual(RANK_NAMES[12], 'Q')

    def test_king_display(self):
        self.assertEqual(RANK_NAMES[13], 'K')

    def test_number_cards(self):
        for i in range(2, 11):
            self.assertEqual(RANK_NAMES[i], str(i))

    def test_all_ranks_present(self):
        """1-13 全部有映射"""
        for i in range(1, 14):
            self.assertIn(i, RANK_NAMES)


class TestSuits(unittest.TestCase):
    """花色符号正确性"""

    def test_four_suits(self):
        self.assertEqual(len(SUITS), 4)
        self.assertIn('spade', SUITS)
        self.assertIn('heart', SUITS)
        self.assertIn('diamond', SUITS)
        self.assertIn('club', SUITS)

    def test_suit_symbols(self):
        self.assertEqual(SUITS['spade'], '♠')
        self.assertEqual(SUITS['heart'], '♥')
        self.assertEqual(SUITS['diamond'], '♦')
        self.assertEqual(SUITS['club'], '♣')


class TestMoveValidation(unittest.TestCase):
    """移动验证的边界情况"""

    def test_move_to_same_rank_fails(self):
        """同级别不能叠放"""
        target = [Card('spade', 5, True)]
        self.assertFalse(is_valid_move(Card('heart', 5, True), target))

    def test_move_higher_rank_fails(self):
        """高级别不能放到低级别上"""
        target = [Card('spade', 5, True)]
        self.assertFalse(is_valid_move(Card('heart', 6, True), target))

    def test_move_two_lower_fails(self):
        """差 2 不能放"""
        target = [Card('spade', 10, True)]
        self.assertFalse(is_valid_move(Card('heart', 8, True), target))

    def test_cross_suit_move_valid(self):
        """不同花色只要差 1 就能放"""
        target = [Card('spade', 10, True)]
        self.assertTrue(is_valid_move(Card('heart', 9, True), target))

    def test_ace_on_two(self):
        target = [Card('spade', 2, True)]
        self.assertTrue(is_valid_move(Card('spade', 1, True), target))

    def test_nothing_on_ace(self):
        """A 上不能再放牌（没有 rank 0）"""
        target = [Card('spade', 1, True)]
        # rank 0 不存在，所以任何牌都不能放在 A 上
        for r in range(1, 14):
            self.assertFalse(is_valid_move(Card('spade', r, True), target))


class TestMovableSequence(unittest.TestCase):
    """可移动序列边界"""

    def test_single_card_is_movable(self):
        self.assertTrue(is_movable_sequence([Card('spade', 5, True)]))

    def test_face_down_cards_in_sequence(self):
        """暗牌也能通过 is_movable_sequence（该函数不检查 face_up）"""
        seq = [Card('spade', 5, False), Card('spade', 4, False)]
        self.assertTrue(is_movable_sequence(seq))

    def test_full_13_card_sequence(self):
        seq = [Card('spade', 13 - i, True) for i in range(13)]
        self.assertTrue(is_movable_sequence(seq))


class TestCompleteSequence(unittest.TestCase):
    """完整序列边界"""

    def test_12_cards_not_complete(self):
        seq = [Card('spade', 13 - i, True) for i in range(12)]
        self.assertFalse(is_complete_sequence(seq))

    def test_14_cards_not_complete(self):
        seq = [Card('spade', 13 - i, True) for i in range(13)]
        seq.append(Card('spade', 1, True))  # extra A
        self.assertFalse(is_complete_sequence(seq))

    def test_reverse_order_not_complete(self):
        """A→K 顺序（反的）不算完整"""
        seq = [Card('spade', i + 1, True) for i in range(13)]
        self.assertFalse(is_complete_sequence(seq))


class TestGameStateSerialization(unittest.TestCase):
    """序列化完整性回归测试"""

    def test_roundtrip_preserves_difficulty(self):
        for diff in ('easy', 'medium', 'hard'):
            gs = GameState()
            gs.new_game(diff)
            restored = GameState.from_dict(gs.to_dict())
            self.assertEqual(restored.difficulty, diff)

    def test_roundtrip_preserves_score_and_moves(self):
        gs = GameState()
        gs.new_game('easy')
        gs.score = 42
        gs.moves = 99
        restored = GameState.from_dict(gs.to_dict())
        self.assertEqual(restored.score, 42)
        self.assertEqual(restored.moves, 99)

    def test_roundtrip_preserves_card_face_up(self):
        gs = GameState()
        gs.new_game('easy')
        data = gs.to_dict()
        restored = GameState.from_dict(data)
        for ci in range(10):
            for j in range(len(gs.columns[ci])):
                self.assertEqual(
                    gs.columns[ci][j].face_up,
                    restored.columns[ci][j].face_up
                )

    def test_roundtrip_preserves_stock(self):
        gs = GameState()
        gs.new_game('easy')
        restored = GameState.from_dict(gs.to_dict())
        self.assertEqual(len(gs.stock), len(restored.stock))


class TestWinCondition(unittest.TestCase):
    """胜利条件精确性"""

    def test_7_sets_not_won(self):
        gs = GameState()
        gs.new_game('easy')
        seq = [Card('spade', 13 - i, True) for i in range(13)]
        gs.completed = [seq] * 7
        self.assertFalse(gs.is_won())

    def test_8_sets_won(self):
        gs = GameState()
        gs.new_game('easy')
        seq = [Card('spade', 13 - i, True) for i in range(13)]
        gs.completed = [seq] * 8
        self.assertTrue(gs.is_won())

    def test_0_sets_not_won(self):
        gs = GameState()
        gs.new_game('easy')
        self.assertFalse(gs.is_won())


class TestDeckRandomSuits(unittest.TestCase):
    """花色随机选择测试"""

    def test_easy_always_one_suit(self):
        """初级：始终只有1种花色"""
        for _ in range(20):
            deck = create_deck('easy')
            suits_used = set(c.suit for c in deck)
            self.assertEqual(len(suits_used), 1)
            self.assertEqual(len(deck), 104)

    def test_easy_suit_is_valid(self):
        """初级选出的花色必须是四种之一"""
        for _ in range(20):
            deck = create_deck('easy')
            suit = next(iter(set(c.suit for c in deck)))
            self.assertIn(suit, ALL_SUITS)

    def test_easy_can_choose_non_spade(self):
        """初级：多次创建，应该有机会选到非黑桃花色（概率极高）"""
        suits_seen = set()
        for _ in range(100):
            deck = create_deck('easy')
            suits_seen.update(c.suit for c in deck)
        # 100次中至少出现过2种不同的花色（4选1，不出现第二种的概率 = (1/4)^99 ≈ 0）
        self.assertGreater(len(suits_seen), 1)

    def test_medium_always_two_suits(self):
        """中级：始终只有2种花色，各52张"""
        for _ in range(20):
            deck = create_deck('medium')
            counts = Counter(c.suit for c in deck)
            self.assertEqual(len(counts), 2)
            for cnt in counts.values():
                self.assertEqual(cnt, 52)

    def test_medium_can_choose_different_pairs(self):
        """中级：多次创建，应该出现不同的花色组合"""
        combos_seen = set()
        for _ in range(100):
            deck = create_deck('medium')
            combo = frozenset(c.suit for c in deck)
            combos_seen.add(combo)
        self.assertGreater(len(combos_seen), 1)

    def test_hard_always_four_suits(self):
        """高级：始终4种花色，各26张"""
        deck = create_deck('hard')
        counts = Counter(c.suit for c in deck)
        self.assertEqual(len(counts), 4)
        for cnt in counts.values():
            self.assertEqual(cnt, 26)

    def test_each_suit_has_full_ranks(self):
        """每种花色应该包含完整的 A-K"""
        for diff in ('easy', 'medium', 'hard'):
            deck = create_deck(diff)
            suits_used = set(c.suit for c in deck)
            for s in suits_used:
                ranks = sorted(c.rank for c in deck if c.suit == s)
                # 每种花色的 rank 集合应该覆盖 1-13
                rank_set = set(ranks)
                self.assertEqual(rank_set, set(range(1, 14)),
                                 f'{diff} 难度下 {s} 花色缺少某些 rank')


if __name__ == '__main__':
    unittest.main()
