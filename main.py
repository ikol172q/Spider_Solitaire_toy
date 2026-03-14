"""蜘蛛纸牌 - 应用入口

Kivy + Buildozer 构建的蜘蛛纸牌游戏，目标设备：华为 Mate 40。
"""

import os
import sys
import json
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.core.window import Window
from kivy.core.text import LabelBase

from spider_solitaire.game.game_state import GameState
from spider_solitaire.game.stats import GameStats
from spider_solitaire.ui.menu_screen import MenuScreen
from spider_solitaire.ui.game_screen import GameScreen
from spider_solitaire.ui.stats_screen import StatsScreen

# ---- 平台检测 ----
IS_ANDROID = sys.platform == 'android'

# ---- 注册字体 ----
# 1) DejaVuSans 替换默认 Roboto → Latin + 数字 + 符号（♠♥♦♣）
# 2) DroidSansFallback 注册为 "CJK" → 中文字符
import kivy as _kivy
_KIVY_FONTS = os.path.join(os.path.dirname(_kivy.__file__), 'data', 'fonts')
_DEJAVU = os.path.join(_KIVY_FONTS, 'DejaVuSans.ttf')
if os.path.isfile(_DEJAVU):
    LabelBase.register(name='Roboto', fn_regular=_DEJAVU)

# 字体搜索路径：APK 打包后的路径可能不同，尝试多个位置
_FONT_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'fonts', 'chinese.ttf'),
]
if IS_ANDROID:
    # Android APK 中 assets 可能在应用私有目录下
    try:
        from android.storage import app_storage_path  # noqa: F401
        _FONT_CANDIDATES.append(
            os.path.join(app_storage_path(), 'app', 'assets', 'fonts', 'chinese.ttf'))
    except Exception:
        pass

_CJK_FONT = None
for _candidate in _FONT_CANDIDATES:
    if os.path.isfile(_candidate):
        _CJK_FONT = _candidate
        break

if _CJK_FONT:
    LabelBase.register(name='CJK', fn_regular=_CJK_FONT)
else:
    print('警告: 未找到中文字体 chinese.ttf，中文可能显示为方块')

# ---- 桌面调试时的窗口设置 ----
# 华为 Mate 40 横屏比例：2376×1080 ≈ 19.8:9
# 桌面预览使用缩小版本（横屏优先）
PREVIEW_WIDTH = 920
PREVIEW_HEIGHT = 420


class SpiderSolitaireApp(App):
    """蜘蛛纸牌应用"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_state = None
        self.save_path = None
        self.sm = None  # ScreenManager
        self.stats = None  # 统计

    def build(self):
        self.title = '蜘蛛纸牌'

        # 桌面调试窗口大小（仅桌面平台，Android 使用设备实际尺寸）
        if not IS_ANDROID:
            Window.size = (PREVIEW_WIDTH, PREVIEW_HEIGHT)

        # 存档路径
        save_dir = os.path.expanduser('~/.spider_solitaire')
        os.makedirs(save_dir, exist_ok=True)
        self.save_path = os.path.join(save_dir, 'save.json')

        # 统计
        self.stats = GameStats()

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
            on_stats_pressed=self._show_stats,
            has_saved_game=self._has_save()
        )
        self.sm.add_widget(menu)

    def _add_game(self):
        """添加游戏屏幕"""
        scr = GameScreen(
            name='game',
            game_state=self.game_state,
            on_menu_pressed=self._back_to_menu,
            on_game_won=self._on_game_won
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

    def _show_stats(self):
        self._remove_screen('stats')
        scr = StatsScreen(
            name='stats',
            game_stats=self.stats,
            on_back=self._back_from_stats
        )
        self.sm.add_widget(scr)
        self.sm.current = 'stats'

    def _back_from_stats(self):
        self._remove_screen('stats')
        self.sm.current = 'menu'

    def _on_game_won(self):
        """游戏胜利回调 — 记录统计"""
        gs = self.game_state
        if gs:
            self.stats.record_game(
                difficulty=gs.difficulty,
                won=True,
                score=gs.score,
                moves=gs.moves,
                elapsed_time=gs.elapsed_time,
                completed_sets=len(gs.completed)
            )

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
