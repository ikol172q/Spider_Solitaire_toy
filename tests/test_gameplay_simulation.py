"""游戏模拟测试 — 用 AI 自动玩牌，验证游戏逻辑的正确性和健壮性

这不是单元测试，而是集成测试/压力测试：
- 随机启动游戏，AI 尝试所有合法移动
- 跑几百局，检查是否会崩溃、状态是否始终合法
- 验证不变量：总牌数始终 = 104，分数变化合理，etc.
"""

import unittest
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spider_solitaire.game.card import Card
from spider_solitaire.game.game_state import GameState
from spider_solitaire.game.rules import is_movable_sequence, can_deal


# ============================================================
#  辅助函数
# ============================================================

def count_all_cards(gs):
    """统计游戏中所有牌的总数"""
    total = 0
    for col in gs.columns:
        total += len(col)
    total += len(gs.stock)
    for seq in gs.completed:
        total += len(seq)
    return total


def verify_invariants(test_case, gs, label=''):
    """验证游戏状态的不变量"""
    prefix = f'[{label}] ' if label else ''

    # 1. 总牌数始终 = 104
    total = count_all_cards(gs)
    test_case.assertEqual(total, 104,
                          f'{prefix}总牌数应该是 104，实际是 {total}')

    # 2. 恰好 10 列
    test_case.assertEqual(len(gs.columns), 10,
                          f'{prefix}应该有 10 列')

    # 3. 每列最顶上的牌（如果有）必须是正面朝上
    for i, col in enumerate(gs.columns):
        if col:
            test_case.assertTrue(col[-1].face_up,
                                 f'{prefix}列 {i} 顶牌应该正面朝上')

    # 4. 每列中，正面朝上的牌必须在正面朝下的牌之上（不能 face_up 下面有 face_down）
    for i, col in enumerate(gs.columns):
        seen_face_up = False
        for j, card in enumerate(col):
            if card.face_up:
                seen_face_up = True
            elif seen_face_up:
                test_case.fail(
                    f'{prefix}列 {i} 位置 {j}: 暗牌出现在亮牌之后')

    # 5. completed 中的每组必须是 13 张
    for k, seq in enumerate(gs.completed):
        test_case.assertEqual(len(seq), 13,
                              f'{prefix}completed[{k}] 应该有 13 张牌')

    # 6. score 不应该是负无穷（合理性检查）
    test_case.assertGreater(gs.score, -10000,
                            f'{prefix}分数异常: {gs.score}')

    # 7. moves >= 0
    test_case.assertGreaterEqual(gs.moves, 0,
                                 f'{prefix}步数不应为负')

    # 8. stock 的牌数必须是 10 的倍数
    test_case.assertEqual(len(gs.stock) % 10, 0,
                          f'{prefix}stock 牌数应该是 10 的倍数，实际 {len(gs.stock)}')


def find_all_legal_moves(gs):
    """找出当前状态的所有合法移动

    返回 [(from_col, card_index, to_col), ...]
    """
    moves = []
    for from_col in range(10):
        col = gs.columns[from_col]
        if not col:
            continue
        # 找到最长的可移动序列起点
        for card_idx in range(len(col)):
            if not col[card_idx].face_up:
                continue
            seq = col[card_idx:]
            if not is_movable_sequence(seq):
                continue
            # 尝试移到每个目标列
            for to_col in range(10):
                if to_col == from_col:
                    continue
                if gs.can_move(from_col, card_idx, to_col):
                    moves.append((from_col, card_idx, to_col))
    return moves


