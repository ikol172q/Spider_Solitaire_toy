"""游戏棋盘 Widget - 管理10列卡牌、待发牌、已完成区"""

from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.properties import ObjectProperty
from kivy.metrics import dp
from kivy.animation import Animation
from kivy.clock import Clock

from .theme import (
    CARD_OVERLAP_CLOSED, CARD_OVERLAP_OPEN,
    EMPTY_SLOT_COLOR, BACKGROUND_COLOR,
    FONT_SIZE_SMALL, PADDING, MARGIN,
    CARD_BACK_COLOR, RED_SUIT_COLOR, BLACK_SUIT_COLOR
)
from .card_widget import CardWidget
from ..game.card import SUITS, RANK_NAMES


class BoardWidget(Widget):
    """游戏棋盘 Widget"""

    game_state = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_state = kwargs.get('game_state', None)
        self._card_widgets = []
        self._extra_widgets = []
        self._column_positions = []
        self._stock_area = None
        self._card_map = []

        # 动态尺寸（在 redraw 时根据屏幕宽度计算）
        self._cw = dp(60)   # 卡牌宽
        self._ch = dp(85)   # 卡牌高
        self._cr = dp(4)    # 圆角

        # 拖拽状态
        self._dragging = False
        self._drag_col = None
        self._drag_idx = None
        self._drag_offset = (0, 0)

        # 点击自动移动
        self.auto_move_enabled = False
        self._touch_start_pos = None   # 记录 touch_down 位置
        self._TAP_THRESHOLD = dp(15)   # 移动 < 15dp 视为点击

        # 动画状态
        self._animating = False

        # 辅助牌信息浮框
        self.show_card_hints = False
        self._hint_widgets = []

        # 极度压缩列 — 长按可弹出详情
        self._compressed_cols = set()
        self._long_press_event = None
        self._long_press_popup = None

        self.on_state_updated = None
        self.bind(size=self._on_resize)

    def _on_resize(self, *args):
        # 旋转/缩放时取消进行中的动画、拖拽和长按，防止状态错乱
        self._cancel_long_press()
        self._dismiss_column_popup()
        if self._animating:
            from kivy.animation import Animation as _Anim
            _Anim.cancel_all(self)
            for w in self._card_widgets:
                _Anim.cancel_all(w)
            self._animating = False
        if self._dragging:
            self._dragging = False
            self._drag_col = None
            self._drag_idx = None
            self._touch_start_pos = None
        self.redraw()

    def set_game_state(self, gs):
        self.game_state = gs
        self.redraw()

    # ========== 计算动态卡牌尺寸 ==========

    def _calc_card_size(self):
        """根据屏幕宽度和高度动态计算卡牌尺寸

        竖屏时主要受宽度约束，横屏时同时考虑高度约束：
        - 宽度约束：10 列 + 间距必须放下
        - 高度约束：牌高 + 底部区域 + padding 不能超过可用高度的一半
        取两者较小值。
        """
        usable_w = self.width - 2 * MARGIN
        max_card_w = (usable_w - 9 * dp(2)) / 10  # 宽度约束

        # 横屏时卡牌更扁（1.15），竖屏保持标准（1.42）
        is_landscape = self.width > self.height
        self._aspect = 1.15 if is_landscape else 1.42

        # 高度约束：ch=cw*aspect, 需要 ch + ch*0.4 + dp(20) <= height*0.5
        max_card_w_h = (self.height * 0.5 - dp(20)) / (self._aspect * 1.4)

        self._cw = min(dp(60), max(dp(30), min(max_card_w, max_card_w_h)))
        self._ch = self._cw * self._aspect
        self._cr = self._cw * 0.067

    # ========== 绘制 ==========

    def redraw(self):
        if self.game_state is None:
            return

        self._clear_widgets()
        self.canvas.clear()
        self._compressed_cols = set()

        with self.canvas:
            Color(*BACKGROUND_COLOR)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[0])

        self._calc_card_size()
        self._calc_column_positions()

        for col_idx in range(10):
            self._draw_column(col_idx)

        self._draw_stock()
        self._draw_completed()

        if self.show_card_hints and self.width > self.height:
            self._draw_card_hints()

    def _clear_widgets(self):
        for w in self._card_widgets + self._extra_widgets + self._hint_widgets:
            if w.parent == self:
                self.remove_widget(w)
        self._card_widgets = []
        self._extra_widgets = []
        self._hint_widgets = []
        self._card_map = []

    def _calc_column_positions(self):
        usable_w = self.width - 2 * MARGIN
        cw = self._cw
        gap = max(dp(1), (usable_w - 10 * cw) / 9) if usable_w > 10 * cw else dp(1)

        # 如果还是放不下，缩小留白
        total = 10 * cw + 9 * gap
        start_x = self.x + (self.width - total) / 2

        self._column_positions = []
        x = start_x
        for _ in range(10):
            self._column_positions.append(x)
            x += cw + gap

    @property
    def _top_y(self):
        """第一张牌顶部 Y 坐标"""
        return self.y + self.height - dp(10) - self._ch

    @property
    def _bottom_area_scale(self):
        """横屏时底部完成区/发牌区缩小系数"""
        return 0.65 if self.width > self.height else 1.0

    @property
    def _bottom_y(self):
        """牌列不能低于此 Y（给底部栏留空间）"""
        scale = self._bottom_area_scale
        return self.y + self._ch * 0.4 * scale + PADDING

    def _find_movable_start(self, column):
        """找到列中可移动序列的起始索引（从底部往上找同花色递减段）"""
        n = len(column)
        if n == 0:
            return n
        # 从最后一张牌往上扫描
        start = n - 1
        while start > 0:
            prev = column[start - 1]
            curr = column[start]
            if (prev.face_up and curr.face_up
                    and prev.suit == curr.suit
                    and prev.rank == curr.rank + 1):
                start -= 1
            else:
                break
        return start

    def _calc_column_overlaps(self, column, available):
        """分阶段计算每张牌的实际重叠距离

        策略：
        1. 先用理想间距（暗牌 overlap_closed, 亮牌 overlap_open）
        2. 如果总间距超出可用高度，优先压缩暗牌（最低到 dp(2)）
        3. 暗牌压到极限仍不够时，再等比压缩亮牌
        4. 亮牌最低不低于 dp(9)，保证可拖拽

        返回: list[float] — 每张牌(除最后一张)的实际间距
        """
        n = len(column)
        if n <= 1:
            return []

        is_landscape = self.width > self.height
        if is_landscape:
            ideal_closed = CARD_OVERLAP_CLOSED * 0.3
            ideal_open = CARD_OVERLAP_OPEN * 0.85
        else:
            ideal_closed = CARD_OVERLAP_CLOSED
            ideal_open = CARD_OVERLAP_OPEN

        min_closed = dp(2)  # 暗牌最小间距
        min_open = dp(9)    # 亮牌最小间距（保证可拖拽）

        # 统计暗牌/亮牌数量（不含最后一张）
        closed_count = sum(1 for i in range(n - 1) if not column[i].face_up)
        open_count = (n - 1) - closed_count

        ideal_total = closed_count * ideal_closed + open_count * ideal_open

        if ideal_total <= available:
            # 理想间距放得下，不需要压缩
            return [ideal_open if column[i].face_up else ideal_closed
                    for i in range(n - 1)]

        # ---- 第一阶段：先压缩暗牌 ----
        # 计算如果暗牌压到极限，亮牌保持理想间距是否放得下
        open_total = open_count * ideal_open
        remaining_for_closed = available - open_total

        if remaining_for_closed >= closed_count * min_closed:
            # 暗牌部分压缩即可，亮牌不动
            closed_each = remaining_for_closed / closed_count if closed_count > 0 else 0
            return [ideal_open if column[i].face_up else closed_each
                    for i in range(n - 1)]

        # ---- 第二阶段：暗牌已到极限，开始压缩亮牌 ----
        actual_closed = min_closed
        remaining_for_open = available - closed_count * actual_closed

        if open_count == 0:
            # 全是暗牌
            each = available / (n - 1) if n > 1 else 0
            return [max(min_closed, each)] * (n - 1)

        open_each = remaining_for_open / open_count if open_count > 0 else 0
        open_each = max(min_open, open_each)

        return [open_each if column[i].face_up else actual_closed
                for i in range(n - 1)]

    def _draw_column(self, col_idx):
        column = self.game_state.columns[col_idx]
        col_x = self._column_positions[col_idx]
        top_y = self._top_y
        bottom_y = self._bottom_y
        cw, ch = self._cw, self._ch

        if not column:
            self._draw_empty_slot(col_x, top_y)
            return

        n = len(column)
        is_landscape = self.width > self.height
        available = top_y - bottom_y

        # 分阶段计算每张牌的间距
        overlaps = self._calc_column_overlaps(column, available)

        # 判断列是否处于极度压缩状态（用于长按提示）
        if overlaps:
            avg_open = 0
            open_count = 0
            for i, ov in enumerate(overlaps):
                if column[i].face_up:
                    avg_open += ov
                    open_count += 1
            if open_count > 0:
                avg_open /= open_count
                if avg_open < dp(14):
                    # 标记此列为高度压缩，供长按弹出使用
                    if not hasattr(self, '_compressed_cols'):
                        self._compressed_cols = set()
                    self._compressed_cols.add(col_idx)

        # 找出可移动序列起始索引（用于低亮不可移动的牌）
        movable_start = self._find_movable_start(column)

        cy = top_y
        for i, card in enumerate(column):
            w = CardWidget(card_width=cw, card_height=ch, card_radius=self._cr,
                           compact=is_landscape)
            w.card = card

            # 翻开但不在可移动序列中 → 低亮
            if card.face_up and i < movable_start:
                w.dimmed = True

            w.pos = (col_x, cy)
            self.add_widget(w)
            self._card_widgets.append(w)
            self._card_map.append({
                'widget': w, 'col': col_idx, 'idx': i,
                'x': col_x, 'y': cy
            })

            if i < n - 1:
                actual = overlaps[i]

                # 在被压住的翻开牌的露出区域添加迷你 rank+suit 标签
                if card.face_up and is_landscape and actual >= dp(8):
                    self._draw_mini_label(card, col_x, cy, cw, actual)

                cy -= actual

    def _draw_mini_label(self, card, col_x, card_y, cw, visible_h):
        """在被压住的翻开牌的露出条上绘制迷你 rank+suit"""
        rank_str = RANK_NAMES[card.rank]
        suit_sym = SUITS[card.suit]
        text = f'{rank_str}{suit_sym}'

        if card.suit in ('heart', 'diamond'):
            color = RED_SUIT_COLOR
        else:
            color = BLACK_SUIT_COLOR

        font_sz = max(dp(8), min(visible_h * 0.75, cw * 0.22))
        lbl = Label(
            text=text,
            font_size=font_sz,
            color=color,
            size_hint=(None, None),
            size=(cw * 0.55, visible_h),
            pos=(col_x + cw * 0.42, card_y + (self._ch - visible_h)),
            halign='right', valign='top',
            bold=True
        )
        lbl.text_size = lbl.size
        self.add_widget(lbl)
        self._extra_widgets.append(lbl)

    def _draw_empty_slot(self, x, y):
        with self.canvas:
            Color(*EMPTY_SLOT_COLOR)
            Line(rounded_rectangle=(x, y, self._cw, self._ch, self._cr), width=1.5)

    def _draw_stock(self):
        gs = self.game_state
        cw, ch = self._cw, self._ch
        scale = self._bottom_area_scale
        s_cw = cw * scale
        s_ch = ch * scale
        s_cr = self._cr * scale
        sx = self.x + self.width - MARGIN - s_cw
        sy = self.y + PADDING

        remaining = len(gs.stock) // 10

        if remaining > 0:
            with self.canvas:
                for i in range(min(remaining, 5)):
                    off = i * dp(2) * scale
                    Color(*CARD_BACK_COLOR)
                    RoundedRectangle(pos=(sx - off, sy + off), size=(s_cw, s_ch), radius=[s_cr])
                Color(0.3, 0.35, 0.6, 1)
                Line(rounded_rectangle=(sx, sy, s_cw, s_ch, s_cr), width=1)

            # 中文"发牌"用 CJK 字体（字体不随 scale 缩太多）
            _fs = FONT_SIZE_SMALL * 1.2
            lbl_text = Label(
                text='发牌', font_name='CJK',
                font_size=_fs, color=(1, 1, 1, 1),
                size_hint=(None, None), size=(s_cw, s_ch * 0.5),
                pos=(sx, sy + s_ch * 0.4),
                halign='center', valign='middle'
            )
            lbl_text.text_size = lbl_text.size
            self.add_widget(lbl_text)
            self._extra_widgets.append(lbl_text)

            # 数字用默认字体
            lbl_num = Label(
                text=str(remaining),
                font_size=_fs, color=(1, 1, 1, 0.8),
                size_hint=(None, None), size=(s_cw, s_ch * 0.35),
                pos=(sx, sy + s_ch * 0.05),
                halign='center', valign='middle'
            )
            lbl_num.text_size = lbl_num.size
            self.add_widget(lbl_num)
            self._extra_widgets.append(lbl_num)
            # 触摸区域稍微放大以便点击
            self._stock_area = (sx - dp(5), sy - dp(5), s_cw + dp(10), s_ch + dp(10))
        else:
            self._stock_area = None

    def _draw_completed(self):
        gs = self.game_state
        done = len(gs.completed)
        cx = self.x + MARGIN
        cy = self.y + PADDING
        cw, ch = self._cw, self._ch
        scale = self._bottom_area_scale

        # 每沓牌的位置参数（根据可用宽度自适应）
        s_cw = cw * scale
        avail_w = self.width - 2 * MARGIN - s_cw - dp(15)  # 减去发牌区宽度
        stack_gap = dp(3) * scale
        stack_w = min(s_cw * 0.7, (avail_w - 7 * stack_gap - dp(35)) / 8)
        stack_w = max(stack_w, dp(15))
        stack_h = stack_w * 1.42  # 保持牌的宽高比

        # 记录完成区位置供动画使用
        self._completed_positions = []

        with self.canvas:
            for i in range(8):
                sx = cx + i * (stack_w + stack_gap)
                self._completed_positions.append((sx, cy))
                if i < done:
                    # 画一沓叠放的牌（3-4 张偏移营造厚度感）
                    layers = min(4, 13)
                    for j in range(layers):
                        off_x = j * dp(0.5)
                        off_y = j * dp(1)
                        Color(1, 1, 1, 1)
                        RoundedRectangle(
                            pos=(sx + off_x, cy + off_y),
                            size=(stack_w, stack_h),
                            radius=[self._cr * 0.6])
                    # 最上面一层画边框
                    top_x = sx + (layers - 1) * dp(0.5)
                    top_y = cy + (layers - 1) * dp(1)
                    Color(0.2, 0.6, 0.2, 1)
                    Line(rounded_rectangle=(
                        top_x, top_y, stack_w, stack_h, self._cr * 0.6
                    ), width=1.2)

                    # 在最上层显示 "A" + 花色符号（颜色与花色匹配）
                    suit = gs.completed[i][0].suit  # K→A 序列，第一张是 K
                    suit_sym = SUITS[suit]
                    suit_color = RED_SUIT_COLOR if suit in ('heart', 'diamond') else BLACK_SUIT_COLOR
                    lbl_a = Label(
                        text=f'A\n{suit_sym}',
                        font_size=stack_w * 0.40,
                        color=suit_color,
                        size_hint=(None, None),
                        size=(stack_w, stack_h),
                        pos=(top_x, top_y),
                        halign='center', valign='middle',
                        bold=True, line_height=0.85
                    )
                    lbl_a.text_size = lbl_a.size
                    self.add_widget(lbl_a)
                    self._extra_widgets.append(lbl_a)
                else:
                    # 空位虚线框
                    Color(1, 1, 1, 0.15)
                    Line(rounded_rectangle=(
                        sx, cy, stack_w, stack_h, self._cr * 0.6
                    ), width=1)

        # 显示 "done/8" 数字标签
        lbl = Label(
            text=f'{done}/8', font_size=FONT_SIZE_SMALL * 1.2,
            color=(1, 1, 1, 0.9), size_hint=(None, None),
            size=(dp(35), stack_h),
            pos=(cx + 8 * (stack_w + stack_gap) + stack_gap, cy),
            halign='left', valign='middle'
        )
        lbl.text_size = lbl.size
        self.add_widget(lbl)
        self._extra_widgets.append(lbl)

    # ========== 辅助牌信息浮框（横屏专用）==========

    def _draw_card_hints(self):
        """在每列上方绘制半透明浮框，显示该列所有翻开牌的 rank+suit

        浮框覆盖在暗牌区域上，用虚线边框 + 半透明底色。
        仅在横屏 + show_card_hints=True 时调用。
        """
        gs = self.game_state
        if not gs:
            return

        cw = self._cw
        hint_font = max(dp(9), cw * 0.22)

        for col_idx in range(10):
            column = gs.columns[col_idx]
            if not column:
                continue

            # 收集翻开的牌（带索引）
            face_up_cards = [(i, c) for i, c in enumerate(column) if c.face_up]
            if not face_up_cards:
                continue

            movable_start = self._find_movable_start(column)

            # 四花色亮色方案（与弹窗一致）
            _suit_bright = {
                'heart':   'ff6666',   # 亮红
                'diamond': 'ff8040',   # 亮橙红
                'club':    'ffffff',   # 白色
                'spade':   'b3d9ff',   # 亮蓝白
            }
            _suit_dim = {
                'heart':   '994d4d',   # 暗红
                'diamond': '995533',   # 暗橙
                'club':    '999999',   # 灰
                'spade':   '708099',   # 暗蓝灰
            }

            # 构建 markup 文本：每张牌一行，颜色按花色+可移动性
            lines = []
            for idx, c in face_up_cards:
                rank_str = RANK_NAMES[c.rank]
                suit_sym = SUITS[c.suit]
                is_movable = idx >= movable_start
                hex_color = _suit_bright.get(c.suit, 'ffffff') if is_movable \
                    else _suit_dim.get(c.suit, '999999')
                if is_movable:
                    lines.append(f'[color={hex_color}][b]{rank_str}{suit_sym}[/b][/color]')
                else:
                    lines.append(f'[color={hex_color}]{rank_str}{suit_sym}[/color]')
            hint_text = '\n'.join(lines)

            col_x = self._column_positions[col_idx]
            top_y = self._top_y

            # 浮框高度：每行约 hint_font*1.2，最小 cw*0.5
            line_h = hint_font * 1.2
            box_h = max(cw * 0.5, len(lines) * line_h + dp(4))
            # 浮框宽度 = 卡牌宽度
            box_w = cw
            # 位置：紧贴在列的最顶部牌上方
            box_x = col_x
            box_y = top_y + self._ch + dp(2)
            # 如果超出 widget 顶部，往下移
            if box_y + box_h > self.y + self.height - dp(2):
                box_y = self.y + self.height - dp(2) - box_h

            # 画深色不透明背景 + 虚线边框（确保遮住底下的牌色）
            with self.canvas:
                Color(0.08, 0.08, 0.10, 0.92)
                RoundedRectangle(pos=(box_x, box_y), size=(box_w, box_h),
                                 radius=[dp(3)])
                Color(0.6, 0.7, 0.6, 0.7)
                Line(rounded_rectangle=(box_x, box_y, box_w, box_h, dp(3)),
                     width=1.2, dash_length=4, dash_offset=3)

            # 文字标签（启用 markup 以支持逐行着色）
            # 加 [s] 模拟描边：先画一层黑色阴影，再画彩色文字
            shadow_lines = []
            for idx_c, c in face_up_cards:
                rank_str = RANK_NAMES[c.rank]
                suit_sym = SUITS[c.suit]
                shadow_lines.append(f'[color=111111]{rank_str}{suit_sym}[/color]')
            shadow_text = '\n'.join(shadow_lines)

            # 阴影层（偏移 1dp 制造描边效果）
            shadow_lbl = Label(
                text=shadow_text,
                font_size=hint_font,
                color=(0, 0, 0, 1),
                markup=True,
                size_hint=(None, None),
                size=(box_w, box_h),
                pos=(box_x + dp(0.5), box_y - dp(0.5)),
                halign='center', valign='middle',
                line_height=1.0
            )
            shadow_lbl.text_size = shadow_lbl.size
            self.add_widget(shadow_lbl)
            self._hint_widgets.append(shadow_lbl)

            # 前景文字层
            lbl = Label(
                text=hint_text,
                font_size=hint_font,
                color=(1, 1, 1, 0.95),
                markup=True,
                size_hint=(None, None),
                size=(box_w, box_h),
                pos=(box_x, box_y),
                halign='center', valign='middle',
                line_height=1.0
            )
            lbl.text_size = lbl.size
            self.add_widget(lbl)
            self._hint_widgets.append(lbl)

    # ========== 发牌动画 ==========

    def _deal_with_animation(self):
        """带飞牌动画的发牌"""
        gs = self.game_state
        if not gs or self._animating:
            return

        # 记录发牌前每列的牌数
        pre_counts = [len(col) for col in gs.columns]

        # 记录发牌堆位置
        stock_x = self.x + self.width - MARGIN - self._cw
        stock_y = self.y + PADDING

        # 执行发牌
        if not gs.deal_row():
            return

        # 先正常重绘（新牌已在列中）
        self.redraw()

        # 找到每列新发的那张牌（最后一张）
        fly_widgets = []
        fly_targets = []
        for col_idx in range(10):
            new_idx = pre_counts[col_idx]  # 新牌在列中的 index
            # 在 _card_map 中找到它
            for info in self._card_map:
                if info['col'] == col_idx and info['idx'] == new_idx:
                    fly_widgets.append(info['widget'])
                    fly_targets.append((info['x'], info['y']))
                    break

        if not fly_widgets:
            self._notify_state_updated()
            return

        # 把这些卡牌移到发牌堆位置（动画起点）
        self._animating = True
        for w in fly_widgets:
            w.pos = (stock_x, stock_y)

        # 逐张飞出，每张间隔 0.06 秒
        for i, (w, (tx, ty)) in enumerate(zip(fly_widgets, fly_targets)):
            delay = i * 0.06
            anim = Animation(x=tx, y=ty, duration=0.25, t='out_quad')
            if i == len(fly_widgets) - 1:
                # 最后一张动画完成时解除锁定
                anim.bind(on_complete=lambda *a: self._on_deal_anim_done())
            Clock.schedule_once(lambda dt, a=anim, ww=w: a.start(ww), delay)

    def _on_deal_anim_done(self):
        """发牌动画结束"""
        self._animating = False
        self._notify_state_updated()

    # ========== 完成收集动画 ==========

    def _play_complete_animation(self, col_idx, done_idx):
        """K→A 完成时，13 张牌依次飞向左下角完成区

        参数：
            col_idx: 完成序列所在的列
            done_idx: 在 completed 列表中的索引
        """
        gs = self.game_state
        cw, ch = self._cw, self._ch

        # 先 redraw 显示移除后的棋盘状态
        self.redraw()

        # 完成区目标位置
        if hasattr(self, '_completed_positions') and done_idx < len(self._completed_positions):
            target_x, target_y = self._completed_positions[done_idx]
        else:
            target_x = self.x + MARGIN + done_idx * (cw * 0.55 + dp(4))
            target_y = self.y + PADDING

        # 获取刚完成的 13 张牌
        completed_cards = gs.completed[done_idx]

        # 计算这 13 张牌在列中原来的位置（从该列顶部排列）
        col_x = self._column_positions[col_idx]
        top_y = self._top_y

        # 创建 13 张临时卡牌 widget，从列中原位置出发
        self._animating = True
        fly_widgets = []
        start_y = top_y

        for i, card in enumerate(completed_cards):
            w = CardWidget(card_width=cw, card_height=ch, card_radius=self._cr)
            w.card = card
            w.pos = (col_x, start_y - i * CARD_OVERLAP_OPEN * 0.6)
            self.add_widget(w)
            fly_widgets.append(w)

        # 逐张飞向完成区（从 A 开始，即 index 12 → 0）
        total = len(fly_widgets)
        for i in range(total - 1, -1, -1):
            w = fly_widgets[i]
            seq_i = total - 1 - i  # 飞行顺序：最后一张(A)先飞
            delay = seq_i * 0.04

            # 飞行到目标位置（逐渐缩小到完成区尺寸）
            target_w = cw * 0.55
            target_h = ch * 0.55
            anim = Animation(
                x=target_x, y=target_y,
                width=target_w, height=target_h,
                duration=0.35, t='in_out_quad'
            )

            if seq_i == total - 1:
                # 最后一个动画完成时清理
                def _finish(*a, widgets=fly_widgets):
                    for ww in widgets:
                        if ww.parent == self:
                            self.remove_widget(ww)
                    self._animating = False
                    self.redraw()
                    self._notify_state_updated()
                anim.bind(on_complete=_finish)

            Clock.schedule_once(lambda dt, a=anim, ww=w: a.start(ww), delay)

    # ========== 触摸处理 ==========

    def _cancel_long_press(self):
        """取消长按计时器"""
        if self._long_press_event:
            self._long_press_event.cancel()
            self._long_press_event = None

    def _dismiss_column_popup(self):
        """关闭列详情弹窗"""
        if self._long_press_popup:
            self._long_press_popup.dismiss()
            self._long_press_popup = None

    def _on_long_press(self, col_idx, touch_x, touch_y, dt):
        """长按触发：弹出该列的所有翻开牌详情"""
        self._long_press_event = None

        # 取消拖拽状态（长按不拖拽）
        if self._dragging:
            self._dragging = False
            self._drag_col = None
            self._drag_idx = None
            self._touch_start_pos = None
            # 恢复选中状态
            for info in self._card_map:
                info['widget'].selected = False
            self.redraw()

        gs = self.game_state
        if not gs or col_idx >= len(gs.columns):
            return

        column = gs.columns[col_idx]
        face_up_cards = [(i, c) for i, c in enumerate(column) if c.face_up]
        if not face_up_cards:
            return

        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.scrollview import ScrollView

        # 构建内容
        content = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(4))
        scroll = ScrollView(size_hint=(1, 1))
        inner = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))
        inner.bind(minimum_height=inner.setter('height'))

        movable_start = self._find_movable_start(column)

        for idx, card in face_up_cards:
            rank_str = RANK_NAMES[card.rank]
            suit_sym = SUITS[card.suit]
            text = f'{rank_str}{suit_sym}'

            # 深色背景上使用亮色文字（支持四花色）
            is_movable = idx >= movable_start
            # 四花色亮色方案
            suit_bright = {
                'heart':   (1.0, 0.4, 0.4, 1.0),    # 亮红
                'diamond': (1.0, 0.5, 0.25, 1.0),    # 亮橙红
                'club':    (1.0, 1.0, 1.0, 1.0),     # 白色
                'spade':   (0.7, 0.85, 1.0, 1.0),    # 亮蓝白
            }
            bright = suit_bright.get(card.suit, (1.0, 1.0, 1.0, 1.0))
            if is_movable:
                lbl_color = bright
            else:
                # 不可移动：保持同色系但降低亮度，alpha 0.8（比之前 0.55 亮很多）
                lbl_color = tuple(c * 0.6 for c in bright[:3]) + (0.8,)

            lbl = Label(
                text=text,
                font_size=dp(18) if is_movable else dp(15),
                color=lbl_color,
                size_hint_y=None, height=dp(26),
                bold=is_movable,
                halign='center', valign='middle'
            )
            lbl.text_size = (None, lbl.height)
            inner.add_widget(lbl)

        scroll.add_widget(inner)
        content.add_widget(scroll)

        # 弹窗（保持 Kivy 默认深色背景，用亮色文字）
        self._dismiss_column_popup()
        popup = Popup(
            title='', content=content,
            size_hint=(None, None),
            size=(dp(90), min(dp(300), len(face_up_cards) * dp(28) + dp(40))),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            auto_dismiss=True,
            separator_height=0
        )
        # 定位到触摸点附近
        popup.bind(on_open=lambda *a: setattr(
            popup, 'pos',
            (min(touch_x + dp(10), self.width - dp(100)),
             max(touch_y - popup.height / 2, dp(10)))
        ))
        self._long_press_popup = popup
        popup.open()

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False

        # 关闭已有的列详情弹窗
        self._dismiss_column_popup()

        # 动画进行中不处理触摸
        if self._animating:
            return True

        # 1) 发牌区
        if self._stock_area:
            sx, sy, sw, sh = self._stock_area
            if sx <= touch.x <= sx + sw and sy <= touch.y <= sy + sh:
                # 检查是否有空列
                if any(len(col) == 0 for col in self.game_state.columns):
                    self._show_hint('请先填满所有空列')
                else:
                    self._deal_with_animation()
                return True

        # 2) 找被点击的卡牌
        hit = None
        for info in reversed(self._card_map):
            w = info['widget']
            if w.collide_point(*touch.pos):
                hit = info
                break

        if hit is None:
            return False

        col, idx = hit['col'], hit['idx']
        card = self.game_state.columns[col][idx]

        if not card.face_up:
            return False

        seq = self.game_state.get_movable_sequence(col, idx)
        if seq is None:
            # 即使不可移动，如果列是压缩的，也启动长按检测
            if col in self._compressed_cols:
                self._cancel_long_press()
                self._long_press_event = Clock.schedule_once(
                    lambda dt: self._on_long_press(col, touch.x, touch.y, dt), 0.5)
                touch.grab(self)
            return False

        # 记录起始位置（用于区分点击 vs 拖拽）
        self._touch_start_pos = (touch.x, touch.y)

        # 启动长按计时器（0.5 秒）
        self._cancel_long_press()
        self._long_press_event = Clock.schedule_once(
            lambda dt: self._on_long_press(col, touch.x, touch.y, dt), 0.5)

        # 开始拖拽
        self._dragging = True
        self._drag_col = col
        self._drag_idx = idx
        self._drag_offset = (touch.x - hit['x'], touch.y - hit['y'])

        # ★ 关键：将拖拽的卡牌移到最上层（z-order）
        drag_infos = [info2 for info2 in self._card_map
                      if info2['col'] == col and info2['idx'] >= idx]
        for info2 in drag_infos:
            w = info2['widget']
            w.selected = True
            # remove 再 add → 移到 widget 树最后 → 画在最上面
            self.remove_widget(w)
            self.add_widget(w)

        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        # 手指移动 → 取消长按
        self._cancel_long_press()
        if self._animating:
            return True
        if touch.grab_current is not self or not self._dragging:
            return False

        ox, oy = self._drag_offset
        base_x = touch.x - ox
        base_y = touch.y - oy

        first = True
        prev_y = base_y
        for info in self._card_map:
            if info['col'] == self._drag_col and info['idx'] >= self._drag_idx:
                w = info['widget']
                if first:
                    w.pos = (base_x, base_y)
                    first = False
                else:
                    prev_y -= CARD_OVERLAP_OPEN
                    w.pos = (base_x, prev_y)
        return True

    def on_touch_up(self, touch):
        self._cancel_long_press()
        if touch.grab_current is not self:
            return False

        touch.ungrab(self)
        if not self._dragging:
            return False

        gs = self.game_state
        from_col = self._drag_col
        from_idx = self._drag_idx

        # 判断是否为"点击"（手指几乎没移动）
        is_tap = False
        if self._touch_start_pos and self.auto_move_enabled:
            sx, sy = self._touch_start_pos
            dist = ((touch.x - sx) ** 2 + (touch.y - sy) ** 2) ** 0.5
            is_tap = dist < self._TAP_THRESHOLD

        moved = False
        if is_tap:
            # 点击自动移动：随机选一个合法目标列
            target = self._find_random_auto_target(from_col, from_idx)
            if target is not None:
                # 记录牌飞行前的位置信息
                fly_infos = [
                    info for info in self._card_map
                    if info['col'] == from_col and info['idx'] >= from_idx
                ]
                src_positions = [(info['widget'], info['x'], info['y'])
                                 for info in fly_infos]

                # 记录牌在目标列的起始索引（move 之前）
                target_start_idx = len(gs.columns[target])

                pre_done = len(gs.completed)
                moved = gs.move_cards(from_col, from_idx, target)

                if moved and len(gs.completed) > pre_done:
                    self._dragging = False
                    self._drag_col = None
                    self._drag_idx = None
                    self._touch_start_pos = None
                    self._play_complete_animation(target, len(gs.completed) - 1)
                    return True

                if moved:
                    # 播放飞牌动画
                    self._dragging = False
                    self._drag_col = None
                    self._drag_idx = None
                    self._touch_start_pos = None
                    self._play_auto_move_animation(
                        src_positions, target, target_start_idx)
                    return True
        else:
            # 常规拖拽放置
            target = self._find_target_column(touch.x)
            if target is not None and target != from_col:
                pre_done = len(gs.completed)
                moved = gs.move_cards(from_col, from_idx, target)
                if moved and len(gs.completed) > pre_done:
                    self._dragging = False
                    self._drag_col = None
                    self._drag_idx = None
                    self._touch_start_pos = None
                    self._play_complete_animation(target, len(gs.completed) - 1)
                    return True

        self._dragging = False
        self._drag_col = None
        self._drag_idx = None
        self._touch_start_pos = None
        self.redraw()

        if moved:
            self._notify_state_updated()
        return True

    def _find_target_column(self, tx):
        """找到离松手位置最近的列，容差放宽到卡牌宽度的 2.5 倍"""
        best = None
        best_dist = float('inf')
        cw = self._cw
        tolerance = max(cw * 2.5, dp(80))  # 至少 80dp
        for i, cx in enumerate(self._column_positions):
            d = abs(tx - (cx + cw / 2))
            if d < best_dist and d < tolerance:
                best_dist = d
                best = i
        return best

    def _find_random_auto_target(self, from_col, card_idx):
        """为点击自动移动随机选一个合法目标列

        收集所有合法目标，随机选一个返回。如果无合法移动返回 None。
        """
        import random as _rnd
        gs = self.game_state
        if not gs:
            return None

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

    def _play_auto_move_animation(self, src_positions, target_col, card_idx):
        """点击自动移动的飞牌动画

        参数：
            src_positions: [(widget, src_x, src_y), ...] 原位置
            target_col: 目标列索引
            card_idx: 牌在目标列中的起始索引
        """
        self._animating = True

        # 先 redraw 得到新布局（牌已经在目标列了）
        self.redraw()

        # 在新 _card_map 中找到这些牌的目标位置
        gs = self.game_state
        target_infos = [
            info for info in self._card_map
            if info['col'] == target_col and info['idx'] >= card_idx
        ]

        if not target_infos or len(target_infos) != len(src_positions):
            # 安全回退：直接显示结果
            self._animating = False
            self._notify_state_updated()
            return

        # 把牌移到原始位置（动画起点）
        for (_, src_x, src_y), info in zip(src_positions, target_infos):
            info['widget'].pos = (src_x, src_y)

        # 逐张飞到目标位置
        total = len(target_infos)
        for i, ((_, _, _), info) in enumerate(zip(src_positions, target_infos)):
            w = info['widget']
            tx, ty = info['x'], info['y']
            anim = Animation(x=tx, y=ty, duration=0.2, t='out_quad')
            if i == total - 1:
                anim.bind(on_complete=lambda *a: self._on_auto_move_done())
            Clock.schedule_once(
                lambda dt, a=anim, ww=w: a.start(ww), i * 0.03)

    def _on_auto_move_done(self):
        """自动移动动画结束"""
        self._animating = False
        self._notify_state_updated()

    def _show_hint(self, text):
        """在屏幕中央短暂显示提示文字"""
        lbl = Label(
            text=text, font_name='CJK',
            font_size=FONT_SIZE_SMALL * 1.5,
            color=(1, 1, 0.6, 1),
            size_hint=(None, None),
            size=(self.width * 0.8, dp(40)),
            pos=(self.x + self.width * 0.1, self.y + self.height * 0.45),
            halign='center', valign='middle'
        )
        lbl.text_size = lbl.size
        self.add_widget(lbl)
        # 1.5 秒后自动消失
        def _remove(dt):
            if lbl.parent == self:
                self.remove_widget(lbl)
        Clock.schedule_once(_remove, 1.5)

    def _notify_state_updated(self):
        if self.on_state_updated:
            self.on_state_updated()
