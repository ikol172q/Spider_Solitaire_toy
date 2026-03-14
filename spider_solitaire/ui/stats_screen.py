"""统计界面 - 显示游戏历史记录"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle

from .theme import (
    BACKGROUND_COLOR, BUTTON_COLOR,
    FONT_SIZE_LARGE, FONT_SIZE_TITLE,
    FONT_SIZE_NORMAL, FONT_SIZE_SMALL, PADDING
)

CJK = 'CJK'


def _fmt_time(secs):
    """秒数格式化为 m:ss"""
    if secs <= 0:
        return '--'
    m, s = divmod(int(secs), 60)
    return f'{m}:{s:02d}'


class StatsScreen(Screen):
    """统计界面"""

    def __init__(self, game_stats=None, on_back=None, **kwargs):
        super().__init__(**kwargs)
        self.game_stats = game_stats
        self._on_back = on_back

        with self.canvas.before:
            Color(*BACKGROUND_COLOR)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        from kivy.uix.anchorlayout import AnchorLayout
        anchor = AnchorLayout(anchor_x='center', anchor_y='center')

        root = BoxLayout(orientation='vertical', padding=PADDING * 2, spacing=PADDING)
        self._stats_root = root

        # 标题
        root.add_widget(Label(
            text='历史记录', font_name=CJK,
            font_size=FONT_SIZE_LARGE * 1.5,
            color=(1, 1, 1, 1), bold=True,
            size_hint_y=0.08))

        # 滚动区域
        scroll = ScrollView(size_hint_y=0.82)
        self._content = BoxLayout(
            orientation='vertical', spacing=PADDING,
            size_hint_y=None, padding=[PADDING, 0])
        self._content.bind(minimum_height=self._content.setter('height'))
        scroll.add_widget(self._content)
        root.add_widget(scroll)

        # 返回按钮
        btn = Button(
            text='返回', font_name=CJK,
            font_size=FONT_SIZE_NORMAL * 1.3,
            background_color=BUTTON_COLOR,
            size_hint_y=0.08)
        btn.bind(on_press=lambda *a: self._back())
        root.add_widget(btn)

        anchor.add_widget(root)
        self.add_widget(anchor)
        self.bind(size=self._on_size)

    def _on_size(self, *a):
        is_landscape = self.width > self.height
        if hasattr(self, '_stats_root'):
            self._stats_root.size_hint_x = 0.6 if is_landscape else 1

    def on_enter(self):
        self._refresh()

    def _refresh(self):
        self._content.clear_widgets()
        if not self.game_stats:
            return

        # 全部统计
        self._add_section('全部')
        self._add_stats(self.game_stats.get_summary())

        # 按难度
        diff_names = [('easy', '初级'), ('medium', '中级'), ('hard', '高级')]
        for diff_key, diff_label in diff_names:
            s = self.game_stats.get_summary(diff_key)
            if s['total'] > 0:
                self._add_section(diff_label)
                self._add_stats(s)

    def _add_section(self, title):
        lbl = Label(
            text=title, font_name=CJK,
            font_size=FONT_SIZE_TITLE * 1.2,
            color=(0.6, 1, 0.6, 1), bold=True,
            size_hint_y=None, height=FONT_SIZE_TITLE * 2.5,
            halign='left', valign='bottom')
        lbl.text_size = (None, None)
        self._content.add_widget(lbl)

    def _add_stats(self, s):
        rows = [
            ('游玩次数', str(s['total'])),
            ('胜利次数', str(s['wins'])),
            ('胜率', f"{s['win_rate']}%"),
            ('最高分', str(s['best_score'])),
            ('最低分', str(s['worst_score'])),
            ('平均分', str(s['avg_score'])),
            ('平均步数', str(s['avg_moves'])),
            ('最快通关', _fmt_time(s['best_time'])),
            ('最慢通关', _fmt_time(s['worst_time'])),
            ('通关时间中位数', _fmt_time(s['time_p50'])),
        ]
        for label_txt, value_txt in rows:
            row = BoxLayout(
                orientation='horizontal',
                size_hint_y=None, height=FONT_SIZE_NORMAL * 2.5,
                spacing=PADDING)
            row.add_widget(Label(
                text=label_txt, font_name=CJK,
                font_size=FONT_SIZE_NORMAL,
                color=(0.85, 0.85, 0.85, 1),
                size_hint_x=0.55, halign='right', valign='middle'))
            row.children[0].text_size = row.children[0].size
            row.add_widget(Label(
                text=value_txt,
                font_size=FONT_SIZE_NORMAL * 1.1,
                color=(1, 1, 0.7, 1), bold=True,
                size_hint_x=0.45, halign='left', valign='middle'))
            row.children[0].text_size = row.children[0].size
            self._content.add_widget(row)

    def _upd_bg(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _back(self):
        if self._on_back:
            self._on_back()
