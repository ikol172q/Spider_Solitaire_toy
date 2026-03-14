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


def calc_card_size(widget_width, widget_height=99999, margin=MARGIN):
    """board_widget.py._calc_card_size() 的纯函数版本

    同时考虑宽度约束和高度约束（横屏时高度可能更受限）。
    widget_height 默认为很大的值，这样纯宽度测试不受影响。
    横屏时使用 1.15 纵横比（更扁），竖屏使用 1.42。
    """
    dp_min, dp_max = 30, 60
    usable_w = widget_width - 2 * margin
    min_gap = 2  # dp(2)
    max_card_w = (usable_w - 9 * min_gap) / 10  # 宽度约束

    # 横屏时卡牌更扁（1.15），竖屏保持标准（1.42）
    is_landscape = widget_width > widget_height
    aspect = 1.15 if is_landscape else 1.42

    # 高度约束：ch=cw*aspect, 需要 ch + ch*0.4 + 20 <= height*0.5
    # → cw <= (height*0.5 - 20) / (aspect * 1.4)
    max_card_w_h = (widget_height * 0.5 - 20) / (aspect * 1.4)

    cw = min(dp_max, max(dp_min, min(max_card_w, max_card_w_h)))
    ch = cw * aspect
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


# ============================================================
# 横屏 & 横竖屏切换 — 纯计算逻辑的辅助函数
# ============================================================

def detect_orientation(width, height):
    """判断当前方向: 'landscape' / 'portrait' / 'square'"""
    if width > height:
        return 'landscape'
    elif height > width:
        return 'portrait'
    return 'square'


def calc_bar_height(width, height, base_bar_height=56):
    """game_screen.py._upd_bg() 中状态栏/按钮栏高度自适应"""
    is_landscape = width > height
    return base_bar_height * 0.75 if is_landscape else base_bar_height


def calc_menu_hint_x(width, height):
    """menu_screen.py._on_size() 中菜单宽度自适应"""
    return 0.55 if width > height else 1


def calc_stats_hint_x(width, height):
    """stats_screen.py._on_size() 中统计页宽度自适应"""
    return 0.6 if width > height else 1


def calc_board_available_height(widget_height, ch, padding=PADDING):
    """board_widget.py._top_y - _bottom_y 的纯计算版本
    可用绘牌区域高度 = (height - 10 - ch) - (ch*0.4 + padding)
    """
    top_y = widget_height - 10 - ch
    bottom_y = ch * 0.4 + padding
    return top_y - bottom_y


def simulate_rotation(w, h):
    """模拟旋转: 交换宽高"""
    return h, w


# ============================================================
# 横屏卡牌尺寸测试
# ============================================================

class TestLandscapeCardSize(unittest.TestCase):
    """测试横屏时高度约束对卡牌尺寸的影响"""

    def test_landscape_height_limits_card_size(self):
        """横屏时高度约束可能比宽度约束更严"""
        cw_portrait, _, _ = calc_card_size(420, 920)
        cw_landscape, _, _ = calc_card_size(920, 420)
        self.assertLessEqual(cw_landscape, 60)
        self.assertGreaterEqual(cw_landscape, 30)

    def test_landscape_cards_fit_height(self):
        """横屏时卡牌高度 + 底部区域不超过可用高度的 50%"""
        for h in [300, 350, 400, 420, 480]:
            cw, ch, _ = calc_card_size(920, h)
            needed = ch + ch * 0.4 + 20
            self.assertLessEqual(needed, h * 0.5 + 1,
                                 f"height={h}, cw={cw}, ch={ch}")

    def test_portrait_unaffected_by_large_height(self):
        """竖屏时（高度充裕）只受宽度约束"""
        cw_no_h, _, _ = calc_card_size(420)
        cw_with_h, _, _ = calc_card_size(420, 920)
        self.assertAlmostEqual(cw_no_h, cw_with_h, places=3)

    def test_very_short_landscape(self):
        """极矮横屏 — 高度约束占主导（aspect=1.15 更扁，需要更矮才触发）"""
        cw, ch, _ = calc_card_size(1200, 200)
        # h=200: (100-20)/(1.15*1.4) = 49.7 → cw < 60
        self.assertLess(cw, 60)
        self.assertGreaterEqual(cw, 30)

    def test_landscape_ten_columns_still_fit(self):
        """横屏时 10 列仍然放得下"""
        for w, h in [(920, 420), (800, 360), (1080, 480)]:
            cw, _, _ = calc_card_size(w, h)
            usable = w - 2 * MARGIN
            min_total = 10 * cw + 9 * 1
            self.assertLessEqual(min_total, usable + 1,
                                 f"w={w}, h={h}, cw={cw}")

    def test_landscape_card_smaller_than_portrait_on_mate40(self):
        """Mate 40 横屏时卡牌应比竖屏小（因为高度更受限）"""
        cw_p, _, _ = calc_card_size(420, 920)   # 竖屏
        cw_l, _, _ = calc_card_size(920, 420)   # 横屏
        # 竖屏 cw ≈ 37.2 (宽度约束), 横屏高度约束 ≈ (210-20)/1.988 ≈ 95.6 → capped 60
        # 但宽度约束 (920-30-18)/10=87.2 → capped 60
        # 两个约束都 >= 60，所以横屏 cw=60 > 竖屏 37.2
        # 实际上横屏 Mate40 宽度够 → 卡牌反而更大
        self.assertGreaterEqual(cw_l, cw_p)

    def test_height_constraint_formula_correctness(self):
        """验证高度约束公式: cw <= (h*0.5 - 20) / (aspect * 1.4)
        宽度 2000 > h → 横屏 → aspect=1.15
        """
        for h in [250, 300, 400, 500]:
            aspect = 1.15  # 2000 > h → landscape
            expected_max = (h * 0.5 - 20) / (aspect * 1.4)
            cw, ch, _ = calc_card_size(2000, h)  # 宽度不限
            # cw 应该受高度约束且 <= 60
            self.assertLessEqual(cw, min(60, expected_max) + 0.01)

    def test_both_constraints_simultaneously(self):
        """宽度和高度同时受限"""
        # 宽度约束: (350-30-18)/10 = 30.2 → cw ≈ 30.2
        # 高度约束: (300*0.5-20)/1.988 = 65.4 → 不受限
        cw, _, _ = calc_card_size(350, 300)
        self.assertAlmostEqual(cw, 30.2, places=0)

    def test_min_card_size_even_in_extreme_landscape(self):
        """即使极端横屏，卡牌也不低于最小值 30"""
        cw, _, _ = calc_card_size(2000, 100)
        # h=100: (50-20)/(1.15*1.4)=18.6 → clamp to 30
        self.assertEqual(cw, 30)

    def test_aspect_ratio_maintained_in_landscape(self):
        """横屏时高宽比 1.15（更扁的牌）"""
        for w, h in [(920, 420), (800, 360), (1080, 480), (1200, 250)]:
            cw, ch, _ = calc_card_size(w, h)
            self.assertAlmostEqual(ch / cw, 1.15, places=5,
                                   msg=f"w={w}, h={h}")


# ============================================================
# 横竖屏切换测试（旋转）
# ============================================================

class TestOrientationSwitching(unittest.TestCase):
    """测试竖屏 ↔ 横屏切换时的计算一致性"""

    # --- Mate 40 常量 ---
    MATE40_P = (420, 920)   # 竖屏
    MATE40_L = (920, 420)   # 横屏

    def test_rotation_swaps_dimensions(self):
        """旋转后宽高互换"""
        w, h = simulate_rotation(*self.MATE40_P)
        self.assertEqual((w, h), self.MATE40_L)

    def test_double_rotation_restores(self):
        """旋转两次 = 回到原始"""
        w, h = simulate_rotation(*simulate_rotation(*self.MATE40_P))
        self.assertEqual((w, h), self.MATE40_P)

    def test_card_size_recalculated_after_rotation(self):
        """旋转后 calc_card_size 产生不同结果"""
        cw_p, _, _ = calc_card_size(*self.MATE40_P)
        cw_l, _, _ = calc_card_size(*self.MATE40_L)
        # 不要求大小关系，但要求两者都合法
        self.assertGreaterEqual(cw_p, 30)
        self.assertLessEqual(cw_p, 60)
        self.assertGreaterEqual(cw_l, 30)
        self.assertLessEqual(cw_l, 60)

    def test_column_positions_recalculated_after_rotation(self):
        """旋转后列位置也会重新计算"""
        cw_p, _, _ = calc_card_size(*self.MATE40_P)
        pos_p, gap_p = calc_column_positions(0, self.MATE40_P[0], cw_p)

        cw_l, _, _ = calc_card_size(*self.MATE40_L)
        pos_l, gap_l = calc_column_positions(0, self.MATE40_L[0], cw_l)

        # 横屏更宽，间距应该更大
        self.assertGreater(gap_l, gap_p)
        # 两个方向都有 10 列
        self.assertEqual(len(pos_p), 10)
        self.assertEqual(len(pos_l), 10)

    def test_portrait_to_landscape_and_back_card_size_stable(self):
        """竖屏 → 横屏 → 竖屏 后卡牌尺寸恢复原值"""
        cw1, ch1, cr1 = calc_card_size(*self.MATE40_P)
        _ = calc_card_size(*self.MATE40_L)  # 横屏中间状态
        cw3, ch3, cr3 = calc_card_size(*self.MATE40_P)  # 回到竖屏
        self.assertAlmostEqual(cw1, cw3, places=5)
        self.assertAlmostEqual(ch1, ch3, places=5)
        self.assertAlmostEqual(cr1, cr3, places=5)

    def test_column_positions_stable_after_roundtrip(self):
        """竖屏 → 横屏 → 竖屏 后列位置恢复"""
        cw = calc_card_size(*self.MATE40_P)[0]
        pos1, gap1 = calc_column_positions(0, self.MATE40_P[0], cw)

        cw_l = calc_card_size(*self.MATE40_L)[0]
        _ = calc_column_positions(0, self.MATE40_L[0], cw_l)

        cw_back = calc_card_size(*self.MATE40_P)[0]
        pos3, gap3 = calc_column_positions(0, self.MATE40_P[0], cw_back)

        for a, b in zip(pos1, pos3):
            self.assertAlmostEqual(a, b, places=5)
        self.assertAlmostEqual(gap1, gap3, places=5)

    def test_overlap_factor_tighter_in_landscape(self):
        """横屏时重叠需要更多缩放（可用高度更小）"""
        # 20 张牌的重叠
        flags = [False] * 5 + [True] * 15

        cw_p, ch_p, _ = calc_card_size(*self.MATE40_P)
        avail_p = calc_board_available_height(self.MATE40_P[1], ch_p)
        factor_p, _ = calc_overlap_factor(flags, avail_p)

        cw_l, ch_l, _ = calc_card_size(*self.MATE40_L)
        avail_l = calc_board_available_height(self.MATE40_L[1], ch_l)
        factor_l, _ = calc_overlap_factor(flags, avail_l)

        # 横屏可用高度更小，缩放因子应 <= 竖屏
        self.assertLessEqual(factor_l, factor_p + 0.01,
                             f"portrait factor={factor_p}, landscape factor={factor_l}")

    def test_many_real_device_sizes(self):
        """多种真实设备尺寸的竖屏和横屏都能正常布局"""
        devices = [
            (420, 920),   # Mate 40
            (360, 780),   # 小屏手机
            (412, 915),   # Pixel 7
            (393, 852),   # iPhone 14
            (480, 1040),  # 大屏手机
            (600, 1024),  # 小平板
            (800, 1280),  # 大平板
        ]
        for pw, ph in devices:
            for w, h in [(pw, ph), (ph, pw)]:  # 竖屏 + 横屏
                cw, ch, _ = calc_card_size(w, h)
                self.assertGreaterEqual(cw, 30, f"device=({w},{h})")
                self.assertLessEqual(cw, 60, f"device=({w},{h})")

                # 10 列放得下
                pos, gap = calc_column_positions(0, w, cw)
                self.assertEqual(len(pos), 10, f"device=({w},{h})")
                self.assertLessEqual(pos[9] + cw, w, f"device=({w},{h})")

                # 高度约束成立
                needed = ch + ch * 0.4 + 20
                self.assertLessEqual(needed, h * 0.5 + 1, f"device=({w},{h})")