def play_one_game(gs, max_steps=500, seed=None):
    """AI 自动玩一局游戏

    策略：
    1. 优先移动能形成同花色序列的牌
    2. 其次随机选一个合法移动
    3. 没有移动时尝试发牌
    4. 发牌也不行就结束

    返回:
        dict: {steps, won, completed_sets, final_score, stuck}
    """
    if seed is not None:
        random.seed(seed)

    steps = 0
    stuck_counter = 0

    while steps < max_steps:
        moves = find_all_legal_moves(gs)

        if moves:
            stuck_counter = 0
            # 简单策略：优先同花色堆叠
            best = None
            for m in moves:
                from_col, card_idx, to_col = m
                moving_card = gs.columns[from_col][card_idx]
                target_col = gs.columns[to_col]
                if target_col and target_col[-1].suit == moving_card.suit:
                    best = m
                    break

            if best is None:
                best = random.choice(moves)

            result = gs.move_cards(*best)
            assert result, f"move_cards 返回 False，但 can_move 返回了 True: {best}"
            steps += 1

            if gs.is_won():
                return {
                    'steps': steps, 'won': True,
                    'completed_sets': len(gs.completed),
                    'final_score': gs.score, 'stuck': False
                }
        else:
            # 没有合法移动 → 尝试发牌
            if gs.stock and can_deal(gs.columns):
                gs.deal_row()
                steps += 1
                stuck_counter = 0
            else:
                stuck_counter += 1
                if stuck_counter > 1:
                    return {
                        'steps': steps, 'won': False,
                        'completed_sets': len(gs.completed),
                        'final_score': gs.score, 'stuck': True
                    }

    return {
        'steps': steps, 'won': False,
        'completed_sets': len(gs.completed),
        'final_score': gs.score, 'stuck': False
    }


# ============================================================
#  测试类
# ============================================================

class TestGameInvariants(unittest.TestCase):
    """验证游戏不变量在各种操作后始终成立"""

    def test_new_game_invariants(self):
        """新游戏开始后不变量成立"""
        for diff in ('easy', 'medium', 'hard'):
            gs = GameState()
            gs.new_game(diff)
            verify_invariants(self, gs, f'new_game({diff})')

    def test_invariants_after_deal(self):
        """发牌后不变量成立"""
        gs = GameState()
        gs.new_game('easy')
        gs.deal_row()
        verify_invariants(self, gs, 'after deal_row')

    def test_invariants_after_multiple_deals(self):
        """连续发 5 次牌（把 stock 发完）"""
        gs = GameState()
        gs.new_game('easy')
        for i in range(5):
            result = gs.deal_row()
            self.assertTrue(result, f'第 {i+1} 次发牌应该成功')
            verify_invariants(self, gs, f'deal #{i+1}')
        # stock 应该空了
        self.assertEqual(len(gs.stock), 0)
        # 第 6 次应该失败
        self.assertFalse(gs.deal_row())

    def test_invariants_after_move(self):
        """移动后不变量成立"""
        gs = GameState()
        gs.new_game('easy')
        moves = find_all_legal_moves(gs)
        if moves:
            gs.move_cards(*moves[0])
            verify_invariants(self, gs, 'after move')

    def test_invariants_after_undo(self):
        """undo 后不变量成立"""
        gs = GameState()
        gs.new_game('easy')
        moves = find_all_legal_moves(gs)
        if moves:
            gs.move_cards(*moves[0])
            gs.undo()
            verify_invariants(self, gs, 'after undo')

    def test_invariants_after_complete(self):
        """手动构造完成序列，完成后不变量成立"""
        gs = GameState()
        gs.new_game('easy')
        # 把列 0 原有牌放到 stock 尾部（保持总数 104）
        suit = gs.columns[0][0].suit
        old_cards = gs.columns[0][:]
        gs.columns[0] = [Card(suit, 13 - i, face_up=True) for i in range(13)]
        # 补偿：把多出来的牌从 stock 中移除相应数量
        diff = len(gs.columns[0]) - len(old_cards)  # 13-6=7
        gs.stock = gs.stock[diff:]  # 从 stock 丢弃 7 张保持总数
        self.assertEqual(count_all_cards(gs), 104)

        gs.check_complete(0)
        self.assertEqual(len(gs.completed), 1)
        # 总牌数不变
        self.assertEqual(count_all_cards(gs), 104)


