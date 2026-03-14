"""蜘蛛纸牌 - 应用入口

Kivy + Buildozer 构建的蜘蛛纸牌游戏，目标设备：华为 Mate 40。
"""

import os
import json
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.core.window import Window
from kivy.core.text import LabelBase

from spider_solitaire.game.game_state import GameState
from spider_solitaire.ui.menu_screen import MenuScreen
from spider_solitaire.ui.game_screen import GameScreen

# ---- 注册字体 ----
# 1) DejaVuSans 替换默认 Roboto → Latin + 数字 + 符号（♠♥♦♣）
# 2) DroidSansFallback 注册为 "CJK" → 中文字符
import kivy as _kivy
_KIVY_FONTS = os.path.join(os.path.dirname(_kivy.__file__), 'data', 'fonts')
_DEJAVU = os.path.join(_KIVY_FONTS, 'DejaVuSans.ttf')
if os.path.isfile(_DEJAVU):
    LabelBase.register(name='Roboto', fn_regular=_DEJAVU)

_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'fonts')
_CJK_FONT = os.path.join(_FONT_DIR, 'chinese.ttf')
if os.path.isfile(_CJK_FONT):
    LabelBase.register(name='CJK', fn_regular=_CJK_FONT)

# ---- 桌面调试时的窗口设置 ----
# 华为 Mate 40 竖屏比例：1080×2376 ≈ 9:19.8
# 桌面预览使用缩小版本
PREVIEW_WIDTH = 420
PREVIEW_HEIGHT = 920


class SpiderSolitaireApp(App):
    """蜘蛛纸牌应用"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_state = None
        self.save_path = None
        self.sm = None  # ScreenManager

    def build(self):
        self.title = '蜘蛛纸牌'

        # 桌面调试窗口大小（Android 上会被忽略）
        Window.size = (PREVIEW_WIDTH, PREVIEW_HEIGHT)

        # 存档路径
        save_dir = os.path.expanduser('~/.spider_solitaire')
        os.makedirs(save_dir, exist_ok=True)
        self.save_path = os.path.join(save_dir, 'save.json')

        self.sm = ScreenManager()
        self._add_menu()
        return self.sm

    # ========== 屏幕管理 ==========

    def _add_menu(self):
        """添加菜单屏幕"""
        menu = MenuScreen(
            name='menu',
            on_difficulty_selected=self._start_new,
            on_continue_game=self._continue,
            has_saved_game=self._has_save()
        )
        self.sm.add_widget(menu)

    def _add_game(self):
        """添加游戏屏幕"""
        scr = GameScreen(
            name='game',
            game_state=self.game_state,
            on_menu_pressed=self._back_to_menu
        )
        self.sm.add_widget(scr)

    def _remove_screen(self, name):
        if name in [s.name for s in self.sm.screens]:
            self.sm.remove_widget(self.sm.get_screen(name))

    # ========== 回调 ==========

    def _start_new(self, difficulty):
        self.game_state = GameState()
        self.game_state.new_game(difficulty)
        self._remove_screen('game')
        self._add_game()
        self.sm.current = 'game'

    def _continue(self):
        if self._load():
            self._remove_screen('game')
            self._add_game()
            self.sm.current = 'game'

    def _back_to_menu(self, _btn):
        self._save()
        self._remove_screen('game')
        self._remove_screen('menu')
        self._add_menu()
        self.sm.current = 'menu'

    # ========== 存档 ==========

    def _has_save(self):
        return self.save_path and os.path.isfile(self.save_path)

    def _save(self):
        if self.game_state is None or self.save_path is None:
            return
        try:
            with open(self.save_path, 'w', encoding='utf-8') as f:
                json.dump(self.game_state.to_dict(), f)
        except Exception as e:
            print(f'保存失败: {e}')

    def _load(self):
        try:
            with open(self.save_path, 'r', encoding='utf-8') as f:
                self.game_state = GameState.from_dict(json.load(f))
            return True
        except Exception as e:
            print(f'加载失败: {e}')
            return False

    def on_stop(self):
        self._save()


if __name__ == '__main__':
    SpiderSolitaireApp().run()
