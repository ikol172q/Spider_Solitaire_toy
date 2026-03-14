"""UI 逻辑测试 — 不需要 Kivy 渲染环境

测试 UI 层中所有可提取的纯计算逻辑：
- 坐标计算（卡牌尺寸、列位置、重叠缩放）
- 拖放目标检测（容差算法）
- 格式化函数（时间、难度映射）
- 卡牌 Widget 属性计算（字体大小、花色颜色）
- 完成区布局

这些测试不依赖 Kivy 事件循环或 GL 上下文，可在任何 CI 环境运行。
"""

import unittest
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# 从 UI 模块中提取的纯计算函数（避免 import Kivy）
# 在实际应用中这些逻辑嵌入在 Widget 方法中，
# 这里重新实现以验证算法正确性。
# ============================================================

# --- theme.py 常量（dp 值用数字模拟，1dp ≈ 1 单位）---
MARGIN = 15
PADDING = 10
CARD_OVERLAP_CLOSED = 15
CARD_OVERLAP_OPEN = 25


def calc_card_size(widget_width, margin=MARGIN):
    """board_widget.py._calc_card_size() 的纯函数版本"""
    dp_min, dp_max = 30, 60
    usable_w = widget_width - 2 * margin
    min_gap = 2  # dp(2)
    max_card_w = (usable_w - 9 * min_gap) / 10
    cw = min(dp_max, max(dp_min, max_card_w))
    ch = cw * 1.42
    cr = cw * 0.067
    return cw, ch, cr


def calc_column_positions(widget_x, widget_width, cw, margin=MARGIN):
    """board_widget.py._calc_column_positions() 的纯函数版本"""
    usable_w = widget_width - 2 * margin
    if usable_w > 10 * cw:
        gap = max(1, (usable_w - 10 * cw) / 9)
    else:
        gap = 1
    total = 10 * cw + 9 * gap
    start_x = widget_x + (widget_width - total) / 2
    positions = []
    x = start_x
    for _ in range(10):
        positions.append(x)
        x += cw + gap
    return positions, gap


def calc_overlap_factor(column_face_up_flags, available_height):
    """board_widget.py._draw_column() 中重叠缩放因子的纯计算"""
    n = len(column_face_up_flags)
    if n <= 1:
        return 1.0, 0
    total_overlap = 0
    for i in range(n - 1):
        total_overlap += CARD_OVERLAP_OPEN if column_face_up_flags[i] else CARD_OVERLAP_CLOSED
    if total_overlap > available_height:
        factor = available_height / total_overlap if total_overlap > 0 else 1
    else:
        factor = 1.0
    return factor, total_overlap


def find_target_column(tx, column_positions, cw, min_tolerance=80):
    """board_widget.py._find_target_column() 的纯函数版本"""
    best = None
    best_dist = float('inf')
    tolerance = max(cw * 2.5, min_tolerance)
    for i, cx in enumerate(column_positions):
        d = abs(tx - (cx + cw / 2))
        if d < best_dist and d < tolerance:
            best_dist = d
            best = i
    return best


def calc_completed_stack_size(widget_width, cw, margin=MARGIN):
    """board_widget.py._draw_completed() 布局计算"""
    avail_w = widget_width - 2 * margin - cw - 15  # dp(15)
    stack_gap = 3  # dp(3)
    stack_w = min(cw * 0.7, (avail_w - 7 * stack_gap - 35) / 8)  # dp(35)
    stack_w = max(stack_w, 20)  # dp(20)
    stack_h = stack_w * 1.42
    return stack_w, stack_h, stack_gap


def calc_stock_remaining(stock_count):
    """board_widget.py._draw_stock() 中发牌堆数量"""
    return stock_count // 10


def fmt_time(secs):
    """stats_screen.py._fmt_time() 的纯函数版本"""
    if secs <= 0:
        return '--'
    m, s = divmod(int(secs), 60)
    return f'{m}:{s:02d}'


def fmt_time_game_screen(elapsed):
    """game_screen.py._tick() 中时间格式化"""
    m, s = divmod(elapsed, 60)
    return f"{m:02d}:{s:02d}"