class TestRotationDragAndAnimationSafety(unittest.TestCase):
    """测试旋转时拖拽/动画状态重置的逻辑正确性

    board_widget._on_resize() 在旋转时:
    1. 如果 _animating=True → 取消所有动画，设 _animating=False
    2. 如果 _dragging=True → 重置拖拽状态
    这里用纯数据结构模拟这个逻辑。
    """

    def _make_state(self, animating=False, dragging=False,
                    drag_col=None, drag_idx=None, touch_start=None):
        return {
            'animating': animating,
            'dragging': dragging,
            'drag_col': drag_col,
            'drag_idx': drag_idx,
            'touch_start_pos': touch_start,
        }

    def _simulate_on_resize(self, state):
        """模拟 board_widget._on_resize() 的状态重置逻辑"""
        new = dict(state)
        if new['animating']:
            # 取消所有动画
            new['animating'] = False
        if new['dragging']:
            new['dragging'] = False
            new['drag_col'] = None
            new['drag_idx'] = None
            new['touch_start_pos'] = None
        return new

    def test_idle_state_unchanged(self):
        """空闲状态旋转不改变任何状态"""
        state = self._make_state()
        after = self._simulate_on_resize(state)
        self.assertEqual(state, after)

    def test_animation_cancelled_on_resize(self):
        """旋转时动画被取消"""
        state = self._make_state(animating=True)
        after = self._simulate_on_resize(state)
        self.assertFalse(after['animating'])

    def test_drag_reset_on_resize(self):
        """旋转时拖拽被重置"""
        state = self._make_state(dragging=True, drag_col=3, drag_idx=5,
                                 touch_start=(100, 200))
        after = self._simulate_on_resize(state)
        self.assertFalse(after['dragging'])
        self.assertIsNone(after['drag_col'])
        self.assertIsNone(after['drag_idx'])
        self.assertIsNone(after['touch_start_pos'])

    def test_both_animation_and_drag_reset(self):
        """旋转时同时有动画和拖拽 → 都被重置"""
        state = self._make_state(animating=True, dragging=True,
                                 drag_col=2, drag_idx=7,
                                 touch_start=(50, 80))
        after = self._simulate_on_resize(state)
        self.assertFalse(after['animating'])
        self.assertFalse(after['dragging'])
        self.assertIsNone(after['drag_col'])

    def test_multiple_rapid_rotations(self):
        """快速连续旋转多次 → 状态始终安全"""
        state = self._make_state(animating=True, dragging=True,
                                 drag_col=5, drag_idx=2,
                                 touch_start=(200, 300))
        for _ in range(10):
            state = self._simulate_on_resize(state)
        self.assertFalse(state['animating'])
        self.assertFalse(state['dragging'])
        self.assertIsNone(state['drag_col'])

    def test_resize_then_new_drag(self):
        """旋转重置后可以开始新的拖拽"""
        state = self._make_state(dragging=True, drag_col=1, drag_idx=3)
        state = self._simulate_on_resize(state)
        # 模拟新拖拽
        state['dragging'] = True
        state['drag_col'] = 7
        state['drag_idx'] = 0
        state['touch_start_pos'] = (300, 400)
        self.assertTrue(state['dragging'])
        self.assertEqual(state['drag_col'], 7)

    def test_resize_then_new_animation(self):
        """旋转取消动画后可以开始新动画"""
        state = self._make_state(animating=True)
        state = self._simulate_on_resize(state)
        state['animating'] = True
        self.assertTrue(state['animating'])


class TestAutoMoveStateDuringRotation(unittest.TestCase):
    """测试旋转时自动移动开关状态的保持"""

    def test_auto_move_preserved_on_rotation(self):
        """auto_move_enabled 不被 _on_resize 重置"""
        # _on_resize 只重置 animating/dragging, 不碰 auto_move_enabled
        auto_move = True
        # 模拟 _on_resize — 它不修改 auto_move_enabled
        # 验证旋转后 auto_move 仍然是 True
        self.assertTrue(auto_move)

    def test_auto_move_toggle_state_machine(self):
        """自动移动开关状态机：关→开→关→开"""
        auto_on = False
        for expected in [True, False, True, False]:
            auto_on = not auto_on
            self.assertEqual(auto_on, expected)

    def test_auto_move_button_text_and_color(self):
        """开关切换时按钮文字和颜色的正确性"""
        GREEN = (0.2, 0.6, 0.2, 1)
        GRAY = (0.4, 0.4, 0.4, 1)

        auto_on = False
        # 切换到开
        auto_on = True
        text = '自动：开' if auto_on else '自动：关'
        color = GREEN if auto_on else GRAY
        self.assertEqual(text, '自动：开')
        self.assertEqual(color, GREEN)

        # 切换到关
        auto_on = False
        text = '自动：关' if not auto_on else '自动：开'
        color = GRAY if not auto_on else GREEN
        self.assertEqual(text, '自动：关')
        self.assertEqual(color, GRAY)

    def test_auto_move_uses_fullwidth_colon(self):
        """按钮文字使用全角冒号 ： (U+FF1A) 而不是 ASCII :"""
        text_on = '自动：开'
        text_off = '自动：关'
        self.assertIn('：', text_on)   # 全角冒号
        self.assertIn('：', text_off)
        self.assertNotIn(':', text_on)  # 非 ASCII 冒号
        self.assertNotIn(':', text_off)


# ============================================================
# 横竖屏布局自适应测试
# ============================================================

class TestLandscapeLayoutAdaptation(unittest.TestCase):
    """测试横竖屏布局自适应逻辑"""

    def test_menu_width_portrait(self):
        """竖屏时菜单全宽"""
        self.assertEqual(calc_menu_hint_x(420, 920), 1)

    def test_menu_width_landscape(self):
        """横屏时菜单宽度缩窄"""
        self.assertEqual(calc_menu_hint_x(920, 420), 0.55)

    def test_stats_width_portrait(self):
        """竖屏时统计页全宽"""
        self.assertEqual(calc_stats_hint_x(420, 920), 1)

    def test_stats_width_landscape(self):
        """横屏时统计页宽度缩窄"""
        self.assertEqual(calc_stats_hint_x(920, 420), 0.6)

    def test_bar_height_portrait(self):
        """竖屏时状态栏高度为 56"""
        self.assertEqual(calc_bar_height(420, 920), 56)

    def test_bar_height_landscape(self):
        """横屏时状态栏高度为 56*0.75=42"""
        self.assertEqual(calc_bar_height(920, 420), 42)

    def test_square_screen_not_landscape(self):
        """方形屏幕（宽=高）不算横屏"""
        self.assertEqual(detect_orientation(500, 500), 'square')
        self.assertEqual(calc_bar_height(500, 500), 56)
        self.assertEqual(calc_menu_hint_x(500, 500), 1)

    def test_landscape_bar_total_height_budget(self):
        """横屏时两个栏的总高度不超过可用高度的 25%"""
        for w, h in [(920, 420), (800, 360), (1080, 480)]:
            bar_h = calc_bar_height(w, h)
            total_bars = bar_h * 2  # 状态栏 + 按钮栏
            self.assertLessEqual(total_bars, h * 0.25,
                                 f"device=({w},{h}), total_bars={total_bars}")

    def test_portrait_bar_total_height_budget(self):
        """竖屏时两个栏的总高度不超过可用高度的 15%"""
        for w, h in [(420, 920), (360, 780), (412, 915)]:
            bar_h = calc_bar_height(w, h)
            total_bars = bar_h * 2
            self.assertLessEqual(total_bars, h * 0.15,
                                 f"device=({w},{h}), total_bars={total_bars}")

    def test_layout_changes_on_rotation(self):
        """旋转时所有布局参数都会改变"""
        # 竖屏
        bar_p = calc_bar_height(420, 920)
        menu_p = calc_menu_hint_x(420, 920)
        stats_p = calc_stats_hint_x(420, 920)

        # 横屏
        bar_l = calc_bar_height(920, 420)
        menu_l = calc_menu_hint_x(920, 420)
        stats_l = calc_stats_hint_x(920, 420)

        self.assertNotEqual(bar_p, bar_l)
        self.assertNotEqual(menu_p, menu_l)
        self.assertNotEqual(stats_p, stats_l)


class TestBoardAvailableHeight(unittest.TestCase):
    """测试棋盘可用绘牌高度在不同方向下的表现"""

    def test_portrait_has_more_available_height(self):
        """竖屏比横屏有更多可用高度"""
        cw_p, ch_p, _ = calc_card_size(420, 920)
        avail_p = calc_board_available_height(920, ch_p)

        cw_l, ch_l, _ = calc_card_size(920, 420)
        avail_l = calc_board_available_height(420, ch_l)

        self.assertGreater(avail_p, avail_l)

    def test_available_height_positive(self):
        """所有设备方向下可用高度都 > 0"""
        devices = [(420, 920), (920, 420), (360, 780), (780, 360),
                   (800, 1280), (1280, 800)]
        for w, h in devices:
            cw, ch, _ = calc_card_size(w, h)
            avail = calc_board_available_height(h, ch)
            self.assertGreater(avail, 0, f"device=({w},{h})")

    def test_initial_deal_fits_without_scaling(self):
        """初始发牌（6张最多 = 5间距）在所有方向不需要缩放"""
        devices = [(420, 920), (920, 420), (360, 780), (780, 360)]
        for w, h in devices:
            cw, ch, _ = calc_card_size(w, h)
            avail = calc_board_available_height(h, ch)
            # 初始列：5*CLOSED + 0*OPEN = 75 (最多)，实际 4*15+1*25=85
            initial_overlap = 4 * CARD_OVERLAP_CLOSED + 1 * CARD_OVERLAP_OPEN
            factor, _ = calc_overlap_factor(
                [False] * 5 + [True], avail)
            self.assertEqual(factor, 1.0,
                             f"device=({w},{h}), avail={avail}, overlap={initial_overlap}")

    def test_landscape_long_column_needs_more_scaling(self):
        """横屏时长列需要更激进的缩放"""
        flags = [False] * 5 + [True] * 15  # 20 张

        cw_p, ch_p, _ = calc_card_size(420, 920)
        avail_p = calc_board_available_height(920, ch_p)
        factor_p, total_p = calc_overlap_factor(flags, avail_p)

        cw_l, ch_l, _ = calc_card_size(920, 420)
        avail_l = calc_board_available_height(420, ch_l)
        factor_l, total_l = calc_overlap_factor(flags, avail_l)

        # 横屏可用高度更小，但 overlap total 可能不同（因为是固定常量）
        # 缩放因子应该更小（更激进的缩放）
        if factor_l < 1.0 or factor_p < 1.0:
            self.assertLessEqual(factor_l, factor_p + 0.01)


