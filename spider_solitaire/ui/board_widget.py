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
from ..game.card import SUITS


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

        # 动画状态
        self._animating = False

        self.on_state_updated = None
        self.bind(size=self._on_resize)

    def _on_resize(self, *args):
        self.redraw()

    def set_game_state(self, gs):
        self.game_state = gs
        self.redraw()

    # ========== 计算动态卡牌尺寸 ==========

    def _calc_card_size(self):
        """根据屏幕宽度动态计算卡牌尺寸，确保 10 列一定能放下"""
        usable_w = self.width - 2 * MARGIN
        max_card_w = (usable_w - 9 * dp(2)) / 10  # 最小间距 dp(2)
        self._cw = min(dp(60), max(dp(30), max_card_w))
        self._ch = self._cw * 1.42  # 保持宽高比
        self._cr = self._cw * 0.067

    # ========== 绘制 ==========

    def redraw(self):
        if self.game_state is None:
            return

        self._clear_widgets()
        self.canvas.clear()

        with self.canvas:
            Color(*BACKGROUND_COLOR)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[0])

        self._calc_card_size()
        self._calc_column_positions()

        for col_idx in range(10):
            self._draw_column(col_idx)

        self._draw_stock()
        self._draw_completed()

    def _clear_widgets(self):
        for w in self._card_widgets + self._extra_widgets:
            if w.parent == self:
                self.remove_widget(w)
        self._card_widgets = []
        self._extra_widgets = []
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
    def _bottom_y(self):
        """牌列不能低于此 Y（给底部栏留空间）"""
        return self.y + self._ch * 0.4 + PADDING

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

        # 计算理想间距总和
        total_overlap = 0
        for i in range(n - 1):
            total_overlap += CARD_OVERLAP_OPEN if column[i].face_up else CARD_OVERLAP_CLOSED

        # 可用高度 = 从第一张牌顶部到底线，减去最后一张牌高度
        available = top_y - bottom_y
        if total_overlap > available:
            factor = available / total_overlap if total_overlap > 0 else 1
        else:
            factor = 1.0

        cy = top_y
        for i, card in enumerate(column):
            w = CardWidget(card_width=cw, card_height=ch, card_radius=self._cr)
            w.card = card
            w.pos = (col_x, cy)
            self.add_widget(w)
            self._card_widgets.append(w)
            self._card_map.append({
                'widget': w, 'col': col_idx, 'idx': i,
                'x': col_x, 'y': cy
            })

            if i < n - 1:
                overlap = CARD_OVERLAP_OPEN if card.face_up else CARD_OVERLAP_CLOSED
                cy -= overlap * factor

    def _draw_empty_slot(self, x, y):
        with self.canvas:
            Color(*EMPTY_SLOT_COLOR)
            Line(rounded_rectangle=(x, y, self._cw, self._ch, self._cr), width=1.5)

    def _draw_stock(self):
        gs = self.game_state
        cw, ch = self._cw, self._ch
        sx = self.x + self.width - MARGIN - cw
        sy = self.y + PADDING

        remaining = len(gs.stock) // 10

        if remaining > 0:
            with self.canvas:
                for i in range(min(remaining, 5)):
                    off = i * dp(2)
                    Color(*CARD_BACK_COLOR)
                    RoundedRectangle(pos=(sx - off, sy + off), size=(cw, ch), radius=[self._cr])
                Color(0.3, 0.35, 0.6, 1)
                Line(rounded_rectangle=(sx, sy, cw, ch, self._cr), width=1)

            # 中文"发牌"用 CJK 字体
            lbl_text = Label(
                text='发牌', font_name='CJK',
                font_size=FONT_SIZE_SMALL, color=(1, 1, 1, 1),
                size_hint=(None, None), size=(cw, ch * 0.5),
                pos=(sx, sy + ch * 0.4),
                halign='center', valign='middle'
            )
            lbl_text.text_size = lbl_text.size
            self.add_widget(lbl_text)
            self._extra_widgets.append(lbl_text)

            # 数字用默认字体
            lbl_num = Label(
                text=str(remaining),
                font_size=FONT_SIZE_SMALL, color=(1, 1, 1, 0.8),
                size_hint=(None, None), size=(cw, ch * 0.35),
                pos=(sx, sy + ch * 0.05),
                halign='center', valign='middle'
            )
            lbl_num.text_size = lbl_num.size
            self.add_widget(lbl_num)
            self._extra_widgets.append(lbl_num)
            self._stock_area = (sx, sy, cw, ch)
        else:
            self._stock_area = None

    def _draw_completed(self):
        gs = self.game_state
        done = len(gs.completed)
        cx = self.x + MARGIN
        cy = self.y + PADDING
        cw, ch = self._cw, self._ch

        # 每沓牌的位置参数（根据可用宽度自适应）
        avail_w = self.width - 2 * MARGIN - cw - dp(15)  # 减去发牌区宽度
        stack_gap = dp(3)
        stack_w = min(cw * 0.7, (avail_w - 7 * stack_gap - dp(35)) / 8)
        stack_w = max(stack_w, dp(20))
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

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False

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
            return False

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
        if touch.grab_current is not self:
            return False

        touch.ungrab(self)
        if not self._dragging:
            return False

        target = self._find_target_column(touch.x)
        gs = self.game_state

        moved = False
        if target is not None and target != self._drag_col:
            # 记录完成数，用于检测是否刚完成一组
            pre_done = len(gs.completed)
            moved = gs.move_cards(self._drag_col, self._drag_idx, target)

            if moved and len(gs.completed) > pre_done:
                # 刚完成了一组！播放收集动画
                self._dragging = False
                self._drag_col = None
                self._drag_idx = None
                self._play_complete_animation(target, len(gs.completed) - 1)
                return True

        self._dragging = False
        self._drag_col = None
        self._drag_idx = None
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