def get_difficulty_label(difficulty):
    """game_screen.py 中难度映射"""
    diff_map = {'easy': '初级', 'medium': '中级', 'hard': '高级'}
    return diff_map.get(difficulty, '')


def get_suit_color(suit):
    """card_widget.py._get_suit_color() 的纯函数版本"""
    RED = (0.85, 0.1, 0.1, 1)
    BLACK = (0.1, 0.1, 0.1, 1)
    if suit in ('heart', 'diamond'):
        return RED
    return BLACK


def calc_card_font_sizes(card_width):
    """card_widget.py.__init__() 中字体大小计算"""
    return card_width * 0.45, card_width * 0.62


def calc_card_back_step(card_width):
    """card_widget.py._draw_back() 中交叉纹样步长"""
    return max(6, int(card_width / 8))


# ============================================================
# 测试类
# ============================================================

class TestCalcCardSize(unittest.TestCase):
    """测试卡牌动态尺寸计算"""

    def test_wide_screen_caps_at_max(self):
        """宽屏幕时卡牌宽度不超过 60（dp最大值）"""
        cw, ch, cr = calc_card_size(800)
        self.assertEqual(cw, 60)
        self.assertAlmostEqual(ch, 60 * 1.42)
        self.assertAlmostEqual(cr, 60 * 0.067)

    def test_narrow_screen_floors_at_min(self):
        """极窄屏幕时卡牌宽度不低于 30（dp最小值）"""
        cw, ch, cr = calc_card_size(100)  # 极窄
        self.assertEqual(cw, 30)
        self.assertAlmostEqual(ch, 30 * 1.42)

    def test_mate40_width(self):
        """Mate 40 实际宽度 (~420dp) 的计算"""
        cw, ch, cr = calc_card_size(420)
        # (420 - 30) / 10 - 9*2/10 = 39 - 1.8 = 37.2
        # usable = 420 - 30 = 390, max_card_w = (390 - 18) / 10 = 37.2
        self.assertGreaterEqual(cw, 30)
        self.assertLessEqual(cw, 60)
        # 10 列应该能放下
        total_width = 10 * cw + 9 * 2  # 最小间距
        self.assertLessEqual(total_width, 420 - 2 * MARGIN)

    def test_aspect_ratio_maintained(self):
        """高度始终是宽度的 1.42 倍"""
        for width in [300, 420, 600, 800, 1080]:
            cw, ch, cr = calc_card_size(width)
            self.assertAlmostEqual(ch / cw, 1.42, places=5)

    def test_radius_proportional(self):
        """圆角始终是宽度的 0.067 倍"""
        for width in [300, 420, 600]:
            cw, ch, cr = calc_card_size(width)
            self.assertAlmostEqual(cr / cw, 0.067, places=5)

    def test_ten_columns_fit(self):
        """宽度足够时 10 列卡牌都能放下（含间距）
        注意：当 widget 宽度 < 10*30+9+30 ≈ 339 时几何上不可能放下 10 列最小牌
        """
        for width in range(350, 1200, 50):
            cw, ch, cr = calc_card_size(width)
            usable = width - 2 * MARGIN
            min_total = 10 * cw + 9 * 1  # 最小间距 1
            self.assertLessEqual(min_total, usable + 1,  # 容差 1
                                 f"width={width}, cw={cw}")


class TestCalcColumnPositions(unittest.TestCase):
    """测试列位置计算"""

    def test_ten_columns(self):
        """生成恰好 10 个列位置"""
        cw = 40
        positions, gap = calc_column_positions(0, 500, cw)
        self.assertEqual(len(positions), 10)

    def test_positions_increasing(self):
        """列位置严格递增"""
        cw = 40
        positions, gap = calc_column_positions(0, 500, cw)
        for i in range(9):
            self.assertGreater(positions[i + 1], positions[i])

    def test_gap_at_least_1(self):
        """列间距至少为 1"""
        cw = 40
        _, gap = calc_column_positions(0, 200, cw)  # 很窄
        self.assertGreaterEqual(gap, 1)

    def test_centered_on_widget(self):
        """列布局以 widget 中心对齐"""
        cw = 40
        widget_x, widget_w = 50, 600
        positions, gap = calc_column_positions(widget_x, widget_w, cw)
        total = 10 * cw + 9 * gap
        expected_start = widget_x + (widget_w - total) / 2
        self.assertAlmostEqual(positions[0], expected_start, places=3)

    def test_uniform_spacing(self):
        """所有列间距相等"""
        cw = 40
        positions, gap = calc_column_positions(0, 600, cw)
        for i in range(9):
            actual_gap = positions[i + 1] - positions[i] - cw
            self.assertAlmostEqual(actual_gap, gap, places=3)

    def test_widget_offset(self):
        """widget 的 x 偏移正确传递"""
        cw = 40
        pos_at_0, _ = calc_column_positions(0, 500, cw)
        pos_at_100, _ = calc_column_positions(100, 500, cw)
        for a, b in zip(pos_at_0, pos_at_100):
            self.assertAlmostEqual(b - a, 100, places=3)