class TestScoreAccounting(unittest.TestCase):
    """分数和步数计算的精确性"""

    def test_score_decreases_on_move(self):
        gs = GameState()
        gs.new_game('easy')
        initial_score = gs.score
        moves = find_all_legal_moves(gs)
        if moves:
            gs.move_cards(*moves[0])
            self.assertEqual(gs.score, initial_score - 1)

    def test_score_decreases_on_deal(self):
        gs = GameState()
        gs.new_game('easy')
        initial_score = gs.score
        gs.deal_row()
        self.assertEqual(gs.score, initial_score - 1)

    def test_score_increases_on_complete(self):
        gs = GameState()
        gs.new_game('easy')
        suit = gs.columns[0][0].suit
        gs.columns[0] = [Card(suit, 13 - i, face_up=True) for i in range(13)]
        initial_score = gs.score
        gs.check_complete(0)
        self.assertEqual(gs.score, initial_score + 100)

    def test_moves_counter_accurate(self):
        """多次操作后步数精确"""
        gs = GameState()
        gs.new_game('easy')
        self.assertEqual(gs.moves, 0)

        op_count = 0
        # 发一次牌
        gs.deal_row()
        op_count += 1
        self.assertEqual(gs.moves, op_count)

        # 尝试几次移动
        for _ in range(5):
            moves = find_all_legal_moves(gs)
            if moves:
                gs.move_cards(*moves[0])
                op_count += 1
        self.assertEqual(gs.moves, op_count)

    def test_undo_restores_score_and_moves(self):
        gs = GameState()
        gs.new_game('easy')
        initial_score = gs.score
        initial_moves = gs.moves

        moves = find_all_legal_moves(gs)
        if moves:
            gs.move_cards(*moves[0])
            self.assertNotEqual(gs.score, initial_score)
            gs.undo()
            self.assertEqual(gs.score, initial_score)
            self.assertEqual(gs.moves, initial_moves)


class TestUndoCompleteness(unittest.TestCase):
    """undo 的完整性 — 多次操作后全部撤销，应恢复到初始状态"""

    def test_undo_chain(self):
        gs = GameState()
        gs.new_game('easy')

        # 保存初始状态快照
        initial_columns = [[c.to_dict() for c in col] for col in gs.columns]
        initial_stock = [c.to_dict() for c in gs.stock]
        initial_score = gs.score

        # 做若干次操作
        ops = 0
        gs.deal_row()
        ops += 1
        for _ in range(10):
            moves = find_all_legal_moves(gs)
            if moves:
                gs.move_cards(*moves[0])
                ops += 1

        # 全部撤销
        for _ in range(ops):
            gs.undo()

        # 验证恢复到初始状态
        restored_columns = [[c.to_dict() for c in col] for col in gs.columns]
        restored_stock = [c.to_dict() for c in gs.stock]
        self.assertEqual(initial_columns, restored_columns)
        self.assertEqual(initial_stock, restored_stock)
        self.assertEqual(initial_score, gs.score)


class TestUpdateElapsedTime(unittest.TestCase):
    """update_elapsed_time 测试"""

    def test_elapsed_time_updates(self):
        gs = GameState()
        gs.new_game('easy')
        gs.start_time = 1000.0
        # 模拟当前时间
        import unittest.mock
        with unittest.mock.patch('spider_solitaire.game.game_state.time') as mock_time:
            mock_time.time.return_value = 1042.0
            gs.update_elapsed_time()
        self.assertEqual(gs.elapsed_time, 42)

    def test_elapsed_time_no_start(self):
        """start_time 为 None 时不崩溃"""
        gs = GameState()
        gs.start_time = None
        gs.update_elapsed_time()
        self.assertEqual(gs.elapsed_time, 0)