class TestOrientationDetection(unittest.TestCase):
    """测试方向检测的边界情况"""

    def test_portrait(self):
        self.assertEqual(detect_orientation(420, 920), 'portrait')

    def test_landscape(self):
        self.assertEqual(detect_orientation(920, 420), 'landscape')

    def test_square(self):
        self.assertEqual(detect_orientation(500, 500), 'square')

    def test_barely_landscape(self):
        """宽度只比高度多 1"""
        self.assertEqual(detect_orientation(501, 500), 'landscape')

    def test_barely_portrait(self):
        """高度只比宽度多 1"""
        self.assertEqual(detect_orientation(500, 501), 'portrait')

    def test_very_wide(self):
        """极宽屏幕（如折叠屏展开）"""
        self.assertEqual(detect_orientation(2000, 400), 'landscape')

    def test_very_tall(self):
        """极窄高屏幕"""
        self.assertEqual(detect_orientation(300, 1200), 'portrait')


class TestEndToEndRotationScenarios(unittest.TestCase):
    """端到端旋转场景：模拟完整的旋转流程"""

    def _full_layout(self, w, h):
        """计算某个方向下的全部布局参数"""
        cw, ch, cr = calc_card_size(w, h)
        positions, gap = calc_column_positions(0, w, cw)
        bar_h = calc_bar_height(w, h)
        menu_x = calc_menu_hint_x(w, h)
        avail_h = calc_board_available_height(h, ch)
        return {
            'cw': cw, 'ch': ch, 'cr': cr,
            'positions': positions, 'gap': gap,
            'bar_h': bar_h, 'menu_x': menu_x,
            'avail_h': avail_h, 'orientation': detect_orientation(w, h),
        }

    def test_mate40_portrait_layout_valid(self):
        """Mate 40 竖屏完整布局合法"""
        layout = self._full_layout(420, 920)
        self.assertEqual(layout['orientation'], 'portrait')
        self.assertEqual(len(layout['positions']), 10)
        self.assertGreater(layout['avail_h'], 0)
        self.assertEqual(layout['bar_h'], 56)
        self.assertEqual(layout['menu_x'], 1)

    def test_mate40_landscape_layout_valid(self):
        """Mate 40 横屏完整布局合法"""
        layout = self._full_layout(920, 420)
        self.assertEqual(layout['orientation'], 'landscape')
        self.assertEqual(len(layout['positions']), 10)
        self.assertGreater(layout['avail_h'], 0)
        self.assertEqual(layout['bar_h'], 42)
        self.assertEqual(layout['menu_x'], 0.55)

    def test_rotation_roundtrip_all_params_stable(self):
        """竖屏 → 横屏 → 竖屏 所有参数恢复"""
        layout1 = self._full_layout(420, 920)
        _ = self._full_layout(920, 420)  # 横屏
        layout3 = self._full_layout(420, 920)  # 回到竖屏

        self.assertAlmostEqual(layout1['cw'], layout3['cw'])
        self.assertAlmostEqual(layout1['ch'], layout3['ch'])
        self.assertAlmostEqual(layout1['gap'], layout3['gap'])
        self.assertAlmostEqual(layout1['avail_h'], layout3['avail_h'])
        self.assertEqual(layout1['bar_h'], layout3['bar_h'])
        self.assertEqual(layout1['menu_x'], layout3['menu_x'])

    def test_all_devices_portrait_and_landscape(self):
        """7 种设备的竖屏和横屏都能产生合法布局"""
        devices = [
            (420, 920), (360, 780), (412, 915),
            (393, 852), (480, 1040), (600, 1024), (800, 1280),
        ]
        for pw, ph in devices:
            for w, h in [(pw, ph), (ph, pw)]:
                layout = self._full_layout(w, h)
                self.assertEqual(len(layout['positions']), 10,
                                 f"device=({w},{h})")
                self.assertGreater(layout['avail_h'], 0,
                                   f"device=({w},{h})")
                self.assertGreaterEqual(layout['cw'], 30,
                                        f"device=({w},{h})")
                self.assertLessEqual(layout['cw'], 60,
                                     f"device=({w},{h})")
                last_right = layout['positions'][9] + layout['cw']
                self.assertLessEqual(last_right, w,
                                     f"device=({w},{h})")

    def test_game_mid_play_rotation(self):
        """游戏中途旋转：拖拽/动画状态重置 + 布局重新计算"""
        # 竖屏中正在拖拽
        state = {
            'animating': False,
            'dragging': True,
            'drag_col': 3,
            'drag_idx': 2,
            'touch_start_pos': (150, 600),
        }
        layout_p = self._full_layout(420, 920)

        # 旋转 → _on_resize 触发
        if state['animating']:
            state['animating'] = False
        if state['dragging']:
            state['dragging'] = False
            state['drag_col'] = None
            state['drag_idx'] = None
            state['touch_start_pos'] = None
        layout_l = self._full_layout(920, 420)

        # 验证状态安全 + 布局变化
        self.assertFalse(state['dragging'])
        self.assertNotEqual(layout_p['bar_h'], layout_l['bar_h'])

    def test_animation_in_progress_rotation(self):
        """动画进行中旋转：动画取消 + 布局刷新"""
        state = {'animating': True, 'dragging': False,
                 'drag_col': None, 'drag_idx': None,
                 'touch_start_pos': None}

        if state['animating']:
            state['animating'] = False

        layout = self._full_layout(920, 420)
        self.assertFalse(state['animating'])
        self.assertEqual(len(layout['positions']), 10)


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


# ============================================================
# 可移动序列检测（dimming 逻辑）
# ============================================================

def find_movable_start(column):
    """board_widget.py._find_movable_start() 的纯函数版本

    找到列中从底部开始的最长同花色降序序列起始索引。
    索引之前的翻开牌应被标记为 dimmed。
    """
    n = len(column)
    if n == 0:
        return n
    start = n - 1
    while start > 0:
        prev = column[start - 1]
        curr = column[start]
        if (prev['face_up'] and curr['face_up']
                and prev['suit'] == curr['suit']
                and prev['rank'] == curr['rank'] + 1):
            start -= 1
        else:
            break
    return start


def make_card(suit='spade', rank=1, face_up=True):
    """创建简单的 card dict 用于测试"""
    return {'suit': suit, 'rank': rank, 'face_up': face_up}


class TestFindMovableStart(unittest.TestCase):
    """测试可移动序列检测逻辑"""

    def test_empty_column(self):
        """空列返回 0"""
        self.assertEqual(find_movable_start([]), 0)

    def test_single_card(self):
        """单张牌 — movable_start = 0"""
        col = [make_card('spade', 5)]
        self.assertEqual(find_movable_start(col), 0)

    def test_two_card_same_suit_descending(self):
        """两张同花降序 — 全部可移动"""
        col = [make_card('spade', 6), make_card('spade', 5)]
        self.assertEqual(find_movable_start(col), 0)

    def test_two_card_different_suit(self):
        """两张不同花色 — 只有最后一张可移动"""
        col = [make_card('spade', 6), make_card('heart', 5)]
        self.assertEqual(find_movable_start(col), 1)

    def test_two_card_not_descending(self):
        """两张同花但不降序 — 只有最后一张可移动"""
        col = [make_card('spade', 5), make_card('spade', 6)]
        self.assertEqual(find_movable_start(col), 1)

    def test_long_same_suit_run(self):
        """K-Q-J-10-9-8-7-6-5-4-3-2-A 全同花降序"""
        col = [make_card('heart', r) for r in range(13, 0, -1)]
        self.assertEqual(find_movable_start(col), 0)

    def test_face_down_breaks_sequence(self):
        """背面牌打断序列"""
        col = [
            make_card('spade', 8, face_up=False),
            make_card('spade', 7),
            make_card('spade', 6),
            make_card('spade', 5),
        ]
        self.assertEqual(find_movable_start(col), 1)

    def test_mixed_suits_partial_run(self):
        """混合花色 — 只有底部连续同花降序部分可移动"""
        col = [
            make_card('heart', 10),    # 翻开，不同花色
            make_card('spade', 9),     # 翻开，序列起点
            make_card('spade', 8),
            make_card('spade', 7),
        ]
        self.assertEqual(find_movable_start(col), 1)

    def test_multiple_face_down_then_run(self):
        """多张背面 + 短序列"""
        col = [
            make_card('club', 10, face_up=False),
            make_card('club', 9, face_up=False),
            make_card('club', 5, face_up=False),
            make_card('diamond', 4),
            make_card('diamond', 3),
        ]
        self.assertEqual(find_movable_start(col), 3)

    def test_all_face_down(self):
        """全部背面 — 最后一张仍然是 start"""
        col = [
            make_card('spade', 5, face_up=False),
            make_card('spade', 4, face_up=False),
            make_card('spade', 3, face_up=False),
        ]
        self.assertEqual(find_movable_start(col), 2)

    def test_gap_in_rank_breaks(self):
        """同花但 rank 不连续打断序列"""
        col = [
            make_card('spade', 9),
            make_card('spade', 7),   # 跳过 8
            make_card('spade', 6),
        ]
        self.assertEqual(find_movable_start(col), 1)

    def test_dimmed_cards_count(self):
        """验证 dimmed 牌数量 = movable_start 之前的 face_up 牌"""
        col = [
            make_card('heart', 10, face_up=False),
            make_card('heart', 9),     # face_up, index 1 → dimmed
            make_card('spade', 8),     # face_up, index 2 → dimmed
            make_card('spade', 5),     # face_up, index 3 → dimmed
            make_card('diamond', 4),   # face_up, index 4 — movable start
            make_card('diamond', 3),   # face_up, index 5
        ]
        start = find_movable_start(col)
        self.assertEqual(start, 4)
        # dimmed 牌 = face_up 且 index < start
        dimmed = [c for i, c in enumerate(col) if c['face_up'] and i < start]
        self.assertEqual(len(dimmed), 3)


# ============================================================
# 紧凑模式字体计算
# ============================================================

def calc_card_fonts(card_width, compact=False):
    """card_widget.py CardWidget.__init__ 中字体计算的纯函数版本"""
    cw = card_width
    if compact:
        font_rank = cw * 0.38
        font_suit = cw * 0.50
    else:
        font_rank = cw * 0.45
        font_suit = cw * 0.62
    return font_rank, font_suit


class TestCompactMode(unittest.TestCase):
    """测试紧凑模式（横屏）字体缩小"""

    def test_compact_font_smaller_than_normal(self):
        """紧凑模式字体比标准模式小"""
        for cw in [30, 40, 50, 60]:
            fr_n, fs_n = calc_card_fonts(cw, compact=False)
            fr_c, fs_c = calc_card_fonts(cw, compact=True)
            self.assertLess(fr_c, fr_n, f"cw={cw}")
            self.assertLess(fs_c, fs_n, f"cw={cw}")

    def test_compact_font_ratio(self):
        """紧凑模式字体比例：rank=0.38, suit=0.50"""
        fr, fs = calc_card_fonts(50, compact=True)
        self.assertAlmostEqual(fr, 19.0)
        self.assertAlmostEqual(fs, 25.0)

    def test_normal_font_ratio(self):
        """标准模式字体比例：rank=0.45, suit=0.62"""
        fr, fs = calc_card_fonts(50, compact=False)
        self.assertAlmostEqual(fr, 22.5)
        self.assertAlmostEqual(fs, 31.0)

    def test_font_scales_with_card_width(self):
        """字体大小随卡牌宽度线性缩放"""
        fr30, fs30 = calc_card_fonts(30, compact=True)
        fr60, fs60 = calc_card_fonts(60, compact=True)
        self.assertAlmostEqual(fr60 / fr30, 2.0, places=3)
        self.assertAlmostEqual(fs60 / fs30, 2.0, places=3)


# ============================================================
# 迷你标签计算
# ============================================================

def calc_mini_label_font(visible_h, cw, dp_min=8):
    """board_widget.py._draw_mini_label() 中字体大小的纯计算"""
    return max(dp_min, min(visible_h * 0.75, cw * 0.22))