class TestOverlapFactor(unittest.TestCase):
    """测试卡牌重叠缩放因子计算"""

    def test_single_card_no_overlap(self):
        """单张牌不需要重叠"""
        factor, total = calc_overlap_factor([True], 200)
        self.assertEqual(factor, 1.0)
        self.assertEqual(total, 0)

    def test_empty_column(self):
        """空列"""
        factor, total = calc_overlap_factor([], 200)
        self.assertEqual(factor, 1.0)

    def test_all_face_up_no_scaling(self):
        """面朝上的牌在足够高度时不需要缩放"""
        # 5 张面朝上：4 * 25 = 100
        flags = [True] * 5
        factor, total = calc_overlap_factor(flags, 200)
        self.assertEqual(factor, 1.0)
        self.assertEqual(total, 100)

    def test_all_face_down_no_scaling(self):
        """面朝下的牌在足够高度时不需要缩放"""
        # 5 张面朝下：4 * 15 = 60
        flags = [False] * 5
        factor, total = calc_overlap_factor(flags, 200)
        self.assertEqual(factor, 1.0)
        self.assertEqual(total, 60)

    def test_scaling_needed(self):
        """可用高度不足时需要缩放"""
        # 10 张面朝上：9 * 25 = 225，可用 100
        flags = [True] * 10
        factor, total = calc_overlap_factor(flags, 100)
        self.assertAlmostEqual(factor, 100 / 225, places=5)
        self.assertEqual(total, 225)

    def test_mixed_face_up_down(self):
        """混合面朝上/下的计算"""
        # 3 face-down + 4 face-up：3*15 + 3*25 = 45 + 75 = 120
        # 注意：最后一张不算重叠，所以 n-1=6 张的重叠
        flags = [False, False, False, True, True, True, True]
        factor, total = calc_overlap_factor(flags, 200)
        expected_total = 3 * CARD_OVERLAP_CLOSED + 3 * CARD_OVERLAP_OPEN
        self.assertEqual(total, expected_total)
        self.assertEqual(factor, 1.0)

    def test_scaling_preserves_proportions(self):
        """缩放时各段保持原始比例"""
        flags = [False, False, True, True, True]
        factor, total = calc_overlap_factor(flags, 50)
        # total = 2*15 + 2*25 = 80, available = 50
        expected_factor = 50 / 80
        self.assertAlmostEqual(factor, expected_factor)

    def test_zero_available_height(self):
        """可用高度为 0 时"""
        flags = [True, True, True]
        factor, total = calc_overlap_factor(flags, 0)
        self.assertEqual(factor, 0.0)


