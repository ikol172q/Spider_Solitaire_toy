"""游戏棋盘 Widget - 管理10列卡牌、待发牌、已完成区"""

from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.properties import ObjectProperty
from kivy.metrics import dp

from .theme import (
    CARD_OVERLAP_CLOSED, CARD_OVERLAP_OPEN,
    EMPTY_SLOT_COLOR, BACKGROUND_COLOR,
    FONT_SIZE_SMALL, PADDING, MARGIN,
    CARD_BACK_COLOR
)
from .card_widget import CardWidget


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

            lbl = Label(
                text=f'发牌\n({remaining})', font_name='CJK',
                font_size=FONT_SIZE_SMALL, color=(1, 1, 1, 1),
                size_hint=(None, None), size=(cw, ch), pos=(sx, sy),
                halign='center', valign='middle'
            )
            lbl.text_size = lbl.size
            self.add_widget(lbl)
            self._extra_widgets.append(lbl)
            self._stock_area = (sx, sy, cw, ch)
        else:
            self._stock_area = None

    def _draw_completed(self):
        gs = self.game_state
        done = len(gs.completed)
        cx = self.x + MARGIN
        cy = self.y + PADDING

        slot_w = self._cw * 0.45
        slot_h = self._ch * 0.3
        gap = dp(3)

        with self.canvas:
            for i in range(8):
                sx = cx + i * (slot_w + gap)
                Color(0.2, 0.7, 0.2, 0.9) if i < done else Color(1, 1, 1, 0.15)
                RoundedRectangle(pos=(sx, cy), size=(slot_w, slot_h), radius=[dp(2)])

        if done > 0:
            lbl = Label(
                text=f'{done}/8', font_size=FONT_SIZE_SMALL,
                color=(1, 1, 1, 0.8), size_hint=(None, None),
                size=(dp(30), slot_h),
                pos=(cx + 8 * (slot_w + gap) + gap, cy),
                halign='left', valign='middle'
            )
            lbl.text_size = lbl.size
            self.add_widget(lbl)
            self._extra_widgets.append(lbl)

    # ========== 触摸处理 ==========

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False

        # 1) 发牌区
        if self._stock_area:
            sx, sy, sw, sh = self._stock_area
            if sx <= touch.x <= sx + sw and sy <= touch.y <= sy + sh:
                if self.game_state.deal_row():
                    self.redraw()
                    self._notify_state_updated()
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

        moved = False
        if target is not None and target != self._drag_col:
            moved = self.game_state.move_cards(self._drag_col, self._drag_idx, target)

        self._dragging = False
        self._drag_col = None
        self._drag_idx = None
        self.redraw()

        if moved:
            self._notify_state_updated()
        return True

    def _find_target_column(self, tx):
        best = None
        best_dist = float('inf')
        cw = self._cw
        for i, cx in enumerate(self._column_positions):
            d = abs(tx - (cx + cw / 2))
            if d < best_dist and d < cw:
                best_dist = d
                best = i
        return best

    def _notify_state_updated(self):
        if self.on_state_updated:
            self.on_state_updated()