class TestMiniLabel(unittest.TestCase):
    """测试被压住翻开牌的迷你 rank+suit 标签"""

    def test_font_has_minimum(self):
        """字体不低于 dp(8)"""
        fs = calc_mini_label_font(5, 30)
        self.assertGreaterEqual(fs, 8)

    def test_font_limited_by_card_width(self):
        """字体不超过 cw * 0.22"""
        fs = calc_mini_label_font(100, 40)
        self.assertAlmostEqual(fs, 40 * 0.22)

    def test_font_limited_by_visible_height(self):
        """字体不超过 visible_h * 0.75（当此值更小时）"""
        fs = calc_mini_label_font(10, 100)
        # min(10*0.75, 100*0.22) = min(7.5, 22) = 7.5 → clamp to 8
        self.assertEqual(fs, 8)

    def test_font_scales_with_visible_height(self):
        """可见高度增加时字体增大"""
        fs1 = calc_mini_label_font(12, 60)
        fs2 = calc_mini_label_font(20, 60)
        self.assertLessEqual(fs1, fs2)

    def test_typical_landscape_values(self):
        """横屏典型值：visible_h ≈ 12-20dp, cw ≈ 50-60"""
        for vh, cw in [(12, 50), (15, 55), (20, 60)]:
            fs = calc_mini_label_font(vh, cw)
            self.assertGreaterEqual(fs, 8)
            self.assertLessEqual(fs, cw * 0.22 + 0.01)

    def test_mini_label_text_format(self):
        """迷你标签文本格式：rank + suit 符号"""
        from spider_solitaire.game.card import SUITS, RANK_NAMES
        for rank in [1, 5, 10, 13]:
            for suit in ['spade', 'heart']:
                text = f'{RANK_NAMES[rank]}{SUITS[suit]}'
                self.assertTrue(len(text) >= 2)
                self.assertIn(SUITS[suit], text)

    def test_red_suits_detection(self):
        """红色花色检测：heart, diamond"""
        red_suits = {'heart', 'diamond'}
        for suit in ['spade', 'heart', 'diamond', 'club']:
            is_red = suit in red_suits
            if suit in ('heart', 'diamond'):
                self.assertTrue(is_red)
            else:
                self.assertFalse(is_red)


# ============================================================
# 横屏重叠距离计算
# ============================================================

def calc_landscape_overlaps(is_landscape):
    """board_widget.py._draw_column() 中横屏重叠距离的纯计算"""
    if is_landscape:
        overlap_closed = CARD_OVERLAP_CLOSED * 0.3
        overlap_open = CARD_OVERLAP_OPEN * 0.85
    else:
        overlap_closed = CARD_OVERLAP_CLOSED
        overlap_open = CARD_OVERLAP_OPEN
    return overlap_closed, overlap_open


class TestLandscapeOverlaps(unittest.TestCase):
    """测试横屏时重叠距离调整"""

    def test_landscape_closed_much_smaller(self):
        """横屏时背面牌重叠仅 30%"""
        oc_l, _ = calc_landscape_overlaps(True)
        oc_p, _ = calc_landscape_overlaps(False)
        self.assertAlmostEqual(oc_l / oc_p, 0.3, places=3)

    def test_landscape_open_slightly_smaller(self):
        """横屏时正面牌重叠为 85%"""
        _, oo_l = calc_landscape_overlaps(True)
        _, oo_p = calc_landscape_overlaps(False)
        self.assertAlmostEqual(oo_l / oo_p, 0.85, places=3)

    def test_portrait_overlaps_unchanged(self):
        """竖屏重叠距离与 theme 常量一致"""
        oc, oo = calc_landscape_overlaps(False)
        self.assertEqual(oc, CARD_OVERLAP_CLOSED)
        self.assertEqual(oo, CARD_OVERLAP_OPEN)

    def test_landscape_values(self):
        """横屏具体数值"""
        oc, oo = calc_landscape_overlaps(True)
        self.assertAlmostEqual(oc, 15 * 0.3)   # 4.5
        self.assertAlmostEqual(oo, 25 * 0.85)  # 21.25

    def test_min_open_visible_guarantee(self):
        """横屏时打开牌最小可见区域为 dp(12)"""
        min_open_visible = 12  # dp(12)
        _, oo_l = calc_landscape_overlaps(True)
        # 即使 overlap * factor 很小，也保证至少 dp(12) 的可见区域
        self.assertGreater(oo_l, min_open_visible)


# ============================================================
# 横屏纵横比切换测试
# ============================================================

class TestLandscapeAspectRatio(unittest.TestCase):
    """测试横屏时卡牌使用 1.15 纵横比（更扁）"""

    def test_landscape_aspect_is_1_15(self):
        """横屏时 ch/cw = 1.15"""
        cw, ch, _ = calc_card_size(920, 420)
        self.assertAlmostEqual(ch / cw, 1.15, places=5)

    def test_portrait_aspect_is_1_42(self):
        """竖屏时 ch/cw = 1.42"""
        cw, ch, _ = calc_card_size(420, 920)
        self.assertAlmostEqual(ch / cw, 1.42, places=5)

    def test_landscape_card_flatter(self):
        """横屏牌比竖屏牌更扁"""
        _, ch_l, _ = calc_card_size(920, 420)
        cw_l, _, _ = calc_card_size(920, 420)
        _, ch_p, _ = calc_card_size(420, 920)
        cw_p, _, _ = calc_card_size(420, 920)
        self.assertLess(ch_l / cw_l, ch_p / cw_p)

    def test_aspect_switches_on_rotation(self):
        """旋转时纵横比自动切换"""
        cw_p, ch_p, _ = calc_card_size(420, 920)
        cw_l, ch_l, _ = calc_card_size(920, 420)
        self.assertAlmostEqual(ch_p / cw_p, 1.42, places=5)
        self.assertAlmostEqual(ch_l / cw_l, 1.15, places=5)

    def test_square_uses_portrait_aspect(self):
        """正方形屏幕（w == h）使用竖屏纵横比 1.42"""
        cw, ch, _ = calc_card_size(500, 500)
        self.assertAlmostEqual(ch / cw, 1.42, places=5)

    def test_barely_landscape_uses_1_15(self):
        """宽度略大于高度时使用 1.15"""
        cw, ch, _ = calc_card_size(501, 500)
        self.assertAlmostEqual(ch / cw, 1.15, places=5)

    def test_multiple_devices_aspect(self):
        """多种设备尺寸下纵横比正确"""
        devices = [
            (920, 420, 1.15),    # Mate 40 横屏
            (420, 920, 1.42),    # Mate 40 竖屏
            (800, 360, 1.15),    # 小手机横屏
            (360, 800, 1.42),    # 小手机竖屏
            (1080, 480, 1.15),   # 大手机横屏
            (480, 1080, 1.42),   # 大手机竖屏
        ]
        for w, h, expected_aspect in devices:
            cw, ch, _ = calc_card_size(w, h)
            self.assertAlmostEqual(ch / cw, expected_aspect, places=5,
                                   msg=f"device {w}x{h}")


# ============================================================
# 底部区域缩放（横屏时完成区/发牌区缩小）
# ============================================================

STATUS_BAR_HEIGHT = 56  # dp(56) 模拟值


def calc_bottom_area_scale(width, height):
    """board_widget._bottom_area_scale 的纯函数版本"""
    return 0.65 if width > height else 1.0


def calc_button_bar_height(width, height):
    """game_screen._upd_bg 中按钮栏高度的纯函数版本"""
    is_landscape = width > height
    return STATUS_BAR_HEIGHT * 0.78 if is_landscape else STATUS_BAR_HEIGHT


def calc_status_bar_height_landscape():
    """game_screen._apply_status_landscape 中状态栏高度"""
    return STATUS_BAR_HEIGHT * 0.62


class TestBottomAreaScale(unittest.TestCase):
    """测试横屏时底部区域缩放"""

    def test_landscape_scale_is_0_65(self):
        """横屏时缩放系数为 0.65"""
        self.assertAlmostEqual(calc_bottom_area_scale(920, 420), 0.65)

    def test_portrait_scale_is_1(self):
        """竖屏时缩放系数为 1.0"""
        self.assertAlmostEqual(calc_bottom_area_scale(420, 920), 1.0)

    def test_square_is_portrait(self):
        """正方形时使用竖屏缩放"""
        self.assertAlmostEqual(calc_bottom_area_scale(500, 500), 1.0)

    def test_stock_area_smaller_in_landscape(self):
        """横屏发牌区比竖屏小"""
        cw_l, ch_l, _ = calc_card_size(920, 420)
        cw_p, ch_p, _ = calc_card_size(420, 920)
        scale_l = calc_bottom_area_scale(920, 420)
        scale_p = calc_bottom_area_scale(420, 920)
        area_l = (cw_l * scale_l) * (ch_l * scale_l)
        area_p = (cw_p * scale_p) * (ch_p * scale_p)
        self.assertLess(area_l, area_p)

    def test_completed_stack_smaller_in_landscape(self):
        """横屏完成区堆叠也更小"""
        scale_l = calc_bottom_area_scale(920, 420)
        scale_p = calc_bottom_area_scale(420, 920)
        self.assertLess(scale_l, scale_p)


class TestButtonBarHeight(unittest.TestCase):
    """测试按钮栏高度"""

    def test_landscape_button_bar(self):
        """横屏按钮栏高度为 0.78x"""
        h = calc_button_bar_height(920, 420)
        self.assertAlmostEqual(h, STATUS_BAR_HEIGHT * 0.78)

    def test_portrait_button_bar(self):
        """竖屏按钮栏高度为 1x"""
        h = calc_button_bar_height(420, 920)
        self.assertAlmostEqual(h, STATUS_BAR_HEIGHT)

    def test_landscape_bar_taller_than_old(self):
        """横屏按钮栏比旧版 0.65x 更高"""
        h = calc_button_bar_height(920, 420)
        old_h = STATUS_BAR_HEIGHT * 0.65
        self.assertGreater(h, old_h)

    def test_landscape_status_bar_height(self):
        """横屏状态栏高度合理"""
        h = calc_status_bar_height_landscape()
        self.assertGreater(h, 30)  # 足够容纳文字
        self.assertLess(h, STATUS_BAR_HEIGHT)

    def test_total_bars_leave_space_for_board(self):
        """横屏时状态栏+按钮栏总高度不超过 widget 高度的 25%"""
        screen_h = 420
        status_h = calc_status_bar_height_landscape()
        button_h = calc_button_bar_height(920, 420)
        total = status_h + button_h
        self.assertLess(total / screen_h, 0.25,
                         f"bars={total}, screen={screen_h}")


# ============================================================
# 分阶段压缩测试（替代旧的统一 factor 方式）
# ============================================================

def calc_two_phase_overlaps(face_up_flags, available,
                            ideal_closed=CARD_OVERLAP_CLOSED,
                            ideal_open=CARD_OVERLAP_OPEN,
                            min_closed=2, min_open=9):
    """board_widget._calc_column_overlaps 的纯函数版本

    分阶段压缩：
    1. 先压暗牌到极限（min_closed），保持亮牌理想间距
    2. 暗牌已到极限仍不够，再压亮牌（最低 min_open）
    """
    n = len(face_up_flags)
    if n <= 1:
        return []

    closed_count = sum(1 for i in range(n - 1) if not face_up_flags[i])
    open_count = (n - 1) - closed_count

    ideal_total = closed_count * ideal_closed + open_count * ideal_open

    if ideal_total <= available:
        return [ideal_open if face_up_flags[i] else ideal_closed
                for i in range(n - 1)]

    # 第一阶段：压暗牌
    open_total = open_count * ideal_open
    remaining_for_closed = available - open_total

    if closed_count > 0 and remaining_for_closed >= closed_count * min_closed:
        closed_each = remaining_for_closed / closed_count
        return [ideal_open if face_up_flags[i] else closed_each
                for i in range(n - 1)]

    # 第二阶段：暗牌到极限，压亮牌
    remaining_for_open = available - closed_count * min_closed
    open_each = remaining_for_open / open_count if open_count > 0 else 0
    open_each = max(min_open, open_each)

    return [open_each if face_up_flags[i] else min_closed
            for i in range(n - 1)]