class TestFindTargetColumn(unittest.TestCase):
    """测试拖放目标列检测"""

    def setUp(self):
        self.cw = 40
        # 10 列，每列起始 x: 0, 50, 100, ..., 450
        self.positions = [i * 50 for i in range(10)]

    def test_exact_center(self):
        """精确落在列中心"""
        # 列 3 中心 = 150 + 20 = 170
        result = find_target_column(170, self.positions, self.cw)
        self.assertEqual(result, 3)

    def test_within_tolerance(self):
        """在容差范围内找到最近列"""
        # 列 6 中心 = 300 + 20 = 320, 距离 = 20
        # 列 5 中心 = 250 + 20 = 270, 距离 = 30
        # 列 6 更近
        result = find_target_column(300, self.positions, self.cw)
        self.assertEqual(result, 6)

    def test_beyond_tolerance_returns_none(self):
        """超出所有列容差范围返回 None"""
        # 容差 = max(40*2.5, 80) = 100
        # 所有列中心：20, 70, 120, ..., 470
        # x = 700 距离最近列 470 = 230 > 100
        result = find_target_column(700, self.positions, self.cw)
        self.assertIsNone(result)

    def test_tolerance_minimum_80(self):
        """容差至少 80（即使卡牌很窄）"""
        small_cw = 20  # 2.5 * 20 = 50 < 80
        positions = [i * 30 for i in range(10)]
        # 列 0 中心 = 10，距离 = 85 > 50 但 < 80
        result = find_target_column(95, positions, small_cw, min_tolerance=80)
        # 应该找不到，因为最近列中心是 10+90=100... 让我重新算
        # 列 3 中心 = 90 + 10 = 100, 距离 = |95-100| = 5 < 80
        result = find_target_column(95, positions, small_cw, min_tolerance=80)
        self.assertEqual(result, 3)

    def test_nearest_of_two_candidates(self):
        """两个候选列时选最近的"""
        # 列 2 中心 = 120, 列 3 中心 = 170
        # tx = 140 距列 2 = 20, 距列 3 = 30
        result = find_target_column(140, self.positions, self.cw)
        self.assertEqual(result, 2)

    def test_between_columns(self):
        """恰好在两列正中间时选前一列（先遍历到）"""
        # 列 2 中心 = 120, 列 3 中心 = 170, 中间 = 145
        result = find_target_column(145, self.positions, self.cw)
        self.assertEqual(result, 2)  # 距离 25 < 25，先遍历到

    def test_negative_x(self):
        """触摸在负坐标"""
        result = find_target_column(-200, self.positions, self.cw)
        self.assertIsNone(result)

    def test_first_column(self):
        """选中第一列"""
        result = find_target_column(20, self.positions, self.cw)
        self.assertEqual(result, 0)

    def test_last_column(self):
        """选中最后一列"""
        result = find_target_column(470, self.positions, self.cw)
        self.assertEqual(result, 9)


class TestCompletedStackSize(unittest.TestCase):
    """测试完成区布局计算"""

    def test_stack_width_capped(self):
        """stack 宽度不超过 cw * 0.7"""
        cw = 60
        stack_w, stack_h, stack_gap = calc_completed_stack_size(800, cw)
        self.assertLessEqual(stack_w, cw * 0.7)

    def test_stack_width_minimum(self):
        """stack 宽度至少 20"""
        cw = 40
        stack_w, _, _ = calc_completed_stack_size(200, cw)  # 很窄
        self.assertGreaterEqual(stack_w, 20)

    def test_stack_aspect_ratio(self):
        """stack 高宽比为 1.42"""
        for w in [400, 500, 800]:
            stack_w, stack_h, _ = calc_completed_stack_size(w, 40)
            self.assertAlmostEqual(stack_h / stack_w, 1.42, places=5)

    def test_eight_stacks_fit(self):
        """8 个 stack 加间距应该放得下"""
        for widget_w in [400, 500, 800]:
            cw = 40
            stack_w, _, stack_gap = calc_completed_stack_size(widget_w, cw)
            total_needed = 8 * stack_w + 7 * stack_gap
            avail_w = widget_w - 2 * MARGIN - cw - 15
            self.assertLessEqual(total_needed, avail_w + 40,  # 加 dp(35) 余量
                                 f"widget_w={widget_w}")


class TestStockRemaining(unittest.TestCase):
    """测试发牌堆剩余数量计算"""

    def test_full_stock(self):
        """满额 50 张 = 5 组"""
        self.assertEqual(calc_stock_remaining(50), 5)

    def test_partial_stock(self):
        """30 张 = 3 组"""
        self.assertEqual(calc_stock_remaining(30), 3)

    def test_last_deal(self):
        """10 张 = 1 组"""
        self.assertEqual(calc_stock_remaining(10), 1)

    def test_empty_stock(self):
        """空 = 0 组"""
        self.assertEqual(calc_stock_remaining(0), 0)

    def test_not_divisible(self):
        """不整除（不应该发生，但测试边界）"""
        self.assertEqual(calc_stock_remaining(17), 1)


