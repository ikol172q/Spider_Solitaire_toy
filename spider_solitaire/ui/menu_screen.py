"""菜单界面 - 游戏标题 + 难度选择"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle

from .theme import (
    BACKGROUND_COLOR, BUTTON_COLOR, FONT_SIZE_LARGE,
    FONT_SIZE_TITLE, FONT_SIZE_NORMAL, PADDING
)

# 中文文本全部用 CJK 字体，纯 ASCII 用默认 Roboto
CJK = 'CJK'


class MenuScreen(Screen):
    """菜单界面"""

    def __init__(self, on_difficulty_selected=None, on_continue_game=None,
                 has_saved_game=False, **kwargs):
        super().__init__(**kwargs)
        self.on_difficulty_selected = on_difficulty_selected
        self.on_continue_game = on_continue_game

        # 背景
        with self.canvas.before:
            Color(*BACKGROUND_COLOR)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        # 主布局
        root = BoxLayout(orientation='vertical', padding=PADDING * 3, spacing=PADDING * 2)

        # ---- 标题 ----
        title_box = BoxLayout(orientation='vertical', size_hint_y=0.3, spacing=PADDING)
        title_box.add_widget(Label(
            text='蜘蛛纸牌', font_name=CJK,
            font_size=FONT_SIZE_LARGE * 1.5,
            color=(1, 1, 1, 1), bold=True, size_hint_y=0.6))
        title_box.add_widget(Label(
            text='Spider Solitaire', font_size=FONT_SIZE_TITLE,
            color=(0.8, 0.9, 0.8, 1), size_hint_y=0.4))
        root.add_widget(title_box)

        # ---- 难度选择 ----
        diff_box = BoxLayout(orientation='vertical', size_hint_y=0.5, spacing=PADDING * 2)
        diff_box.add_widget(Label(
            text='选择难度', font_name=CJK, font_size=FONT_SIZE_TITLE,
            color=(1, 1, 1, 0.8), size_hint_y=0.15))

        buttons = [
            ('初级：一种花色', 'easy'),
            ('中级：两种花色', 'medium'),
            ('高级：四种花色', 'hard'),
        ]
        for label, diff in buttons:
            btn = Button(
                text=label, font_name=CJK, font_size=FONT_SIZE_NORMAL,
                background_color=BUTTON_COLOR, size_hint_y=0.28)
            btn.bind(on_press=lambda _, d=diff: self._select(d))
            diff_box.add_widget(btn)

        root.add_widget(diff_box)

        # ---- 继续游戏 ----
        if has_saved_game:
            cont_btn = Button(
                text='继续上次游戏', font_name=CJK, font_size=FONT_SIZE_NORMAL,
                background_color=(0.2, 0.6, 0.2, 1), size_hint_y=0.1)
            cont_btn.bind(on_press=lambda _: self._continue())
            root.add_widget(cont_btn)
        else:
            root.add_widget(BoxLayout(size_hint_y=0.1))

        root.add_widget(BoxLayout(size_hint_y=0.1))
        self.add_widget(root)

    def _upd_bg(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _select(self, difficulty):
        if self.on_difficulty_selected:
            self.on_difficulty_selected(difficulty)

    def _continue(self):
        if self.on_continue_game:
            self.on_continue_game()