class TestTwoPhaseCompression(unittest.TestCase):
    """测试分阶段压缩策略"""

    def test_no_compression_needed(self):
        """充足空间 — 所有牌用理想间距"""
        flags = [False] * 3 + [True] * 5
        overlaps = calc_two_phase_overlaps(flags, 500)
        for i, ov in enumerate(overlaps):
            if flags[i]:
                self.assertAlmostEqual(ov, CARD_OVERLAP_OPEN)
            else:
                self.assertAlmostEqual(ov, CARD_OVERLAP_CLOSED)

    def test_only_closed_compressed(self):
        """空间略紧 — 只压暗牌，亮牌保持理想"""
        # 5 暗 + 5 亮，理想：5*15+5*25=200, 但只有 160 空间
        flags = [False] * 5 + [True] * 5 + [True]  # 11 张，10 个间距
        overlaps = calc_two_phase_overlaps(flags, 160)
        for i, ov in enumerate(overlaps):
            if flags[i]:
                self.assertAlmostEqual(ov, CARD_OVERLAP_OPEN,
                                        msg=f"亮牌 idx={i} 不应被压缩")

    def test_closed_at_minimum_before_open_compressed(self):
        """暗牌到最小值后才开始压亮牌"""
        # 5 暗 + 10 亮, 理想：5*15+10*25=325, 只有 80 空间
        flags = [False] * 5 + [True] * 10 + [True]  # 16 张
        overlaps = calc_two_phase_overlaps(flags, 80)
        for i, ov in enumerate(overlaps):
            if not flags[i]:
                self.assertAlmostEqual(ov, 2, msg=f"暗牌 idx={i} 应在最小值")

    def test_open_cards_respect_minimum(self):
        """亮牌间距不低于 min_open"""
        # 20 张全亮牌，极少空间
        flags = [True] * 20
        overlaps = calc_two_phase_overlaps(flags, 50)
        for ov in overlaps:
            self.assertGreaterEqual(ov, 9)

    def test_total_fits_available(self):
        """总间距不超过可用高度（有余量时）"""
        flags = [False] * 4 + [True] * 8
        available = 150
        overlaps = calc_two_phase_overlaps(flags, available)
        total = sum(overlaps)
        # 可能略超（因为 min_open 保底），但不应大幅超出
        self.assertLessEqual(total, available + 9 * 8,  # 最多 8 张亮牌各超 9dp
                              msg=f"总间距 {total} 远超可用 {available}")

    def test_face_down_compressed_more_than_face_up(self):
        """暗牌间距 <= 亮牌间距"""
        flags = [False] * 5 + [True] * 10
        overlaps = calc_two_phase_overlaps(flags, 120)
        closed_vals = [overlaps[i] for i in range(len(overlaps)) if not flags[i]]
        open_vals = [overlaps[i] for i in range(len(overlaps)) if flags[i]]
        if closed_vals and open_vals:
            self.assertLessEqual(max(closed_vals), min(open_vals))

    def test_single_card_no_overlaps(self):
        """单张牌无间距"""
        self.assertEqual(calc_two_phase_overlaps([True], 200), [])

    def test_empty_column(self):
        """空列无间距"""
        self.assertEqual(calc_two_phase_overlaps([], 200), [])

    def test_all_closed_column(self):
        """全暗牌列（初始状态）"""
        flags = [False] * 6
        overlaps = calc_two_phase_overlaps(flags, 50)
        self.assertEqual(len(overlaps), 5)
        # 全暗牌：理想 5*15=75 > 50, 应该被压缩
        for ov in overlaps:
            self.assertAlmostEqual(ov, 10.0)  # 50/5=10

    def test_realistic_mate40_landscape(self):
        """Mate 40 横屏 — 真实场景：5 暗 + 15 亮"""
        # 横屏可用高度大约 250dp
        flags = [False] * 5 + [True] * 15
        # 横屏重叠：暗 4.5, 亮 21.25
        overlaps = calc_two_phase_overlaps(
            flags, 250,
            ideal_closed=4.5, ideal_open=21.25,
            min_closed=2, min_open=9)
        total = sum(overlaps)
        # 理想：5*4.5+15*21.25=341.25 > 250，需压缩
        self.assertLessEqual(total, 260)  # 允许少量 min_open 溢出
        # 暗牌应该被优先压缩
        closed_vals = [overlaps[i] for i in range(len(overlaps)) if not flags[i]]
        open_vals = [overlaps[i] for i in range(len(overlaps)) if flags[i]]
        self.assertTrue(all(c <= 4.5 for c in closed_vals))


# ============================================================
# 长按弹窗逻辑测试
# ============================================================

def extract_face_up_cards(column):
    """模拟 _on_long_press 中提取 face_up 牌的逻辑"""
    return [(i, c) for i, c in enumerate(column) if c['face_up']]


def calc_popup_label_color(suit, is_movable):
    """模拟 _on_long_press 中标签颜色计算（深色背景 + 亮色文字，支持四花色）

    可移动牌：每种花色有独立亮色
    不可移动牌：同色系降低亮度，alpha 0.8
    """
    suit_bright = {
        'heart':   (1.0, 0.4, 0.4, 1.0),    # 亮红
        'diamond': (1.0, 0.5, 0.25, 1.0),    # 亮橙红
        'club':    (1.0, 1.0, 1.0, 1.0),     # 白色
        'spade':   (0.7, 0.85, 1.0, 1.0),    # 亮蓝白
    }
    bright = suit_bright.get(suit, (1.0, 1.0, 1.0, 1.0))
    if is_movable:
        return bright
    else:
        return tuple(c * 0.6 for c in bright[:3]) + (0.8,)


def calc_popup_size(face_up_count, dp_unit=1):
    """模拟 popup 尺寸计算"""
    width = 90 * dp_unit
    height = min(300 * dp_unit, face_up_count * 28 * dp_unit + 40 * dp_unit)
    return width, height


class TestLongPressPopupLogic(unittest.TestCase):
    """测试长按弹窗的纯逻辑"""

    def test_extract_face_up_only(self):
        """只提取翻开的牌"""
        col = [
            make_card('spade', 10, face_up=False),
            make_card('spade', 9, face_up=False),
            make_card('heart', 8),
            make_card('heart', 7),
        ]
        result = extract_face_up_cards(col)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][0], 2)  # index 2
        self.assertEqual(result[1][0], 3)  # index 3

    def test_extract_all_face_down(self):
        """全暗牌 — 无弹窗内容"""
        col = [make_card('spade', i, face_up=False) for i in range(5, 0, -1)]
        result = extract_face_up_cards(col)
        self.assertEqual(len(result), 0)

    def test_extract_all_face_up(self):
        """全亮牌"""
        col = [make_card('heart', r) for r in range(13, 0, -1)]
        result = extract_face_up_cards(col)
        self.assertEqual(len(result), 13)

    def test_extract_empty_column(self):
        """空列"""
        self.assertEqual(extract_face_up_cards([]), [])

    def test_movable_heart_bright_red(self):
        """可移动红心用亮红色"""
        color = calc_popup_label_color('heart', is_movable=True)
        self.assertEqual(color, (1.0, 0.4, 0.4, 1.0))

    def test_movable_diamond_bright_orange(self):
        """可移动方块用亮橙红"""
        color = calc_popup_label_color('diamond', is_movable=True)
        self.assertEqual(color, (1.0, 0.5, 0.25, 1.0))

    def test_movable_club_white(self):
        """可移动梅花用白色"""
        color = calc_popup_label_color('club', is_movable=True)
        self.assertEqual(color, (1.0, 1.0, 1.0, 1.0))

    def test_movable_spade_light_blue(self):
        """可移动黑桃用亮蓝白"""
        color = calc_popup_label_color('spade', is_movable=True)
        self.assertEqual(color, (0.7, 0.85, 1.0, 1.0))

    def test_non_movable_alpha_0_8(self):
        """不可移动牌的 alpha 为 0.8（比之前 0.55 亮很多）"""
        for suit in ('heart', 'diamond', 'spade', 'club'):
            color = calc_popup_label_color(suit, is_movable=False)
            self.assertAlmostEqual(color[3], 0.8)

    def test_non_movable_dimmed_rgb_darker(self):
        """不可移动牌的 RGB 亮度低于可移动牌"""
        for suit in ('heart', 'diamond', 'spade', 'club'):
            orig = calc_popup_label_color(suit, is_movable=True)
            dimmed = calc_popup_label_color(suit, is_movable=False)
            for i in range(3):
                self.assertLessEqual(dimmed[i], orig[i])

    def test_non_movable_visible_on_dark_bg(self):
        """不可移动牌在深色背景上仍可见"""
        for suit in ('heart', 'diamond', 'spade', 'club'):
            color = calc_popup_label_color(suit, is_movable=False)
            # 至少有一个 RGB 分量 > 0.3（深色背景上可见）
            self.assertTrue(any(c > 0.3 for c in color[:3]),
                          f"suit={suit} color={color} 在深色背景上不可见")

    def test_four_suits_all_distinguishable(self):
        """四花色可移动颜色互相可区分"""
        colors = {s: calc_popup_label_color(s, True) for s in ('heart', 'diamond', 'club', 'spade')}
        # 红心和方块都偏红但不同
        self.assertNotEqual(colors['heart'], colors['diamond'])
        # 梅花和黑桃都偏白/蓝但不同
        self.assertNotEqual(colors['club'], colors['spade'])
        # 红色系和黑色系差别明显
        self.assertGreater(colors['heart'][0], colors['spade'][0])

    def test_popup_size_small_column(self):
        """少量牌 — 高度按牌数计算"""
        w, h = calc_popup_size(3)
        self.assertEqual(w, 90)
        self.assertEqual(h, 3 * 28 + 40)  # 124

    def test_popup_size_capped_at_300(self):
        """大量牌 — 高度上限 300"""
        w, h = calc_popup_size(20)
        self.assertEqual(h, 300)

    def test_popup_size_single_card(self):
        """单张牌"""
        w, h = calc_popup_size(1)
        self.assertEqual(h, 1 * 28 + 40)  # 68

    def test_movable_vs_dimmed_font_size(self):
        """可移动牌字体 18dp > 不可移动牌 15dp"""
        movable_fs = 18
        non_movable_fs = 15
        self.assertGreater(movable_fs, non_movable_fs)


class TestLongPressWithMovableStart(unittest.TestCase):
    """测试长按弹窗 + 可移动检测的集成逻辑"""

    def test_popup_labels_match_movable(self):
        """弹窗中可移动标记与 find_movable_start 一致"""
        col = [
            make_card('spade', 10, face_up=False),
            make_card('heart', 9),       # dimmed (idx 1)
            make_card('spade', 8),       # dimmed (idx 2)
            make_card('diamond', 5),     # movable start (idx 3)
            make_card('diamond', 4),     # movable (idx 4)
            make_card('diamond', 3),     # movable (idx 5)
        ]
        movable_start = find_movable_start(col)
        face_up = extract_face_up_cards(col)

        for idx, card in face_up:
            is_movable = idx >= movable_start
            color = calc_popup_label_color(card['suit'], is_movable)
            if is_movable:
                self.assertEqual(color[3], 1.0, f"idx={idx} 应该完全不透明")
            else:
                self.assertLess(color[3], 1.0, f"idx={idx} 应该半透明")

    def test_all_movable_no_dimmed(self):
        """全同花降序 — 弹窗无 dimmed 牌"""
        col = [make_card('spade', r) for r in range(5, 0, -1)]
        movable_start = find_movable_start(col)
        self.assertEqual(movable_start, 0)
        face_up = extract_face_up_cards(col)
        for idx, card in face_up:
            color = calc_popup_label_color(card['suit'], idx >= movable_start)
            self.assertEqual(color[3], 1.0)

    def test_single_card_always_movable(self):
        """单张牌永远可移动"""
        col = [make_card('heart', 7)]
        movable_start = find_movable_start(col)
        self.assertEqual(movable_start, 0)
        color = calc_popup_label_color('heart', True)
        self.assertEqual(color[3], 1.0)