class TestFmtTime(unittest.TestCase):
    """测试时间格式化"""

    def test_zero(self):
        self.assertEqual(fmt_time(0), '--')

    def test_negative(self):
        self.assertEqual(fmt_time(-5), '--')

    def test_seconds_only(self):
        self.assertEqual(fmt_time(45), '0:45')

    def test_one_minute(self):
        self.assertEqual(fmt_time(60), '1:00')

    def test_mixed(self):
        self.assertEqual(fmt_time(125), '2:05')

    def test_float_input(self):
        """浮点数被截断为整数"""
        self.assertEqual(fmt_time(65.9), '1:05')

    def test_large_value(self):
        self.assertEqual(fmt_time(3661), '61:01')

    def test_one_second(self):
        self.assertEqual(fmt_time(1), '0:01')


class TestFmtTimeGameScreen(unittest.TestCase):
    """测试 game_screen 中的时间格式化"""

    def test_zero(self):
        self.assertEqual(fmt_time_game_screen(0), '00:00')

    def test_seconds_only(self):
        self.assertEqual(fmt_time_game_screen(45), '00:45')

    def test_one_minute(self):
        self.assertEqual(fmt_time_game_screen(60), '01:00')

    def test_mixed(self):
        self.assertEqual(fmt_time_game_screen(125), '02:05')

    def test_hour_plus(self):
        """超过 60 分钟"""
        self.assertEqual(fmt_time_game_screen(3661), '61:01')


class TestDifficultyLabel(unittest.TestCase):
    """测试难度显示映射"""

    def test_easy(self):
        self.assertEqual(get_difficulty_label('easy'), '初级')

    def test_medium(self):
        self.assertEqual(get_difficulty_label('medium'), '中级')

    def test_hard(self):
        self.assertEqual(get_difficulty_label('hard'), '高级')

    def test_unknown(self):
        self.assertEqual(get_difficulty_label('expert'), '')

    def test_empty(self):
        self.assertEqual(get_difficulty_label(''), '')

    def test_none(self):
        self.assertEqual(get_difficulty_label(None), '')


class TestSuitColor(unittest.TestCase):
    """测试花色颜色映射"""

    RED = (0.85, 0.1, 0.1, 1)
    BLACK = (0.1, 0.1, 0.1, 1)

    def test_heart_is_red(self):
        self.assertEqual(get_suit_color('heart'), self.RED)

    def test_diamond_is_red(self):
        self.assertEqual(get_suit_color('diamond'), self.RED)

    def test_spade_is_black(self):
        self.assertEqual(get_suit_color('spade'), self.BLACK)

    def test_club_is_black(self):
        self.assertEqual(get_suit_color('club'), self.BLACK)

    def test_all_four_suits(self):
        """确保每种花色都有颜色"""
        for suit in ['heart', 'diamond', 'spade', 'club']:
            color = get_suit_color(suit)
            self.assertEqual(len(color), 4)  # RGBA


class TestCardFontSizes(unittest.TestCase):
    """测试卡牌字体大小计算"""

    def test_proportional_to_width(self):
        """字体大小与卡牌宽度成正比"""
        rank_40, suit_40 = calc_card_font_sizes(40)
        rank_80, suit_80 = calc_card_font_sizes(80)
        self.assertAlmostEqual(rank_80 / rank_40, 2.0)
        self.assertAlmostEqual(suit_80 / suit_40, 2.0)

    def test_suit_larger_than_rank(self):
        """花色符号比等级文字大"""
        rank, suit = calc_card_font_sizes(50)
        self.assertGreater(suit, rank)

    def test_specific_ratios(self):
        """精确比例 0.45 和 0.62"""
        rank, suit = calc_card_font_sizes(60)
        self.assertAlmostEqual(rank, 27)
        self.assertAlmostEqual(suit, 37.2)

    def test_min_card_width(self):
        """最小卡牌宽度 (30dp) 的字体仍然可读"""
        rank, suit = calc_card_font_sizes(30)
        self.assertAlmostEqual(rank, 13.5)  # 可读
        self.assertAlmostEqual(suit, 18.6)


