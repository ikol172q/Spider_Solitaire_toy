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
    FONT_SIZE_LARGE, FONT_SIZE_TITLE, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, PADDING
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

        self._root = BoxLayout(orientation='vertical')
        self._status_bar = self._build_status_bar()
        self._root.add_widget(self._status_bar)

        self.board = BoardWidget()
        self.board.size_hint = (1, 1)
        self.board.on_state_updated = self._refresh_labels
        self._root.add_widget(self.board)

        self._button_bar = self._build_button_bar()
        self._root.add_widget(self._button_bar)

        with self.canvas.before:
            Color(*BACKGROUND_COLOR)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        self.add_widget(self._root)
        if self.game_state:
            self.board.set_game_state(self.game_state)

    def _upd_bg(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        is_landscape = self.width > self.height
        if hasattr(self, '_status_bar'):
            self._rebuild_status_bar_layout(is_landscape)
        if hasattr(self, '_button_bar'):
            btn_h = STATUS_BAR_HEIGHT * 0.78 if is_landscape else STATUS_BAR_HEIGHT
            self._button_bar.height = btn_h
            # 横屏时稍微增大按钮字体
            _btn_fs = FONT_SIZE_NORMAL * 1.1 if is_landscape else FONT_SIZE_NORMAL
            for child in self._button_bar.children:
                if isinstance(child, Button):
                    child.font_size = _btn_fs

    # ---- 状态栏 ----
    def _build_status_bar(self):
        bar = BoxLayout(
            orientation='horizontal',
            size_hint_y=None, height=STATUS_BAR_HEIGHT,
            padding=PADDING, spacing=PADDING
        )
        gs = self.game_state
        score = gs.score if gs else 0
        moves = gs.moves if gs else 0

        diff_map = {'easy': '初级', 'medium': '中级', 'hard': '高级'}
        diff_txt = diff_map.get(gs.difficulty, '') if gs else ''

        self.lbl_score = Label(
            text=str(score), font_size=FONT_SIZE_NORMAL * 1.1,
            color=(1, 1, 0.7, 1), bold=True)
        self.lbl_moves = Label(
            text=str(moves), font_size=FONT_SIZE_NORMAL * 1.1,
            color=(1, 1, 0.7, 1), bold=True)
        self.lbl_time = Label(
            text='00:00', font_size=FONT_SIZE_NORMAL * 1.1,
            color=(1, 1, 0.7, 1), bold=True)
        self.lbl_diff = Label(
            text=diff_txt, font_name=CJK, font_size=FONT_SIZE_NORMAL * 1.1,
            color=(1, 1, 0.7, 1), bold=True)

        self._status_labels = [
            ('得分', self.lbl_score),
            ('步数', self.lbl_moves),
            ('用时', self.lbl_time),
            ('难度', self.lbl_diff),
        ]
        self._status_header_widgets = []
        self._status_layout_mode = None  # 'portrait' or 'landscape'

        # 初始布局（竖屏双行模式）
        self._apply_status_portrait(bar)
        return bar

    def _apply_status_portrait(self, bar):
        """竖屏：双行布局（上面标签，下面数值）"""
        bar.clear_widgets()
        bar.height = STATUS_BAR_HEIGHT
        self._status_header_widgets = []
        for label_txt, value_lbl in self._status_labels:
            col = BoxLayout(orientation='vertical', size_hint_x=0.25)
            header = Label(
                text=label_txt, font_name=CJK,
                font_size=FONT_SIZE_SMALL,
                color=(0.75, 0.85, 0.75, 1),
                size_hint_y=0.4,
                halign='center', valign='bottom')
            header.bind(size=header.setter('text_size'))
            value_lbl.size_hint_y = 0.6
            value_lbl.size_hint_x = 1
            value_lbl.halign = 'center'
            value_lbl.valign = 'top'
            value_lbl.bind(size=value_lbl.setter('text_size'))
            col.add_widget(header)
            col.add_widget(value_lbl)
            bar.add_widget(col)
            self._status_header_widgets.append(header)
        self._status_layout_mode = 'portrait'

    def _apply_status_landscape(self, bar):
        """横屏：单行布局（'得分：500  步数：0  用时：00:19  难度：初级'）"""
        bar.clear_widgets()
        bar.height = STATUS_BAR_HEIGHT * 0.62
        bar.padding = [PADDING, 0, PADDING, 0]
        self._status_header_widgets = []
        _fs = FONT_SIZE_SMALL * 1.15
        for label_txt, value_lbl in self._status_labels:
            cell = BoxLayout(orientation='horizontal', size_hint_x=0.25)
            header = Label(
                text=label_txt + '：', font_name=CJK,
                font_size=_fs,
                color=(0.75, 0.85, 0.75, 1),
                size_hint_x=0.5,
                halign='right', valign='middle')
            header.bind(size=header.setter('text_size'))
            value_lbl.font_size = FONT_SIZE_NORMAL * 1.15
            value_lbl.size_hint_y = 1
            value_lbl.size_hint_x = 0.5
            value_lbl.halign = 'left'
            value_lbl.valign = 'middle'
            value_lbl.bind(size=value_lbl.setter('text_size'))
            cell.add_widget(header)
            cell.add_widget(value_lbl)
            bar.add_widget(cell)
            self._status_header_widgets.append(header)
        self._status_layout_mode = 'landscape'

    def _detach_status_value_labels(self):
        """将 value_lbl 从旧 parent 中安全移除（防止 re-parent 报错）"""
        for _, value_lbl in self._status_labels:
            if value_lbl.parent:
                value_lbl.parent.remove_widget(value_lbl)

    def _rebuild_status_bar_layout(self, is_landscape):
        """根据方向切换状态栏布局（仅在方向真正变化时重建）"""
        target = 'landscape' if is_landscape else 'portrait'
        if self._status_layout_mode == target:
            return
        self._detach_status_value_labels()
        bar = self._status_bar
        if is_landscape:
            self._apply_status_landscape(bar)
        else:
            self._apply_status_portrait(bar)

    # ---- 按钮栏 ----
    def _build_button_bar(self):
        bar = BoxLayout(
            orientation='horizontal',
            size_hint_y=None, height=STATUS_BAR_HEIGHT,
            padding=PADDING, spacing=PADDING
        )
        for text, cb, w in [
            ('撤销', self._on_undo, 0.2),
            ('新游戏', self._on_new_game, 0.2),
            ('菜单', self._on_menu, 0.2),
        ]:
            btn = Button(text=text, font_name=CJK,
                         font_size=FONT_SIZE_NORMAL,
                         background_color=BUTTON_COLOR, size_hint_x=w)
            btn.bind(on_press=cb)
            bar.add_widget(btn)

        # 点击自动移动 开关按钮
        self._auto_move_on = False
        self._auto_btn = Button(
            text='自动：关', font_name=CJK,
            font_size=FONT_SIZE_NORMAL,
            background_color=(0.4, 0.4, 0.4, 1),
            size_hint_x=0.2)
        self._auto_btn.bind(on_press=self._toggle_auto_move)
        bar.add_widget(self._auto_btn)

        # 辅助牌信息 开关按钮（横屏时显示每列翻开牌的浮框）
        self._hint_on = False
        self._hint_btn = Button(
            text='辅助：关', font_name=CJK,
            font_size=FONT_SIZE_NORMAL,
            background_color=(0.4, 0.4, 0.4, 1),
            size_hint_x=0.2)
        self._hint_btn.bind(on_press=self._toggle_card_hints)
        bar.add_widget(self._hint_btn)

        return bar

    def _toggle_auto_move(self, _btn):
        """切换点击自动移动开关"""
        self._auto_move_on = not self._auto_move_on
        if self._auto_move_on:
            self._auto_btn.background_color = (0.2, 0.6, 0.2, 1)
            self._auto_btn.text = '自动：开'
        else:
            self._auto_btn.background_color = (0.4, 0.4, 0.4, 1)
            self._auto_btn.text = '自动：关'
        self._auto_btn.font_name = CJK  # 确保中文字体不丢失
        self.board.auto_move_enabled = self._auto_move_on

    def _toggle_card_hints(self, _btn):
        """切换辅助牌信息浮框开关"""
        self._hint_on = not self._hint_on
        if self._hint_on:
            self._hint_btn.background_color = (0.2, 0.5, 0.7, 1)
            self._hint_btn.text = '辅助：开'
        else:
            self._hint_btn.background_color = (0.4, 0.4, 0.4, 1)
            self._hint_btn.text = '辅助：关'
        self._hint_btn.font_name = CJK  # 确保中文字体不丢失
        self.board.show_card_hints = self._hint_on
        self.board.redraw()

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
