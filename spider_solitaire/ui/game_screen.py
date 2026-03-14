"""游戏主界面 - 包含状态栏、棋盘、按钮栏"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle

from .board_widget import BoardWidget
from .theme import (
    STATUS_BAR_HEIGHT, BACKGROUND_COLOR, TEXT_COLOR, BUTTON_COLOR,
    FONT_SIZE_LARGE, FONT_SIZE_TITLE, FONT_SIZE_NORMAL, PADDING
)

CJK = 'CJK'


class GameScreen(Screen):
    """游戏主界面"""

    def __init__(self, game_state=None, on_menu_pressed=None,
                 on_game_won=None, **kwargs):
        super().__init__(**kwargs)
        self.game_state = game_state
        self._on_menu_cb = on_menu_pressed
        self._on_game_won = on_game_won
        self._timer_event = None
        self._win_shown = False

        root = BoxLayout(orientation='vertical')
        root.add_widget(self._build_status_bar())

        self.board = BoardWidget()
        self.board.size_hint = (1, 1)
        self.board.on_state_updated = self._refresh_labels
        root.add_widget(self.board)

        root.add_widget(self._build_button_bar())

        with self.canvas.before:
            Color(*BACKGROUND_COLOR)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        self.add_widget(root)
        if self.game_state:
            self.board.set_game_state(self.game_state)

    def _upd_bg(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    # ---- 状态栏（纯数字用默认字体，中文用 CJK）----
    def _build_status_bar(self):
        bar = BoxLayout(
            orientation='horizontal',
            size_hint_y=None, height=STATUS_BAR_HEIGHT,
            padding=PADDING, spacing=PADDING
        )
        gs = self.game_state
        score = gs.score if gs else 0
        moves = gs.moves if gs else 0

        # 纯数字/ASCII 内容 → 默认字体即可
        self.lbl_score = Label(
            text=str(score), font_size=FONT_SIZE_NORMAL,
            color=(1, 1, 1, 1), size_hint_x=0.25)
        self.lbl_moves = Label(
            text=str(moves), font_size=FONT_SIZE_NORMAL,
            color=(1, 1, 1, 1), size_hint_x=0.25)
        self.lbl_time = Label(
            text='00:00', font_size=FONT_SIZE_NORMAL,
            color=(1, 1, 1, 1), size_hint_x=0.25)

        diff_map = {'easy': '初级', 'medium': '中级', 'hard': '高级'}
        diff_txt = diff_map.get(gs.difficulty, '') if gs else ''
        self.lbl_diff = Label(
            text=diff_txt, font_name=CJK, font_size=FONT_SIZE_NORMAL,
            color=(1, 1, 1, 1), size_hint_x=0.25)

        bar.add_widget(self.lbl_score)
        bar.add_widget(self.lbl_moves)
        bar.add_widget(self.lbl_time)
        bar.add_widget(self.lbl_diff)
        return bar

    # ---- 按钮栏 ----
    def _build_button_bar(self):
        bar = BoxLayout(
            orientation='horizontal',
            size_hint_y=None, height=STATUS_BAR_HEIGHT,
            padding=PADDING, spacing=PADDING
        )
        for text, cb, w in [
            ('撤销', self._on_undo, 0.33),
            ('新游戏', self._on_new_game, 0.33),
            ('菜单', self._on_menu, 0.34),
        ]:
            btn = Button(text=text, font_name=CJK,
                         font_size=FONT_SIZE_NORMAL,
                         background_color=BUTTON_COLOR, size_hint_x=w)
            btn.bind(on_press=cb)
            bar.add_widget(btn)
        return bar

    # ---- 刷新 ----
    def _refresh_labels(self):
        gs = self.game_state
        if gs is None:
            return
        self.lbl_score.text = str(gs.score)
        self.lbl_moves.text = str(gs.moves)

    def _tick(self, dt):
        gs = self.game_state
        if gs is None:
            return
        gs.update_elapsed_time()
        m, s = divmod(gs.elapsed_time, 60)
        self.lbl_time.text = f"{m:02d}:{s:02d}"
        if gs.is_won():
            self._show_win()

    # ---- 按钮回调 ----
    def _on_undo(self, _btn):
        if self.game_state and self.game_state.undo():
            self._refresh_labels()
            self.board.redraw()

    def _on_new_game(self, _btn):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(
            text='开始新游戏？', font_name=CJK, size_hint_y=0.6))
        btns = BoxLayout(size_hint_y=0.4, spacing=10)

        popup = Popup(title='', content=content,
                      size_hint=(0.8, 0.35), auto_dismiss=False)

        cancel = Button(text='取消', font_name=CJK, size_hint_x=0.5)
        cancel.bind(on_press=lambda *a: popup.dismiss())
        btns.add_widget(cancel)

        def confirm(*a):
            if self.game_state:
                self.game_state.new_game()
                self._refresh_labels()
                self.board.redraw()
            popup.dismiss()

        ok = Button(text='确认', font_name=CJK, size_hint_x=0.5)
        ok.bind(on_press=confirm)
        btns.add_widget(ok)
        content.add_widget(btns)
        popup.open()

    def _on_menu(self, btn):
        if self._on_menu_cb:
            self._on_menu_cb(btn)

    # ---- 胜利 ----
    def _show_win(self):
        if self._win_shown:
            return
        self._win_shown = True

        if self._timer_event:
            self._timer_event.cancel()
            self._timer_event = None

        # 通知 App 记录统计
        if self._on_game_won:
            self._on_game_won()

        gs = self.game_state
        m, s = divmod(gs.elapsed_time, 60)

        content = BoxLayout(orientation='vertical', padding=20, spacing=10)
        content.add_widget(Label(
            text='恭喜！你赢了！', font_name=CJK,
            font_size=FONT_SIZE_LARGE, size_hint_y=0.2))

        # 带标签的统计信息（标签用 CJK，数值用默认）
        stats_box = BoxLayout(orientation='vertical', size_hint_y=0.45, spacing=5)
        for label_txt, value_txt in [
            ('得分', str(gs.score)),
            ('步数', str(gs.moves)),
            ('用时', f'{m}:{s:02d}'),
        ]:
            row = BoxLayout(orientation='horizontal', spacing=10)
            row.add_widget(Label(
                text=label_txt, font_name=CJK,
                font_size=FONT_SIZE_NORMAL, color=(0.8, 0.8, 0.8, 1),
                size_hint_x=0.4, halign='right', valign='middle'))
            row.children[0].text_size = (None, None)
            row.add_widget(Label(
                text=value_txt,
                font_size=FONT_SIZE_NORMAL * 1.3, color=(1, 1, 0.7, 1),
                size_hint_x=0.6, halign='left', valign='middle', bold=True))
            stats_box.add_widget(row)
        content.add_widget(stats_box)

        btns = BoxLayout(size_hint_y=0.35, spacing=10)
        popup = Popup(title='', content=content,
                      size_hint=(0.85, 0.55), auto_dismiss=False)

        btn_menu = Button(text='菜单', font_name=CJK, size_hint_x=0.5)
        btn_menu.bind(on_press=lambda *a: (popup.dismiss(), self._on_menu(None)))
        btns.add_widget(btn_menu)

        def again(*a):
            if gs:
                gs.new_game()
                self._refresh_labels()
                self.board.redraw()
                self._start_timer()
            popup.dismiss()

        btn_again = Button(text='再来一局', font_name=CJK, size_hint_x=0.5)
        btn_again.bind(on_press=again)
        btns.add_widget(btn_again)
        content.add_widget(btns)
        popup.open()

    # ---- 生命周期 ----
    def _start_timer(self):
        if self._timer_event:
            self._timer_event.cancel()
        self._timer_event = Clock.schedule_interval(self._tick, 1.0)

    def on_enter(self):
        self._start_timer()

    def on_leave(self):
        if self._timer_event:
            self._timer_event.cancel()
            self._timer_event = None
