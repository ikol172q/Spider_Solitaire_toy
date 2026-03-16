"""游戏历史统计模块

数据双重持久化 + 时间戳合并策略：
1. 主存储：应用私有目录 (~/.spider_solitaire/stats.json)
2. 备份存储：Android app-specific 外部目录（通过 Context 获取），
   桌面平台回退到 ~/.spider_solitaire_backup/

每条记录都有唯一时间戳 (ts)。启动时读取两边数据，按 ts 去重合并，
确保版本更新或重装后不丢失也不重复。
"""

import os
import sys
import json
import time
try:
    from kivy.utils import platform as _kivy_platform
except ImportError:
    _kivy_platform = sys.platform  # 测试环境回退


_EXTERNAL_BACKUP_FILE = 'stats.json'


def _get_android_external_dir():
    """获取 Android app-specific 外部存储目录

    使用 pyjnius 调用 Context.getExternalFilesDir()，
    这个路径在 Android 10+ 也无需额外权限即可读写。
    失败时返回 None。
    """
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        context = PythonActivity.mActivity
        # getExternalFilesDir(null) → /storage/emulated/0/Android/data/<pkg>/files/
        ext_dir = context.getExternalFilesDir(None)
        if ext_dir:
            return ext_dir.getAbsolutePath()
    except Exception:
        pass
    return None


def _get_default_backup_dir():
    """根据平台返回默认备份目录"""
    if _kivy_platform == 'android':
        d = _get_android_external_dir()
        if d:
            return os.path.join(d, 'SpiderSolitaire')
        # 回退：不再使用 /sdcard（Android 10+ scoped storage 不允许）
        # 返回 None，跳过备份
        return None
    else:
        # 桌面平台：使用 home 下的备份目录
        return os.path.expanduser('~/.spider_solitaire_backup')


class GameStats:
    """记录和查询游戏历史统计

    数据存储在 ~/.spider_solitaire/stats.json，
    同时备份到 /sdcard/SpiderSolitaire/stats.json（Android 外部存储）。
    启动时自动合并两边数据（按时间戳去重），保证不丢不重。
    """

    def __init__(self, path=None, backup_dir=None):
        if path is None:
            if _kivy_platform == 'android':
                # Android 上用 Kivy App 的 user_data_dir
                try:
                    from kivy.app import App
                    app = App.get_running_app()
                    d = app.user_data_dir if app else os.path.expanduser('~/.spider_solitaire')
                except Exception:
                    d = os.path.expanduser('~/.spider_solitaire')
            else:
                d = os.path.expanduser('~/.spider_solitaire')
            try:
                os.makedirs(d, exist_ok=True)
            except Exception:
                pass
            path = os.path.join(d, 'stats.json')
        self.path = path
        self._backup_dir = backup_dir if backup_dir is not None else _get_default_backup_dir()
        self.records = []
        self._load()

    # ---- 持久化 ----

    @property
    def _backup_path(self):
        if self._backup_dir:
            return os.path.join(self._backup_dir, _EXTERNAL_BACKUP_FILE)
        return None

    @staticmethod
    def _record_key(rec):
        """记录的唯一标识：(ts, difficulty, score, moves)
        ts 精确到毫秒级，加上其它字段基本不会冲突。"""
        return (rec.get('ts', 0), rec.get('difficulty', ''),
                rec.get('score', 0), rec.get('moves', 0))

    @staticmethod
    def _merge(list_a, list_b):
        """按时间戳去重合并两个记录列表，按 ts 排序返回"""
        seen = {}
        for rec in (list_a or []) + (list_b or []):
            key = GameStats._record_key(rec)
            if key not in seen:
                seen[key] = rec
        return sorted(seen.values(), key=lambda r: r.get('ts', 0))

    def _load(self):
        """加载数据：读取主存储和备份，合并去重"""
        primary = self._read_json(self.path)
        bp = self._backup_path
        backup = self._read_json(bp) if bp else None

        if primary is not None and backup is not None:
            # 两边都有数据 → 合并
            merged = self._merge(primary, backup)
            if len(merged) > len(primary) or len(merged) > len(backup):
                print(f'合并主存储({len(primary)}条)和备份({len(backup)}条) → {len(merged)}条')
            self.records = merged
            # 合并后回写两边
            self._save_to(self.path)
            if bp:
                self._save_to(bp)
        elif primary is not None:
            self.records = primary
        elif backup is not None:
            self.records = backup
            print(f'从备份恢复了 {len(self.records)} 条记录')
            self._save_to(self.path)
        else:
            self.records = []

    def _read_json(self, filepath):
        """读取 JSON 文件，失败返回 None"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return None

    def _save(self):
        """保存到主存储 + 备份"""
        self._save_to(self.path)
        bp = self._backup_path
        if bp:
            self._save_to(bp)

    def _save_to(self, filepath):
        """保存到指定路径"""
        try:
            d = os.path.dirname(filepath)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.records, f, ensure_ascii=False)
        except Exception as e:
            print(f'统计保存失败 ({filepath}): {e}')

    # ---- 记录 ----

    def record_game(self, difficulty, won, score, moves, elapsed_time, completed_sets):
        """记录一局游戏结果

        参数:
            difficulty: 'easy'/'medium'/'hard'
            won: 是否胜利
            score: 最终分数
            moves: 总步数
            elapsed_time: 用时（秒）
            completed_sets: 完成的套数 (0-8)
        """
        self.records.append({
            'ts': time.time(),
            'difficulty': difficulty,
            'won': won,
            'score': score,
            'moves': moves,
            'time': elapsed_time,
            'sets': completed_sets,
        })
        self._save()

    # ---- 查询 ----

    def get_summary(self, difficulty=None):
        """获取统计摘要

        参数:
            difficulty: 筛选难度，None 表示全部

        返回:
            dict，包含各项统计
        """
        recs = self.records
        if difficulty:
            recs = [r for r in recs if r.get('difficulty') == difficulty]

        if not recs:
            return {
                'total': 0, 'wins': 0, 'win_rate': 0,
                'best_score': 0, 'worst_score': 0, 'avg_score': 0,
                'best_time': 0, 'worst_time': 0, 'avg_time': 0,
                'avg_moves': 0,
                'time_p25': 0, 'time_p50': 0, 'time_p75': 0,
            }

        total = len(recs)
        wins = sum(1 for r in recs if r.get('won'))
        scores = [r['score'] for r in recs]
        times = [r['time'] for r in recs]
        moves_list = [r['moves'] for r in recs]

        # 胜利局的时间分位数
        win_times = sorted(r['time'] for r in recs if r.get('won'))

        def percentile(arr, p):
            if not arr:
                return 0
            k = (len(arr) - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < len(arr) else f
            return arr[f] + (arr[c] - arr[f]) * (k - f)

        return {
            'total': total,
            'wins': wins,
            'win_rate': round(wins / total * 100, 1) if total > 0 else 0,
            'best_score': max(scores),
            'worst_score': min(scores),
            'avg_score': round(sum(scores) / total),
            'best_time': min(win_times) if win_times else 0,
            'worst_time': max(win_times) if win_times else 0,
            'avg_time': round(sum(times) / total),
            'avg_moves': round(sum(moves_list) / total),
            'time_p25': round(percentile(win_times, 25)),
            'time_p50': round(percentile(win_times, 50)),
            'time_p75': round(percentile(win_times, 75)),
        }