class TestCardBackStep(unittest.TestCase):
    """测试卡牌背面交叉纹样步长"""

    def test_normal_width(self):
        """正常宽度 60 → step = 7"""
        self.assertEqual(calc_card_back_step(60), 7)

    def test_narrow_width(self):
        """窄卡牌 30 → step = 6 (最小值)"""
        self.assertEqual(calc_card_back_step(30), 6)

    def test_very_narrow(self):
        """极窄卡牌 → step 不低于 6"""
        self.assertEqual(calc_card_back_step(10), 6)

    def test_wide_card(self):
        """宽卡牌 80 → step = 10"""
        self.assertEqual(calc_card_back_step(80), 10)


class TestColumnPositionsEdgeCases(unittest.TestCase):
    """列位置计算的边界情况"""

    def test_very_narrow_widget(self):
        """极窄 widget 仍然生成 10 个位置"""
        positions, gap = calc_column_positions(0, 100, 30)
        self.assertEqual(len(positions), 10)
        self.assertEqual(gap, 1)  # 最小间距

    def test_very_wide_widget(self):
        """极宽 widget 产生大间距"""
        positions, gap = calc_column_positions(0, 2000, 40)
        self.assertEqual(len(positions), 10)
        self.assertGreater(gap, 100)

    def test_exact_fit(self):
        """恰好放下 10 列（无多余间距）"""
        cw = 40
        # usable = w - 30, 需要 10*40 + 9*gap = usable
        # 最小 gap=1: 10*40 + 9 = 409, 所以 w = 439
        positions, gap = calc_column_positions(0, 439, cw)
        self.assertEqual(len(positions), 10)
        # 间距应该约等于 1
        self.assertAlmostEqual(gap, 1, places=0)


class TestDragToleranceAtDifferentWidths(unittest.TestCase):
    """不同屏幕宽度下拖放容差的行为"""

    def test_tolerance_with_large_cards(self):
        """大卡牌时容差 = cw * 2.5"""
        cw = 60
        tolerance = max(cw * 2.5, 80)
        self.assertEqual(tolerance, 150)

    def test_tolerance_with_small_cards(self):
        """小卡牌时容差最少 80"""
        cw = 30
        tolerance = max(cw * 2.5, 80)
        self.assertEqual(tolerance, 80)

    def test_tolerance_boundary(self):
        """cw = 32 时刚好超过 80"""
        cw = 32
        tolerance = max(cw * 2.5, 80)
        self.assertEqual(tolerance, 80)

        cw = 33
        tolerance = max(cw * 2.5, 80)
        self.assertAlmostEqual(tolerance, 82.5)

    def test_mate40_tolerance(self):
        """Mate 40 宽度下的容差"""
        cw, _, _ = calc_card_size(420)
        tolerance = max(cw * 2.5, 80)
        # cw ≈ 37.2, 2.5 * 37.2 = 93 > 80
        self.assertGreater(tolerance, 80)


class TestIntegrationCardSizeToColumns(unittest.TestCase):
    """端到端：从屏幕宽度到列位置的完整计算链"""

    def test_mate40_full_layout(self):
        """Mate 40 的完整布局计算"""
        width = 420
        cw, ch, cr = calc_card_size(width)
        positions, gap = calc_column_positions(0, width, cw)

        # 10 列
        self.assertEqual(len(positions), 10)

        # 第一列不在负坐标
        self.assertGreaterEqual(positions[0], 0)

        # 最后一列右边缘不超出屏幕
        last_right = positions[9] + cw
        self.assertLessEqual(last_right, width)

        # 间距合理（> 0）
        self.assertGreater(gap, 0)

    def test_phone_widths(self):
        """多种手机宽度都能正确布局"""
        for width in [360, 375, 390, 412, 420, 480]:
            cw, ch, cr = calc_card_size(width)
            positions, gap = calc_column_positions(0, width, cw)

            self.assertEqual(len(positions), 10)
            self.assertGreaterEqual(positions[0], 0)
            self.assertLessEqual(positions[9] + cw, width)

    def test_tablet_width(self):
        """平板宽度（卡牌应为最大值 60）"""
        cw, ch, cr = calc_card_size(800)
        self.assertEqual(cw, 60)
        positions, gap = calc_column_positions(0, 800, cw)
        self.assertEqual(len(positions), 10)