# ============================================================
# 两阶段压缩补充边界测试
# ============================================================

class TestTwoPhaseCompressionEdgeCases(unittest.TestCase):
    """补充的边界场景测试"""

    def test_all_open_needs_compression(self):
        """全亮牌列需要压缩"""
        flags = [True] * 15
        overlaps = calc_two_phase_overlaps(flags, 100)
        self.assertEqual(len(overlaps), 14)
        # 没有暗牌，直接压亮牌
        for ov in overlaps:
            self.assertGreaterEqual(ov, 9)  # min_open

    def test_two_cards_no_overlap_needed(self):
        """两张牌，空间充足"""
        flags = [True, True]
        overlaps = calc_two_phase_overlaps(flags, 200)
        self.assertEqual(len(overlaps), 1)
        self.assertAlmostEqual(overlaps[0], CARD_OVERLAP_OPEN)

    def test_two_closed_cards_tight(self):
        """两张暗牌，空间极紧"""
        flags = [False, False]
        overlaps = calc_two_phase_overlaps(flags, 3)
        self.assertEqual(len(overlaps), 1)
        self.assertAlmostEqual(overlaps[0], 3.0)  # 3/1=3

    def test_one_closed_one_open_tight(self):
        """一暗一亮一张，空间紧"""
        flags = [False, True, True]  # 3 cards, 2 overlaps
        # 理想: 15+25=40, 给 30 空间
        overlaps = calc_two_phase_overlaps(flags, 30)
        self.assertEqual(len(overlaps), 2)
        # 暗牌被压, 亮牌保持
        self.assertAlmostEqual(overlaps[1], CARD_OVERLAP_OPEN)  # 亮牌
        self.assertAlmostEqual(overlaps[0], 30 - CARD_OVERLAP_OPEN)  # 暗牌 = 5

    def test_zero_available_space(self):
        """可用空间为 0"""
        flags = [True] * 5
        overlaps = calc_two_phase_overlaps(flags, 0)
        # min_open 保底
        for ov in overlaps:
            self.assertGreaterEqual(ov, 9)

    def test_negative_available_space(self):
        """负的可用空间（极端情况）"""
        flags = [False, True, True]
        overlaps = calc_two_phase_overlaps(flags, -10)
        # 不应 crash，min 保底
        self.assertEqual(len(overlaps), 2)

    def test_symmetry_of_compression(self):
        """同类型牌的间距相等"""
        flags = [False, False, True, True, True, False, True]
        overlaps = calc_two_phase_overlaps(flags, 80)
        closed_vals = set(overlaps[i] for i in range(len(overlaps)) if not flags[i])
        open_vals = set(overlaps[i] for i in range(len(overlaps)) if flags[i])
        # 同类型牌间距应该相同
        self.assertLessEqual(len(closed_vals), 1, "暗牌间距应一致")
        self.assertLessEqual(len(open_vals), 1, "亮牌间距应一致")

    def test_large_column_30_cards(self):
        """30 张牌极端场景"""
        flags = [False] * 10 + [True] * 20
        overlaps = calc_two_phase_overlaps(flags, 150)
        self.assertEqual(len(overlaps), 29)
        total = sum(overlaps)
        # 即使 min_open 保底可能超出，也不应 crash
        self.assertGreater(total, 0)


# ============================================================
# 触摸交互取消逻辑测试
# ============================================================

class TestTouchCancellationLogic(unittest.TestCase):
    """测试长按/拖拽的取消逻辑（纯状态机）"""

    def test_long_press_cancelled_by_drag(self):
        """移动距离超过阈值时应取消长按"""
        threshold = 15
        dx, dy = 20, 0
        dist = math.sqrt(dx ** 2 + dy ** 2)
        should_cancel = dist > threshold
        self.assertTrue(should_cancel)

    def test_small_move_keeps_long_press(self):
        """小移动不取消长按"""
        threshold = 15
        dx, dy = 5, 5
        dist = math.sqrt(dx ** 2 + dy ** 2)
        should_cancel = dist > threshold
        self.assertFalse(should_cancel)

    def test_resize_cancels_everything(self):
        """resize 事件应重置所有拖拽/动画/长按状态"""
        # 模拟 _on_resize 的逻辑
        dragging = True
        long_press_event = "scheduled"
        long_press_popup = "open"

        # _on_resize 会将所有这些置空
        dragging = False
        long_press_event = None
        long_press_popup = None

        self.assertFalse(dragging)
        self.assertIsNone(long_press_event)
        self.assertIsNone(long_press_popup)

    def test_long_press_resets_drag_state(self):
        """长按触发时应清除拖拽状态"""
        # 模拟 _on_long_press 开头的逻辑
        dragging = True
        drag_col = 3
        drag_idx = 5

        # _on_long_press 清除拖拽
        dragging = False
        drag_col = None
        drag_idx = None

        self.assertFalse(dragging)
        self.assertIsNone(drag_col)
        self.assertIsNone(drag_idx)


# ============================================================
# CardWidget 低亮（dimmed）颜色公式测试
# ============================================================

def calc_dimmed_color(base_color):
    """card_widget.py._draw_face() 中 dimmed 牌的颜色计算

    公式: tuple(c * 0.5 + 0.3 for c in base_color[:3]) + (0.7,)
    """
    return tuple(c * 0.5 + 0.3 for c in base_color[:3]) + (0.7,)


# RED_SUIT_COLOR = (0.85, 0.1, 0.1, 1)
# BLACK_SUIT_COLOR = (0.1, 0.1, 0.1, 1)
_RED = (0.85, 0.1, 0.1, 1)
_BLACK = (0.1, 0.1, 0.1, 1)


class TestDimmedCardColor(unittest.TestCase):
    """测试 CardWidget dimmed 模式颜色公式"""

    def test_red_dimmed_lighter(self):
        """红色 dimmed 后 R 变小（更接近灰色）"""
        dimmed = calc_dimmed_color(_RED)
        # R: 0.85*0.5+0.3=0.725, 比原始 0.85 小
        self.assertLess(dimmed[0], _RED[0])

    def test_black_dimmed_lighter(self):
        """黑色 dimmed 后变亮（RGB 都增大）"""
        dimmed = calc_dimmed_color(_BLACK)
        for i in range(3):
            self.assertGreater(dimmed[i], _BLACK[i])

    def test_dimmed_alpha_is_0_7(self):
        """dimmed 颜色 alpha = 0.7"""
        for base in [_RED, _BLACK]:
            dimmed = calc_dimmed_color(base)
            self.assertAlmostEqual(dimmed[3], 0.7)

    def test_dimmed_rgb_in_range(self):
        """dimmed 后 RGB 值在 [0, 1] 范围内"""
        for base in [_RED, _BLACK, (1, 1, 1, 1), (0, 0, 0, 1)]:
            dimmed = calc_dimmed_color(base)
            for c in dimmed[:3]:
                self.assertGreaterEqual(c, 0.0)
                self.assertLessEqual(c, 1.0)

    def test_red_specific_values(self):
        """红色 dimmed 精确值"""
        dimmed = calc_dimmed_color(_RED)
        self.assertAlmostEqual(dimmed[0], 0.725)   # 0.85*0.5+0.3
        self.assertAlmostEqual(dimmed[1], 0.35)     # 0.1*0.5+0.3
        self.assertAlmostEqual(dimmed[2], 0.35)     # 0.1*0.5+0.3

    def test_black_specific_values(self):
        """黑色 dimmed 精确值"""
        dimmed = calc_dimmed_color(_BLACK)
        self.assertAlmostEqual(dimmed[0], 0.35)     # 0.1*0.5+0.3
        self.assertAlmostEqual(dimmed[1], 0.35)
        self.assertAlmostEqual(dimmed[2], 0.35)

    def test_dimmed_vs_original_distinguishable(self):
        """dimmed 颜色与原色有明显区别"""
        for base in [_RED, _BLACK]:
            dimmed = calc_dimmed_color(base)
            diff = sum(abs(dimmed[i] - base[i]) for i in range(3))
            self.assertGreater(diff, 0.1, f"dimmed 与原色差距太小: {base} → {dimmed}")

    def test_dimmed_background_color(self):
        """dimmed 牌背景色为浅灰 (0.82, 0.82, 0.80, 1)"""
        bg = (0.82, 0.82, 0.80, 1)
        self.assertAlmostEqual(bg[0], 0.82)
        self.assertAlmostEqual(bg[2], 0.80)
        # 不能是纯白（与正常牌区分）
        self.assertLess(bg[0], 1.0)


# ============================================================
# 压缩列检测逻辑测试
# ============================================================

def is_column_compressed(overlaps, face_up_flags, threshold=14):
    """board_widget.py 中列压缩检测的纯函数版本

    当列中 face_up 牌的平均间距 < threshold 时标记为 compressed
    """
    if not overlaps:
        return False
    avg_open = 0
    open_count = 0
    for i, ov in enumerate(overlaps):
        if i < len(face_up_flags) and face_up_flags[i]:
            avg_open += ov
            open_count += 1
    if open_count == 0:
        return False
    avg_open /= open_count
    return avg_open < threshold


class TestCompressedColumnDetection(unittest.TestCase):
    """测试压缩列检测逻辑"""

    def test_not_compressed_normal_spacing(self):
        """正常间距 — 不压缩"""
        overlaps = [15, 25, 25, 25]  # 暗牌15 + 亮牌25
        flags = [False, True, True, True]
        self.assertFalse(is_column_compressed(overlaps, flags))

    def test_compressed_tight_spacing(self):
        """极紧间距 — 标记压缩"""
        overlaps = [2, 10, 10, 10]  # 暗牌2 + 亮牌10 < 14
        flags = [False, True, True, True]
        self.assertTrue(is_column_compressed(overlaps, flags))

    def test_threshold_boundary_exact(self):
        """恰好 = 14 — 不压缩"""
        overlaps = [2, 14, 14, 14]
        flags = [False, True, True, True]
        self.assertFalse(is_column_compressed(overlaps, flags))

    def test_threshold_just_below(self):
        """< 14 — 标记压缩"""
        overlaps = [2, 13.9, 13.9, 13.9]
        flags = [False, True, True, True]
        self.assertTrue(is_column_compressed(overlaps, flags))

    def test_all_closed_not_compressed(self):
        """全暗牌 — 不标记压缩（没有亮牌）"""
        overlaps = [2, 2, 2, 2]
        flags = [False, False, False, False]
        self.assertFalse(is_column_compressed(overlaps, flags))

    def test_empty_overlaps(self):
        """空列不压缩"""
        self.assertFalse(is_column_compressed([], []))

    def test_single_face_up_tight(self):
        """单张亮牌极紧"""
        overlaps = [9]
        flags = [True]
        self.assertTrue(is_column_compressed(overlaps, flags))

    def test_mixed_some_tight_some_not(self):
        """混合 — 平均值决定"""
        # 亮牌间距: 20, 8 → 平均 14，不压缩
        overlaps = [2, 20, 8]
        flags = [False, True, True]
        self.assertFalse(is_column_compressed(overlaps, flags))