class TestSameColumnMove(unittest.TestCase):
    """同列移动应该被拒绝"""

    def test_move_to_same_column(self):
        gs = GameState()
        gs.new_game('easy')
        self.assertFalse(gs.move_cards(0, len(gs.columns[0]) - 1, 0))

    def test_can_move_same_column(self):
        gs = GameState()
        gs.new_game('easy')
        self.assertFalse(gs.can_move(0, len(gs.columns[0]) - 1, 0))


class TestStockDepletion(unittest.TestCase):
    """stock 用完后的行为"""

    def test_deal_with_empty_stock(self):
        gs = GameState()
        gs.new_game('easy')
        gs.stock = []
        self.assertFalse(gs.deal_row())

    def test_deal_with_exactly_10(self):
        gs = GameState()
        gs.new_game('easy')
        gs.stock = [Card('spade', r + 1, face_up=False) for r in range(10)]
        result = gs.deal_row()
        self.assertTrue(result)
        self.assertEqual(len(gs.stock), 0)


class TestFlipTopCard(unittest.TestCase):
    """翻牌边界"""

    def test_flip_empty_column(self):
        """空列翻牌不崩溃"""
        gs = GameState()
        gs.new_game('easy')
        gs.columns[0] = []
        gs.flip_top_card(0)  # 不应该抛异常

    def test_flip_already_face_up(self):
        """已经正面朝上的牌翻牌无变化"""
        gs = GameState()
        gs.new_game('easy')
        gs.columns[0] = [Card('spade', 5, face_up=True)]
        gs.flip_top_card(0)
        self.assertTrue(gs.columns[0][-1].face_up)


# ============================================================
#  模拟游戏（压力测试）
# ============================================================

class TestGameplaySimulation(unittest.TestCase):
    """AI 自动玩多局游戏，检查是否会崩溃"""

    def _run_games(self, difficulty, num_games):
        """跑多局游戏并验证不变量"""
        crashes = []
        for i in range(num_games):
            gs = GameState()
            gs.new_game(difficulty)
            try:
                verify_invariants(self, gs, f'game {i} start')
                result = play_one_game(gs, max_steps=300, seed=i)
                verify_invariants(self, gs, f'game {i} end')
            except Exception as e:
                crashes.append((i, str(e)))

        self.assertEqual(len(crashes), 0,
                         f'{len(crashes)}/{num_games} 局崩溃:\n' +
                         '\n'.join(f'  game {i}: {e}' for i, e in crashes[:5]))

    def test_easy_100_games(self):
        """初级 100 局不崩溃"""
        self._run_games('easy', 100)

    def test_medium_100_games(self):
        """中级 100 局不崩溃"""
        self._run_games('medium', 100)

    def test_hard_100_games(self):
        """高级 100 局不崩溃"""
        self._run_games('hard', 100)


class TestGameplayStats(unittest.TestCase):
    """模拟游戏的统计合理性检查"""

    def test_easy_games_no_crash(self):
        """初级 50 局游戏，跟踪完成情况（不要求一定完成序列，AI 策略简单）"""
        completed_counts = []
        for i in range(50):
            gs = GameState()
            gs.new_game('easy')
            result = play_one_game(gs, max_steps=500, seed=i + 1000)
            completed_counts.append(result['completed_sets'])
            # 关键：不崩溃，且不变量成立
            verify_invariants(self, gs, f'easy game {i}')

        total_completed = sum(completed_counts)
        # 仅打印统计，不断言完成数（简单 AI 可能做不到）
        print(f'\n  [easy 50局] 总完成序列: {total_completed}, '
              f'最高单局: {max(completed_counts)}')

    def test_score_always_consistent(self):
        """分数 = 500 - moves + 100 * completed_sets"""
        for i in range(30):
            gs = GameState()
            gs.new_game('easy')
            play_one_game(gs, max_steps=200, seed=i + 2000)
            expected = 500 - gs.moves + 100 * len(gs.completed)
            self.assertEqual(gs.score, expected,
                             f'game {i}: score {gs.score} != expected {expected} '
                             f'(moves={gs.moves}, completed={len(gs.completed)})')


if __name__ == '__main__':
    unittest.main()