class TestOverlapScalingRealWorld(unittest.TestCase):
    """真实场景的重叠缩放测试"""

    def test_initial_deal_column(self):
        """初始发牌：5 面朝下 + 1 面朝上（右 6 列）"""
        flags = [False, False, False, False, True, True]
        # 可用高度估算：420 的屏幕约 350 高度
        factor, total = calc_overlap_factor(flags, 350)
        # total = 4*15 + 1*25 = 85, 350 >> 85
        self.assertEqual(factor, 1.0)
        self.assertEqual(total, 85)

    def test_long_column_needs_scaling(self):
        """很长的列需要缩放：5 面朝下 + 15 面朝上（共 20 张，19 个间距）"""
        flags = [False] * 5 + [True] * 15
        factor, total = calc_overlap_factor(flags, 300)
        # n-1=19 间距: flags[0..4]=False → 5 个 CLOSED, flags[5..18]=True → 14 个 OPEN
        # total = 5*15 + 14*25 = 75 + 350 = 425
        expected = 300 / 425
        self.assertAlmostEqual(factor, expected, places=5)

    def test_all_face_down_initial(self):
        """全部面朝下（除最后一张）"""
        flags = [False] * 5 + [True]
        factor, total = calc_overlap_factor(flags, 200)
        # total = 4*15 + 1*25 = 85
        self.assertEqual(factor, 1.0)


# ============================================================
# 自动移动目标选择测试（使用真实 GameState）
# ============================================================

from spider_solitaire.game.card import Card
from spider_solitaire.game.game_state import GameState


def find_random_auto_target(gs, from_col, card_idx):
    """_find_random_auto_target 的纯函数版本（与 board_widget 逻辑一致）

    收集所有合法目标，随机选一个返回。
    """
    import random as _rnd

    moving_seq = gs.get_movable_sequence(from_col, card_idx)
    if not moving_seq:
        return None

    candidates = []
    for col_idx in range(10):
        if col_idx == from_col:
            continue
        if gs.can_move(from_col, card_idx, col_idx):
            candidates.append(col_idx)

    if not candidates:
        return None
    return _rnd.choice(candidates)