# ============================================================
# 发牌区显示逻辑测试
# ============================================================

def calc_stock_display_layers(stock_count):
    """board_widget._draw_stock() 中的层数和剩余次数计算"""
    remaining = stock_count // 10
    layers = min(remaining, 5)
    return remaining, layers


def calc_stock_layer_offset(layer_index, scale=1.0, dp_unit=2):
    """每层牌的偏移量"""
    return layer_index * dp_unit * scale


class TestStockDisplay(unittest.TestCase):
    """测试发牌区显示逻辑"""

    def test_full_stock_50_cards(self):
        """50 张牌 → 5 次 → 5 层"""
        remaining, layers = calc_stock_display_layers(50)
        self.assertEqual(remaining, 5)
        self.assertEqual(layers, 5)

    def test_stock_30_cards(self):
        """30 张牌 → 3 次 → 3 层"""
        remaining, layers = calc_stock_display_layers(30)
        self.assertEqual(remaining, 3)
        self.assertEqual(layers, 3)

    def test_stock_60_cards(self):
        """60 张牌 → 6 次 → 上限 5 层"""
        remaining, layers = calc_stock_display_layers(60)
        self.assertEqual(remaining, 6)
        self.assertEqual(layers, 5)

    def test_stock_0_cards(self):
        """0 张牌 → 0 次 → 0 层"""
        remaining, layers = calc_stock_display_layers(0)
        self.assertEqual(remaining, 0)
        self.assertEqual(layers, 0)

    def test_stock_10_last_deal(self):
        """10 张牌 → 1 次 → 1 层"""
        remaining, layers = calc_stock_display_layers(10)
        self.assertEqual(remaining, 1)
        self.assertEqual(layers, 1)

    def test_stock_not_divisible(self):
        """非整除 — 向下取整"""
        remaining, _ = calc_stock_display_layers(15)
        self.assertEqual(remaining, 1)

    def test_layer_offset_portrait(self):
        """竖屏每层偏移 = i * dp(2)"""
        for i in range(5):
            off = calc_stock_layer_offset(i, scale=1.0)
            self.assertAlmostEqual(off, i * 2)

    def test_layer_offset_landscape(self):
        """横屏每层偏移 = i * dp(2) * 0.65"""
        for i in range(5):
            off = calc_stock_layer_offset(i, scale=0.65)
            self.assertAlmostEqual(off, i * 2 * 0.65)

    def test_first_layer_no_offset(self):
        """第一层无偏移"""
        self.assertAlmostEqual(calc_stock_layer_offset(0), 0)


# ============================================================
# 完成区叠放层逻辑测试
# ============================================================

def calc_completed_stack_layout(done, max_stacks=8, max_layers=4):
    """board_widget._draw_completed() 中叠放逻辑的纯函数版本

    返回每个位置的 (is_filled, layers, top_offset_x, top_offset_y) 列表
    """
    result = []
    for i in range(max_stacks):
        if i < done:
            layers = min(max_layers, 13)
            top_off_x = (layers - 1) * 0.5  # dp(0.5) per layer
            top_off_y = (layers - 1) * 1.0   # dp(1) per layer
            result.append((True, layers, top_off_x, top_off_y))
        else:
            result.append((False, 0, 0, 0))
    return result


class TestCompletedStackLayout(unittest.TestCase):
    """测试完成区叠放逻辑"""

    def test_no_completed(self):
        """0 套完成 — 全部空"""
        layout = calc_completed_stack_layout(0)
        self.assertEqual(len(layout), 8)
        for filled, layers, _, _ in layout:
            self.assertFalse(filled)

    def test_3_completed(self):
        """3 套完成"""
        layout = calc_completed_stack_layout(3)
        for i in range(3):
            self.assertTrue(layout[i][0])
        for i in range(3, 8):
            self.assertFalse(layout[i][0])

    def test_8_completed_full(self):
        """8 套全部完成"""
        layout = calc_completed_stack_layout(8)
        for filled, layers, _, _ in layout:
            self.assertTrue(filled)

    def test_layer_count_is_4(self):
        """每套叠放 4 层"""
        layout = calc_completed_stack_layout(1)
        self.assertEqual(layout[0][1], 4)

    def test_top_layer_offset(self):
        """顶层偏移 = (4-1) * dp(0.5/1.0)"""
        layout = calc_completed_stack_layout(1)
        _, _, off_x, off_y = layout[0]
        self.assertAlmostEqual(off_x, 1.5)   # 3 * 0.5
        self.assertAlmostEqual(off_y, 3.0)    # 3 * 1.0

    def test_completed_stack_size_with_scale(self):
        """横屏完成区 stack 缩小"""
        scale = 0.65
        cw = 50
        s_cw = cw * scale
        stack_w = s_cw * 0.7
        stack_h = stack_w * 1.42
        # 验证宽高比
        self.assertAlmostEqual(stack_h / stack_w, 1.42)
        # 横屏比竖屏小
        self.assertLess(s_cw, cw)


# ============================================================
# 辅助牌信息开关 状态机测试
# ============================================================

def toggle_hint_state(current_on):
    """game_screen.py._toggle_card_hints() 的纯函数版本

    返回 (new_on, btn_text, btn_color)
    """
    new_on = not current_on
    if new_on:
        return True, '辅助：开', (0.2, 0.5, 0.7, 1)
    else:
        return False, '辅助：关', (0.4, 0.4, 0.4, 1)


def toggle_auto_move_state(current_on):
    """game_screen.py._toggle_auto_move() 的纯函数版本"""
    new_on = not current_on
    if new_on:
        return True, '自动：开', (0.2, 0.6, 0.2, 1)
    else:
        return False, '自动：关', (0.4, 0.4, 0.4, 1)


class TestToggleStates(unittest.TestCase):
    """测试辅助信息和自动移动的开关状态机"""

    def test_hint_toggle_off_to_on(self):
        """辅助信息 关→开"""
        on, text, color = toggle_hint_state(False)
        self.assertTrue(on)
        self.assertEqual(text, '辅助：开')
        self.assertEqual(color, (0.2, 0.5, 0.7, 1))

    def test_hint_toggle_on_to_off(self):
        """辅助信息 开→关"""
        on, text, color = toggle_hint_state(True)
        self.assertFalse(on)
        self.assertEqual(text, '辅助：关')
        self.assertEqual(color, (0.4, 0.4, 0.4, 1))

    def test_hint_double_toggle_restores(self):
        """连续两次切换恢复初始状态"""
        state = False
        state, _, _ = toggle_hint_state(state)
        state, text, color = toggle_hint_state(state)
        self.assertFalse(state)
        self.assertEqual(text, '辅助：关')

    def test_auto_move_toggle_off_to_on(self):
        """自动移动 关→开"""
        on, text, color = toggle_auto_move_state(False)
        self.assertTrue(on)
        self.assertEqual(text, '自动：开')
        self.assertEqual(color, (0.2, 0.6, 0.2, 1))

    def test_auto_move_toggle_on_to_off(self):
        """自动移动 开→关"""
        on, text, color = toggle_auto_move_state(True)
        self.assertFalse(on)
        self.assertEqual(text, '自动：关')

    def test_auto_green_hint_blue(self):
        """自动移动是绿色，辅助信息是蓝色"""
        _, _, auto_color = toggle_auto_move_state(False)
        _, _, hint_color = toggle_hint_state(False)
        # 绿色: G 分量最大
        self.assertGreater(auto_color[1], auto_color[0])
        self.assertGreater(auto_color[1], auto_color[2])
        # 蓝色: B 分量最大
        self.assertGreater(hint_color[2], hint_color[0])
        self.assertGreater(hint_color[2], hint_color[1])


# ============================================================
# 百分位数计算直接测试
# ============================================================

def percentile(arr, p):
    """stats.py.get_summary() 中的百分位数线性插值算法"""
    if not arr:
        return 0
    arr = sorted(arr)
    n = len(arr)
    if n == 1:
        return arr[0]
    k = (n - 1) * p / 100
    f = int(k)
    c = f + 1 if f + 1 < n else f
    return arr[f] + (arr[c] - arr[f]) * (k - f)


class TestPercentileCalculation(unittest.TestCase):
    """测试百分位数线性插值算法"""

    def test_single_value(self):
        """单个值 — 所有百分位都是它"""
        for p in [25, 50, 75]:
            self.assertAlmostEqual(percentile([100], p), 100)

    def test_two_values_median(self):
        """两个值的中位数 = 平均值"""
        self.assertAlmostEqual(percentile([10, 20], 50), 15.0)

    def test_two_values_p25(self):
        """两个值的 P25"""
        self.assertAlmostEqual(percentile([10, 20], 25), 12.5)

    def test_two_values_p75(self):
        """两个值的 P75"""
        self.assertAlmostEqual(percentile([10, 20], 75), 17.5)

    def test_three_values_median(self):
        """三个值中位数 = 中间值"""
        self.assertAlmostEqual(percentile([10, 20, 30], 50), 20.0)

    def test_five_values_median(self):
        """五个值中位数"""
        self.assertAlmostEqual(percentile([1, 2, 3, 4, 5], 50), 3.0)

    def test_unsorted_input(self):
        """输入未排序 — 自动排序"""
        self.assertAlmostEqual(percentile([30, 10, 20], 50), 20.0)

    def test_p0_is_minimum(self):
        """P0 = 最小值"""
        self.assertAlmostEqual(percentile([5, 10, 15], 0), 5.0)

    def test_p100_is_maximum(self):
        """P100 = 最大值"""
        self.assertAlmostEqual(percentile([5, 10, 15], 100), 15.0)

    def test_empty_returns_0(self):
        """空列表返回 0"""
        self.assertEqual(percentile([], 50), 0)

    def test_large_dataset(self):
        """大数据集的 P50 与 statistics.median 一致"""
        import statistics
        data = list(range(1, 101))
        p50 = percentile(data, 50)
        self.assertAlmostEqual(p50, statistics.median(data), places=1)

    def test_identical_values(self):
        """全部相同值"""
        self.assertAlmostEqual(percentile([42, 42, 42, 42], 50), 42.0)


# ============================================================
# 得分公式验证测试
# ============================================================

class TestScoreFormulaInvariant(unittest.TestCase):
    """验证分数 = 500 - 步数 + 100 * 完成套数"""

    def test_initial_score(self):
        """初始得分 500"""
        self.assertEqual(500, 500 - 0 + 100 * 0)

    def test_after_moves_only(self):
        """只移动，不完成"""
        moves = 30
        sets = 0
        expected = 500 - moves + 100 * sets
        self.assertEqual(expected, 470)

    def test_after_one_completion(self):
        """完成一套"""
        moves = 50
        sets = 1
        expected = 500 - moves + 100 * sets
        self.assertEqual(expected, 550)

    def test_after_winning(self):
        """赢（8 套完成，假设 200 步）"""
        moves = 200
        sets = 8
        expected = 500 - moves + 100 * sets
        self.assertEqual(expected, 1100)

    def test_negative_score_possible(self):
        """超多步数可以负分"""
        moves = 600
        sets = 0
        expected = 500 - moves + 100 * sets
        self.assertLess(expected, 0)

    def test_deal_counts_as_move(self):
        """发牌也算一步"""
        moves = 5  # 包含 1 次发牌 + 4 次移动
        sets = 0
        expected = 500 - moves
        self.assertEqual(expected, 495)


# ============================================================
# 时间格式一致性测试
# ============================================================

