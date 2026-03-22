"""单张卡牌 Widget - 使用 Kivy Canvas + Label 绘制"""

from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.properties import ObjectProperty, BooleanProperty
from kivy.metrics import dp
from .theme import (
    CARD_COLOR, CARD_BACK_COLOR, RED_SUIT_COLOR, BLACK_SUIT_COLOR,
    CARD_WIDTH, CARD_HEIGHT, CARD_RADIUS, FONT_SIZE_SUIT,
    FONT_SIZE_SMALL, TEXT_COLOR, HIGHLIGHT_COLOR, SUIT_COLORS
)
from ..game.card import SUITS, RANK_NAMES


class CardWidget(Widget):
    """单张卡牌 Widget

    用 Canvas 绘制卡牌背景，用 Label 渲染文字（级别和花色符号）。
    支持动态尺寸：通过 card_width / card_height / card_radius 参数传入。
    """

    card = ObjectProperty(None, allownone=True)
    selected = BooleanProperty(False)
    dimmed = BooleanProperty(False)   # 低亮：已翻开但不可移动的牌

    def __init__(self, card_width=None, card_height=None, card_radius=None,
                 compact=False, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)

        # 使用传入的动态尺寸，或回退到 theme 默认值
        self._card_width = card_width if card_width is not None else CARD_WIDTH
        self._card_height = card_height if card_height is not None else CARD_HEIGHT
        self._card_radius = card_radius if card_radius is not None else CARD_RADIUS
        self._compact = compact   # 横屏紧凑模式：字体缩小

        self.size = (self._card_width, self._card_height)

        # 根据卡牌宽度直接计算字体大小
        cw = self._card_width
        if compact:
            self._font_rank = cw * 0.38
            self._font_suit = cw * 0.65
        else:
            self._font_rank = cw * 0.45
            self._font_suit = cw * 0.80

        # 文字 Label 引用
        self._rank_label = None
        self._center_label = None

        self.bind(card=self._redraw)
        self.bind(selected=self._redraw)
        self.bind(dimmed=self._redraw)
        self.bind(pos=self._redraw)
        self.bind(size=self._redraw)

    def _redraw(self, *args):
        """重绘卡牌"""
        # 清除旧内容
        self.canvas.clear()
        self._remove_labels()

        if self.card is None:
            return

        if self.card.face_up:
            self._draw_face()
        else:
            self._draw_back()

    def _remove_labels(self):
        """移除旧的 Label"""
        for lbl in (self._rank_label, self._center_label):
            if lbl and lbl.parent == self:
                self.remove_widget(lbl)
        self._rank_label = None
        self._center_label = None

    def _get_suit_color(self):
        """根据花色返回颜色"""
        return SUIT_COLORS.get(self.card.suit, BLACK_SUIT_COLOR)

    def _draw_face(self):
        """绘制卡牌正面"""
        r = self._card_radius
        dim = self.dimmed
        with self.canvas:
            # 背景：低亮时用浅灰色
            if dim:
                Color(0.82, 0.82, 0.80, 1)
            else:
                Color(*CARD_COLOR)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[r])

            # 选中高亮
            if self.selected:
                Color(*HIGHLIGHT_COLOR)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[r])

            # 边框
            Color(0.5, 0.5, 0.5, 1)
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, r), width=1)

        # 文字内容
        suit_sym = SUITS[self.card.suit]
        rank_name = RANK_NAMES[self.card.rank]
        base_color = self._get_suit_color()
        # 低亮时颜色变暗（保持足够对比度，WCAG AA 要求 4.5:1）
        # 灰色背景 (0.82,0.82,0.80) 上，文字需要足够深
        if dim:
            color = tuple(c * 0.35 + 0.15 for c in base_color[:3]) + (0.85,)
        else:
            color = base_color

        # 左上角：级别 + 花色
        self._rank_label = Label(
            text=f'{rank_name}\n{suit_sym}',
            font_size=self._font_rank,
            color=color,
            size_hint=(None, None),
            size=(self.width * 0.7, self.height * 0.5),
            pos=(self.x + dp(1), self.y + self.height * 0.48),
            halign='left',
            valign='top',
            bold=True,
            line_height=0.9
        )
        self._rank_label.text_size = self._rank_label.size
        self.add_widget(self._rank_label)

        # 中央大花色符号
        self._center_label = Label(
            text=suit_sym,
            font_size=self._font_suit,
            color=color,
            size_hint=(None, None),
            size=(self.width, self.height * 0.55),
            pos=(self.x, self.y + self.height * 0.02),
            halign='center',
            valign='middle'
        )
        self._center_label.text_size = self._center_label.size
        self.add_widget(self._center_label)

    def _draw_back(self):
        """绘制卡牌背面"""
        r = self._card_radius
        with self.canvas:
            # 深蓝色背景
            Color(*CARD_BACK_COLOR)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[r])

            # 内部浅色边框
            _inset = dp(3)
            Color(0.2, 0.25, 0.5, 1)
            Line(rounded_rectangle=(
                self.x + _inset, self.y + _inset,
                self.width - _inset * 2, self.height - _inset * 2, r
            ), width=1.5)

            # 交叉纹样
            _pad = dp(6)
            Color(0.15, 0.2, 0.45, 0.8)
            step = max(_pad, int(self._card_width / 8))
            x = self.x + _pad
            while x < self.x + self.width - _pad:
                Line(points=[x, self.y + _pad, x, self.y + self.height - _pad], width=1)
                x += step
            y = self.y + _pad
            while y < self.y + self.height - _pad:
                Line(points=[self.x + _pad, y, self.x + self.width - _pad, y], width=1)
                y += step

            # 选中高亮
            if self.selected:
                Color(*HIGHLIGHT_COLOR)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[r])

            # 外边框
            Color(0.3, 0.35, 0.6, 1)
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, r), width=1)