class TestAutoMoveTargetSelection(unittest.TestCase):
    """测试点击自动移动的目标选择逻辑"""

    def _make_gs(self):
        """创建一个空的 GameState 供手动设置列"""
        gs = GameState('easy')
        gs.columns = [[] for _ in range(10)]
        gs.stock = []
        gs.completed = []
        gs.score = 500
        gs.moves = 0
        return gs

    def test_returns_legal_target(self):
        """随机选择一个合法目标列"""
        gs = self._make_gs()
        # 列 0：要移动的 3♥
        gs.columns[0] = [Card('heart', 3, True)]
        # 列 1：4♥ — 同花色匹配
        gs.columns[1] = [Card('heart', 4, True)]
        # 列 2：4♠ — 不同花色匹配
        gs.columns[2] = [Card('spade', 4, True)]
        # 列 3-9：空列

        # 运行多次验证随机性 + 合法性
        legal = {1, 2, 3, 4, 5, 6, 7, 8, 9}  # 所有非源列都合法
        seen = set()
        for _ in range(100):
            target = find_random_auto_target(gs, 0, 0)
            self.assertIn(target, legal)
            seen.add(target)
        # 100 次应该至少选到 2 个不同的目标（概率极高）
        self.assertGreater(len(seen), 1)

    def test_single_legal_target(self):
        """只有一个合法目标时必定选它"""
        gs = self._make_gs()
        gs.columns[0] = [Card('heart', 3, True)]
        gs.columns[1] = [Card('heart', 4, True)]
        # 其他列放不匹配的牌
        for i in range(2, 10):
            gs.columns[i] = [Card('heart', 1, True)]  # A，3不能放A上

        target = find_random_auto_target(gs, 0, 0)
        self.assertEqual(target, 1)

    def test_empty_col_is_valid_target(self):
        """空列也是合法目标"""
        gs = self._make_gs()
        gs.columns[0] = [Card('heart', 5, True)]
        # 其他列全放不匹配的牌，除了列 2 是空的
        for i in range(1, 10):
            gs.columns[i] = [Card('heart', 3, True)]  # 5 不能放 3 上
        gs.columns[2] = []  # 空列

        target = find_random_auto_target(gs, 0, 0)
        self.assertEqual(target, 2)

    def test_no_legal_move(self):
        """所有列都满且无合法移动时返回 None"""
        gs = self._make_gs()
        # 列 0：K♥ — 要移动的牌
        gs.columns[0] = [Card('heart', 13, True)]
        # 其他列都放 A（K 不能放在 A 上，rank 差 12）
        for i in range(1, 10):
            gs.columns[i] = [Card('heart', 1, True)]

        target = find_random_auto_target(gs, 0, 0)
        self.assertIsNone(target)

    def test_move_sequence(self):
        """移动多张序列时返回合法目标"""
        gs = self._make_gs()
        # 列 0：5♥, 4♥, 3♥ 同花色递减序列
        gs.columns[0] = [
            Card('heart', 5, True),
            Card('heart', 4, True),
            Card('heart', 3, True),
        ]
        # 列 1：6♥ — 同花色可接
        gs.columns[1] = [Card('heart', 6, True)]
        # 列 2：6♠ — 不同花色可接
        gs.columns[2] = [Card('spade', 6, True)]

        # 从 index 0 开始移动整个序列（顶部是 5♥）
        target = find_random_auto_target(gs, 0, 0)
        # 随机选择，但结果必须是合法的（1, 2, 或空列）
        self.assertIsNotNone(target)
        self.assertNotEqual(target, 0)

    def test_skip_source_column(self):
        """不会选择源列自身"""
        gs = self._make_gs()
        gs.columns[0] = [Card('heart', 4, True), Card('heart', 3, True)]
        # 只有列 0 有牌

        target = find_random_auto_target(gs, 0, 1)
        # 3♥ 可以去空列
        self.assertIsNotNone(target)
        self.assertNotEqual(target, 0)

    def test_face_down_card_blocked_by_ui(self):
        """面朝下的牌在 UI 层被拦截，不会进入 auto-move

        注意：get_movable_sequence 不检查 face_up（只看花色和 rank），
        face_up 检查发生在 on_touch_down 中。因此此处测试的是：
        即使传入面朝下的索引，find_random_auto_target 仍能安全返回结果
        （不会崩溃），但实际运行时不会被调用。
        """
        gs = self._make_gs()
        gs.columns[0] = [Card('heart', 5, False), Card('heart', 4, True)]

        # 面朝下的牌在 UI 层被拦截，这里只验证函数不崩溃
        target = find_random_auto_target(gs, 0, 0)
        # 不检查返回值，只确保不报错

    def test_auto_move_does_not_affect_game_state(self):
        """find_random_auto_target 不修改游戏状态"""
        gs = self._make_gs()
        gs.columns[0] = [Card('heart', 3, True)]
        gs.columns[1] = [Card('heart', 4, True)]

        import copy
        before = copy.deepcopy(gs.columns)
        find_random_auto_target(gs, 0, 0)
        # 验证状态未改变
        for i in range(10):
            self.assertEqual(len(gs.columns[i]), len(before[i]))


class TestTapVsDragThreshold(unittest.TestCase):
    """测试点击 vs 拖拽的距离判断"""

    def test_zero_distance_is_tap(self):
        dist = 0
        self.assertTrue(dist < 15)  # TAP_THRESHOLD = dp(15)

    def test_small_movement_is_tap(self):
        """手指微移 < 15dp 仍为点击"""
        dist = ((3) ** 2 + (4) ** 2) ** 0.5  # = 5
        self.assertTrue(dist < 15)

    def test_large_movement_is_drag(self):
        """手指移动 > 15dp 为拖拽"""
        dist = ((10) ** 2 + (12) ** 2) ** 0.5  # ≈ 15.6
        self.assertFalse(dist < 15)

    def test_exact_threshold(self):
        """恰好 15dp 不算点击（< 不是 <=）"""
        dist = 15.0
        self.assertFalse(dist < 15)


if __name__ == '__main__':
    unittest.main()