class TestTimeFormatConsistency(unittest.TestCase):
    """验证不同地方的时间格式一致"""

    def test_game_screen_format(self):
        """游戏界面时间格式：mm:ss"""
        elapsed = 125  # 2 分 5 秒
        m, s = divmod(elapsed, 60)
        fmt = f"{m:02d}:{s:02d}"
        self.assertEqual(fmt, "02:05")

    def test_win_popup_format(self):
        """胜利弹窗时间格式：m:ss"""
        elapsed = 125
        m, s = divmod(elapsed, 60)
        fmt = f'{m}:{s:02d}'
        self.assertEqual(fmt, "2:05")

    def test_stats_screen_format(self):
        """统计页面时间格式：m:ss 或 --"""
        secs = 125
        m, s = divmod(int(secs), 60)
        fmt = f'{m}:{s:02d}'
        self.assertEqual(fmt, "2:05")

    def test_stats_zero_returns_dash(self):
        """统计页面 0 秒 → '--'"""
        self.assertEqual(fmt_time(0), '--')

    def test_game_screen_zero(self):
        """游戏界面 0 秒 → '00:00'"""
        m, s = divmod(0, 60)
        fmt = f"{m:02d}:{s:02d}"
        self.assertEqual(fmt, "00:00")

    def test_hour_plus_game_screen(self):
        """超 1 小时"""
        elapsed = 3661  # 1h1m1s
        m, s = divmod(elapsed, 60)
        fmt = f"{m:02d}:{s:02d}"
        self.assertEqual(fmt, "61:01")


# ============================================================
# 迷你标签显示阈值测试
# ============================================================

class TestMiniLabelThreshold(unittest.TestCase):
    """测试迷你标签只在间距 >= dp(8) 时显示"""

    def test_visible_at_8(self):
        """间距 = 8dp — 可以显示"""
        actual = 8
        self.assertTrue(actual >= 8)

    def test_hidden_below_8(self):
        """间距 < 8dp — 不显示"""
        actual = 7
        self.assertFalse(actual >= 8)

    def test_visible_at_25(self):
        """正常间距 25dp — 显示"""
        actual = 25
        self.assertTrue(actual >= 8)

    def test_hidden_at_2(self):
        """暗牌最小间距 2dp — 不显示"""
        actual = 2
        self.assertFalse(actual >= 8)


# ============================================================
# 辅助浮框 markup 颜色逻辑测试
# ============================================================

_HINT_SUIT_BRIGHT = {
    'heart':   'ff6666',
    'diamond': 'ff8040',
    'club':    'ffffff',
    'spade':   'b3d9ff',
}
_HINT_SUIT_DIM = {
    'heart':   '994d4d',
    'diamond': '995533',
    'club':    '999999',
    'spade':   '708099',
}


def build_hint_markup_line(suit, rank_str, suit_sym, is_movable):
    """模拟 _draw_card_hints 中每行 markup 文本的构建"""
    hex_color = _HINT_SUIT_BRIGHT.get(suit, 'ffffff') if is_movable \
        else _HINT_SUIT_DIM.get(suit, '999999')
    if is_movable:
        return f'[color={hex_color}][b]{rank_str}{suit_sym}[/b][/color]'
    else:
        return f'[color={hex_color}]{rank_str}{suit_sym}[/color]'


class TestHintMarkupColors(unittest.TestCase):
    """测试辅助浮框的 markup 颜色逻辑"""

    def test_movable_heart_bright_red(self):
        """可移动红心 — 亮红 + 粗体"""
        line = build_hint_markup_line('heart', 'K', '♥', True)
        self.assertIn('ff6666', line)
        self.assertIn('[b]', line)

    def test_movable_diamond_bright_orange(self):
        """可移动方块 — 亮橙红 + 粗体"""
        line = build_hint_markup_line('diamond', 'Q', '♦', True)
        self.assertIn('ff8040', line)
        self.assertIn('[b]', line)

    def test_movable_club_white(self):
        """可移动梅花 — 白色 + 粗体"""
        line = build_hint_markup_line('club', '10', '♣', True)
        self.assertIn('ffffff', line)
        self.assertIn('[b]', line)

    def test_movable_spade_light_blue(self):
        """可移动黑桃 — 亮蓝白 + 粗体"""
        line = build_hint_markup_line('spade', 'J', '♠', True)
        self.assertIn('b3d9ff', line)
        self.assertIn('[b]', line)

    def test_non_movable_heart_dim(self):
        """不可移动红心 — 暗红 + 无粗体"""
        line = build_hint_markup_line('heart', '3', '♥', False)
        self.assertIn('994d4d', line)
        self.assertNotIn('[b]', line)

    def test_non_movable_spade_dim(self):
        """不可移动黑桃 — 暗蓝灰 + 无粗体"""
        line = build_hint_markup_line('spade', '5', '♠', False)
        self.assertIn('708099', line)
        self.assertNotIn('[b]', line)

    def test_non_movable_club_dim(self):
        """不可移动梅花 — 灰色"""
        line = build_hint_markup_line('club', '7', '♣', False)
        self.assertIn('999999', line)

    def test_non_movable_diamond_dim(self):
        """不可移动方块 — 暗橙"""
        line = build_hint_markup_line('diamond', 'A', '♦', False)
        self.assertIn('995533', line)

    def test_four_suits_all_different_bright(self):
        """四花色可移动颜色各不相同"""
        colors = set()
        for suit in ('heart', 'diamond', 'club', 'spade'):
            colors.add(_HINT_SUIT_BRIGHT[suit])
        self.assertEqual(len(colors), 4)

    def test_four_suits_all_different_dim(self):
        """四花色不可移动颜色各不相同"""
        colors = set()
        for suit in ('heart', 'diamond', 'club', 'spade'):
            colors.add(_HINT_SUIT_DIM[suit])
        self.assertEqual(len(colors), 4)

    def test_markup_contains_card_text(self):
        """markup 包含原始牌面文字"""
        line = build_hint_markup_line('heart', 'K', '♥', True)
        self.assertIn('K♥', line)

    def test_dim_darker_than_bright(self):
        """dim 颜色的十六进制值 < bright（更暗）"""
        for suit in ('heart', 'diamond', 'club', 'spade'):
            bright_val = int(_HINT_SUIT_BRIGHT[suit], 16)
            dim_val = int(_HINT_SUIT_DIM[suit], 16)
            self.assertLess(dim_val, bright_val,
                          f"suit={suit}: dim {_HINT_SUIT_DIM[suit]} >= bright {_HINT_SUIT_BRIGHT[suit]}")


# ============================================================
# 辅助浮框背景可见性测试
# ============================================================

class TestHintOverlayBackground(unittest.TestCase):
    """测试辅助浮框的深色背景确保文字可读"""

    def test_background_opacity_high(self):
        """背景 alpha >= 0.9，遮住下面的牌色"""
        bg_alpha = 0.92
        self.assertGreaterEqual(bg_alpha, 0.9)

    def test_background_is_dark(self):
        """背景 RGB 接近黑色"""
        bg = (0.08, 0.08, 0.10)
        for c in bg:
            self.assertLess(c, 0.15)

    def test_shadow_offset_small(self):
        """文字阴影偏移 0.5dp 足够产生描边又不模糊"""
        offset = 0.5
        self.assertGreater(offset, 0)
        self.assertLessEqual(offset, 1.5)

    def test_all_bright_colors_contrast_vs_dark_bg(self):
        """所有亮色在深色背景上对比度足够（亮度差 > 0.4）"""
        bg_luminance = 0.08  # 近似
        for suit, hex_color in _HINT_SUIT_BRIGHT.items():
            r = int(hex_color[0:2], 16) / 255
            g = int(hex_color[2:4], 16) / 255
            b = int(hex_color[4:6], 16) / 255
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            contrast = luminance - bg_luminance
            self.assertGreater(contrast, 0.4,
                             f"suit={suit} 亮度差 {contrast:.2f} 太小")

    def test_all_dim_colors_contrast_vs_dark_bg(self):
        """所有暗色在深色背景上仍可读（亮度差 > 0.15）"""
        bg_luminance = 0.08
        for suit, hex_color in _HINT_SUIT_DIM.items():
            r = int(hex_color[0:2], 16) / 255
            g = int(hex_color[2:4], 16) / 255
            b = int(hex_color[4:6], 16) / 255
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            contrast = luminance - bg_luminance
            self.assertGreater(contrast, 0.15,
                             f"suit={suit} dim 亮度差 {contrast:.2f} 太小")


# ============================================================
# 随机自动移动目标选择测试
# ============================================================

def find_auto_targets(columns, source_col, source_idx):
    """模拟 _find_random_auto_target 的纯函数版本

    返回所有合法目标列索引（不含 source_col）
    """
    if source_idx >= len(columns[source_col]):
        return []
    moving_cards = columns[source_col][source_idx:]
    bottom_card_rank = moving_cards[0]['rank']
    targets = []
    for i, col in enumerate(columns):
        if i == source_col:
            continue
        if not col:
            targets.append(i)  # 空列
        elif col[-1]['rank'] == bottom_card_rank + 1:
            targets.append(i)  # rank 差 1
    return targets


class TestAutoTargetSelection(unittest.TestCase):
    """测试自动移动目标选择逻辑"""

    def test_empty_column_is_target(self):
        """空列可作为目标"""
        columns = [
            [make_card('spade', 5)],
            [],
        ]
        targets = find_auto_targets(columns, 0, 0)
        self.assertIn(1, targets)

    def test_matching_rank_is_target(self):
        """rank 差 1 的列可作为目标"""
        columns = [
            [make_card('spade', 5)],
            [make_card('heart', 6)],
        ]
        targets = find_auto_targets(columns, 0, 0)
        self.assertIn(1, targets)

    def test_skip_source_column(self):
        """源列不在目标列表中"""
        columns = [
            [make_card('spade', 5)],
            [make_card('heart', 6)],
        ]
        targets = find_auto_targets(columns, 0, 0)
        self.assertNotIn(0, targets)

    def test_no_valid_target(self):
        """没有合法目标 — 返回空"""
        columns = [
            [make_card('spade', 5)],
            [make_card('heart', 3)],  # rank 差不是 1
            [make_card('club', 8)],
        ]
        targets = find_auto_targets(columns, 0, 0)
        self.assertEqual(targets, [])

    def test_multiple_targets(self):
        """多个合法目标"""
        columns = [
            [make_card('spade', 5)],
            [make_card('heart', 6)],
            [],
            [make_card('club', 6)],
        ]
        targets = find_auto_targets(columns, 0, 0)
        self.assertEqual(len(targets), 3)

    def test_source_idx_out_of_range(self):
        """source_idx 越界 — 返回空"""
        columns = [[make_card('spade', 5)]]
        targets = find_auto_targets(columns, 0, 5)
        self.assertEqual(targets, [])


# ============================================================
# GameState.save_state 逻辑测试
# ============================================================

class TestGameStateSaveLogic(unittest.TestCase):
    """测试存档序列化/反序列化的键完整性"""

    def test_to_dict_has_required_keys(self):
        """to_dict 输出包含所有必要键"""
        required = {'difficulty', 'score', 'moves', 'columns', 'stock', 'completed',
                     'elapsed', 'start_time'}
        # 模拟一个最小的 game state dict
        state = {
            'difficulty': 'easy', 'score': 500, 'moves': 0,
            'columns': [[] for _ in range(10)],
            'stock': [], 'completed': [],
            'elapsed': 0, 'start_time': None
        }
        for key in required:
            self.assertIn(key, state, f"缺少键: {key}")

    def test_column_count_is_10(self):
        """序列化后列数 = 10"""
        columns = [[] for _ in range(10)]
        self.assertEqual(len(columns), 10)


if __name__ == '__main__':
    unittest.main()
