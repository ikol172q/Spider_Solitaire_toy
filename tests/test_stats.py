"""GameStats 单元测试"""

import unittest
import os
import tempfile
import shutil
import json

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spider_solitaire.game.stats import GameStats


class TestGameStats(unittest.TestCase):
    """测试 GameStats 类"""

    def setUp(self):
        """每个测试前创建临时文件"""
        self._tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self._tmp.close()
        self.path = self._tmp.name
        os.unlink(self.path)

    def tearDown(self):
        if os.path.isfile(self.path):
            os.unlink(self.path)

    def _stats(self, path=None):
        """创建不写备份的 GameStats"""
        return GameStats(path=path or self.path, backup_dir='')

    # ---- 初始化 / 持久化 ----

    def test_init_no_file(self):
        stats = self._stats()
        self.assertEqual(stats.records, [])

    def test_init_corrupt_file(self):
        with open(self.path, 'w') as f:
            f.write('NOT VALID JSON {{{')
        stats = self._stats()
        self.assertEqual(stats.records, [])

    def test_init_empty_file(self):
        with open(self.path, 'w') as f:
            f.write('')
        stats = self._stats()
        self.assertEqual(stats.records, [])

    def test_persistence_roundtrip(self):
        stats = self._stats()
        stats.record_game('easy', True, 1000, 100, 300.0, 8)
        stats.record_game('hard', False, 200, 50, 600.0, 3)

        stats2 = self._stats()
        self.assertEqual(len(stats2.records), 2)
        self.assertEqual(stats2.records[0]['difficulty'], 'easy')
        self.assertEqual(stats2.records[1]['won'], False)

    # ---- record_game ----

    def test_record_game_appends(self):
        stats = self._stats()
        self.assertEqual(len(stats.records), 0)
        stats.record_game('easy', True, 900, 80, 200.0, 8)
        self.assertEqual(len(stats.records), 1)
        stats.record_game('easy', False, 100, 20, 50.0, 1)
        self.assertEqual(len(stats.records), 2)

    def test_record_game_fields(self):
        stats = self._stats()
        stats.record_game('medium', True, 750, 120, 450.5, 8)
        r = stats.records[0]
        self.assertEqual(r['difficulty'], 'medium')
        self.assertTrue(r['won'])
        self.assertEqual(r['score'], 750)
        self.assertEqual(r['moves'], 120)
        self.assertAlmostEqual(r['time'], 450.5)
        self.assertEqual(r['sets'], 8)
        self.assertIn('ts', r)

    # ---- get_summary 空数据 ----

    def test_summary_empty(self):
        stats = self._stats()
        s = stats.get_summary()
        self.assertEqual(s['total'], 0)
        self.assertEqual(s['wins'], 0)
        self.assertEqual(s['win_rate'], 0)
        self.assertEqual(s['best_score'], 0)
        self.assertEqual(s['avg_moves'], 0)

    # ---- get_summary 有数据 ----

    def _make_stats_with_data(self):
        stats = self._stats()
        stats.record_game('easy', True, 1000, 100, 300.0, 8)
        stats.record_game('easy', True, 800, 150, 500.0, 8)
        stats.record_game('easy', False, 200, 50, 100.0, 2)
        stats.record_game('hard', False, 100, 30, 60.0, 1)
        return stats

    def test_summary_all(self):
        stats = self._make_stats_with_data()
        s = stats.get_summary()
        self.assertEqual(s['total'], 4)
        self.assertEqual(s['wins'], 2)
        self.assertEqual(s['win_rate'], 50.0)
        self.assertEqual(s['best_score'], 1000)
        self.assertEqual(s['worst_score'], 100)

    def test_summary_filter_difficulty(self):
        stats = self._make_stats_with_data()
        s_easy = stats.get_summary(difficulty='easy')
        self.assertEqual(s_easy['total'], 3)
        self.assertEqual(s_easy['wins'], 2)
        self.assertAlmostEqual(s_easy['win_rate'], 66.7)

        s_hard = stats.get_summary(difficulty='hard')
        self.assertEqual(s_hard['total'], 1)
        self.assertEqual(s_hard['wins'], 0)

    def test_summary_nonexistent_difficulty(self):
        stats = self._make_stats_with_data()
        s = stats.get_summary(difficulty='medium')
        self.assertEqual(s['total'], 0)

    def test_summary_avg_score(self):
        stats = self._make_stats_with_data()
        s = stats.get_summary(difficulty='easy')
        self.assertEqual(s['avg_score'], 667)

    def test_summary_avg_moves(self):
        stats = self._make_stats_with_data()
        s = stats.get_summary(difficulty='easy')
        self.assertEqual(s['avg_moves'], 100)

    def test_summary_win_times(self):
        stats = self._make_stats_with_data()
        s = stats.get_summary(difficulty='easy')
        self.assertEqual(s['best_time'], 300.0)
        self.assertEqual(s['worst_time'], 500.0)

    def test_summary_no_wins_times(self):
        stats = self._make_stats_with_data()
        s = stats.get_summary(difficulty='hard')
        self.assertEqual(s['best_time'], 0)
        self.assertEqual(s['worst_time'], 0)
        self.assertEqual(s['time_p50'], 0)

    def test_summary_percentiles_single_win(self):
        stats = self._stats()
        stats.record_game('easy', True, 500, 80, 240.0, 8)
        s = stats.get_summary()
        self.assertEqual(s['time_p25'], 240)
        self.assertEqual(s['time_p50'], 240)
        self.assertEqual(s['time_p75'], 240)

    def test_summary_percentiles_multiple_wins(self):
        stats = self._stats()
        for t in [100, 200, 300, 400]:
            stats.record_game('easy', True, 500, 80, float(t), 8)
        s = stats.get_summary()
        self.assertEqual(s['time_p25'], 175)
        self.assertEqual(s['time_p50'], 250)
        self.assertEqual(s['time_p75'], 325)


class TestGameStatsEdgeCases(unittest.TestCase):
    """边界条件"""

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self._tmp.close()
        self.path = self._tmp.name
        os.unlink(self.path)

    def tearDown(self):
        if os.path.isfile(self.path):
            os.unlink(self.path)

    def _stats(self):
        return GameStats(path=self.path, backup_dir='')

    def test_zero_score(self):
        stats = self._stats()
        stats.record_game('easy', False, 0, 0, 0.0, 0)
        s = stats.get_summary()
        self.assertEqual(s['total'], 1)
        self.assertEqual(s['best_score'], 0)

    def test_large_number_of_records(self):
        stats = self._stats()
        for i in range(500):
            stats.record_game('easy', i % 3 == 0, i * 10, i, float(i * 5), i % 9)
        s = stats.get_summary()
        self.assertEqual(s['total'], 500)

    def test_concurrent_instances_read(self):
        stats1 = self._stats()
        stats1.record_game('easy', True, 500, 50, 100.0, 8)
        stats2 = GameStats(path=self.path, backup_dir='')
        self.assertEqual(len(stats2.records), 1)


class TestGameStatsBackup(unittest.TestCase):
    """备份/恢复测试"""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.primary_path = os.path.join(self._tmpdir, 'primary', 'stats.json')
        self.backup_dir = os.path.join(self._tmpdir, 'backup')

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_backup_created_on_save(self):
        """record_game 同时写主存储和备份"""
        stats = GameStats(path=self.primary_path, backup_dir=self.backup_dir)
        stats.record_game('easy', True, 500, 50, 100.0, 8)

        # 主存储存在
        self.assertTrue(os.path.isfile(self.primary_path))
        # 备份存在
        backup_path = os.path.join(self.backup_dir, 'stats.json')
        self.assertTrue(os.path.isfile(backup_path))

        # 内容一致
        with open(self.primary_path) as f:
            primary_data = json.load(f)
        with open(backup_path) as f:
            backup_data = json.load(f)
        self.assertEqual(primary_data, backup_data)

    def test_restore_from_backup_when_primary_missing(self):
        """主存储丢失（模拟重装）→ 从备份恢复"""
        # 先正常写入
        stats = GameStats(path=self.primary_path, backup_dir=self.backup_dir)
        stats.record_game('easy', True, 999, 88, 200.0, 8)
        stats.record_game('hard', False, 100, 20, 50.0, 2)

        # 删除主存储（模拟 app 卸载）
        os.unlink(self.primary_path)
        self.assertFalse(os.path.isfile(self.primary_path))

        # 重新打开 → 应从备份恢复
        stats2 = GameStats(path=self.primary_path, backup_dir=self.backup_dir)
        self.assertEqual(len(stats2.records), 2)
        self.assertEqual(stats2.records[0]['score'], 999)

        # 恢复后主存储也被重建
        self.assertTrue(os.path.isfile(self.primary_path))

    def test_restore_from_backup_when_primary_corrupt(self):
        """主存储损坏 → 从备份恢复"""
        stats = GameStats(path=self.primary_path, backup_dir=self.backup_dir)
        stats.record_game('medium', True, 700, 60, 150.0, 8)

        # 破坏主存储
        with open(self.primary_path, 'w') as f:
            f.write('CORRUPTED!!!')

        stats2 = GameStats(path=self.primary_path, backup_dir=self.backup_dir)
        self.assertEqual(len(stats2.records), 1)
        self.assertEqual(stats2.records[0]['difficulty'], 'medium')

    def test_no_backup_dir_no_crash(self):
        """backup_dir 为空字符串 → 不备份，不崩溃"""
        stats = GameStats(path=self.primary_path, backup_dir='')
        stats.record_game('easy', True, 500, 50, 100.0, 8)
        self.assertEqual(len(stats.records), 1)
        # 备份目录下不应有文件
        self.assertFalse(os.path.isdir(self.backup_dir))

    def test_both_missing_yields_empty(self):
        """主存储和备份都不存在 → 空记录"""
        stats = GameStats(path=self.primary_path, backup_dir=self.backup_dir)
        self.assertEqual(stats.records, [])


class TestGameStatsMerge(unittest.TestCase):
    """时间戳合并逻辑测试"""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.primary_path = os.path.join(self._tmpdir, 'primary', 'stats.json')
        self.backup_dir = os.path.join(self._tmpdir, 'backup')
        self.backup_path = os.path.join(self.backup_dir, 'stats.json')

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _write_json(self, path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f)

    def test_merge_deduplicates_identical_records(self):
        """主存储和备份有完全相同的记录 → 去重"""
        rec = {'ts': 1000.0, 'difficulty': 'easy', 'won': True,
               'score': 500, 'moves': 80, 'time': 200.0, 'sets': 8}
        self._write_json(self.primary_path, [rec])
        self._write_json(self.backup_path, [rec])

        stats = GameStats(path=self.primary_path, backup_dir=self.backup_dir)
        self.assertEqual(len(stats.records), 1)

    def test_merge_combines_disjoint_records(self):
        """主存储和备份各有不同记录 → 全部保留"""
        rec_a = {'ts': 1000.0, 'difficulty': 'easy', 'won': True,
                 'score': 500, 'moves': 80, 'time': 200.0, 'sets': 8}
        rec_b = {'ts': 2000.0, 'difficulty': 'hard', 'won': False,
                 'score': 100, 'moves': 30, 'time': 60.0, 'sets': 1}
        self._write_json(self.primary_path, [rec_a])
        self._write_json(self.backup_path, [rec_b])

        stats = GameStats(path=self.primary_path, backup_dir=self.backup_dir)
        self.assertEqual(len(stats.records), 2)

    def test_merge_sorted_by_ts(self):
        """合并后按时间戳排序"""
        rec_old = {'ts': 500.0, 'difficulty': 'easy', 'won': True,
                   'score': 300, 'moves': 40, 'time': 100.0, 'sets': 8}
        rec_new = {'ts': 9000.0, 'difficulty': 'hard', 'won': False,
                   'score': 100, 'moves': 20, 'time': 50.0, 'sets': 1}
        # 备份有旧的，主存储有新的
        self._write_json(self.backup_path, [rec_old])
        self._write_json(self.primary_path, [rec_new])

        stats = GameStats(path=self.primary_path, backup_dir=self.backup_dir)
        self.assertEqual(stats.records[0]['ts'], 500.0)
        self.assertEqual(stats.records[1]['ts'], 9000.0)

    def test_merge_overlapping_with_unique(self):
        """部分重叠、部分独有 → 去重 + 保留独有"""
        shared = {'ts': 1000.0, 'difficulty': 'easy', 'won': True,
                  'score': 500, 'moves': 80, 'time': 200.0, 'sets': 8}
        only_primary = {'ts': 2000.0, 'difficulty': 'medium', 'won': True,
                        'score': 600, 'moves': 90, 'time': 300.0, 'sets': 8}
        only_backup = {'ts': 3000.0, 'difficulty': 'hard', 'won': False,
                       'score': 100, 'moves': 30, 'time': 60.0, 'sets': 1}

        self._write_json(self.primary_path, [shared, only_primary])
        self._write_json(self.backup_path, [shared, only_backup])

        stats = GameStats(path=self.primary_path, backup_dir=self.backup_dir)
        self.assertEqual(len(stats.records), 3)
        ts_list = [r['ts'] for r in stats.records]
        self.assertEqual(ts_list, [1000.0, 2000.0, 3000.0])

    def test_merge_updates_both_files(self):
        """合并后两边文件内容一致"""
        rec_a = {'ts': 1000.0, 'difficulty': 'easy', 'won': True,
                 'score': 500, 'moves': 80, 'time': 200.0, 'sets': 8}
        rec_b = {'ts': 2000.0, 'difficulty': 'hard', 'won': False,
                 'score': 100, 'moves': 30, 'time': 60.0, 'sets': 1}
        self._write_json(self.primary_path, [rec_a])
        self._write_json(self.backup_path, [rec_b])

        GameStats(path=self.primary_path, backup_dir=self.backup_dir)

        with open(self.primary_path) as f:
            primary_data = json.load(f)
        with open(self.backup_path) as f:
            backup_data = json.load(f)
        self.assertEqual(len(primary_data), 2)
        self.assertEqual(primary_data, backup_data)

    def test_merge_reinstall_scenario(self):
        """模拟完整的重装场景"""
        # 第一阶段：正常使用，写了3条
        stats = GameStats(path=self.primary_path, backup_dir=self.backup_dir)
        stats.record_game('easy', True, 500, 80, 200.0, 8)
        stats.record_game('easy', False, 100, 20, 50.0, 1)
        stats.record_game('hard', True, 800, 120, 400.0, 8)
        self.assertEqual(len(stats.records), 3)

        # 第二阶段：卸载（删除主存储目录）
        os.unlink(self.primary_path)
        os.rmdir(os.path.dirname(self.primary_path))

        # 第三阶段：重装，玩了1局新的
        stats2 = GameStats(path=self.primary_path, backup_dir=self.backup_dir)
        # 应该从备份恢复了3条
        self.assertEqual(len(stats2.records), 3)
        # 再玩一局
        stats2.record_game('medium', True, 600, 90, 300.0, 8)
        self.assertEqual(len(stats2.records), 4)

        # 第四阶段：再次打开，应该有4条，没有重复
        stats3 = GameStats(path=self.primary_path, backup_dir=self.backup_dir)
        self.assertEqual(len(stats3.records), 4)

    def test_static_merge_function(self):
        """直接测试 _merge 静态方法"""
        a = [{'ts': 1.0, 'difficulty': 'easy', 'score': 100, 'moves': 10},
             {'ts': 2.0, 'difficulty': 'easy', 'score': 200, 'moves': 20}]
        b = [{'ts': 2.0, 'difficulty': 'easy', 'score': 200, 'moves': 20},
             {'ts': 3.0, 'difficulty': 'hard', 'score': 300, 'moves': 30}]
        merged = GameStats._merge(a, b)
        self.assertEqual(len(merged), 3)
        self.assertEqual([r['ts'] for r in merged], [1.0, 2.0, 3.0])

    def test_merge_empty_lists(self):
        self.assertEqual(GameStats._merge([], []), [])
        self.assertEqual(len(GameStats._merge([{'ts': 1.0, 'difficulty': '', 'score': 0, 'moves': 0}], [])), 1)
        self.assertEqual(len(GameStats._merge([], [{'ts': 1.0, 'difficulty': '', 'score': 0, 'moves': 0}])), 1)


if __name__ == '__main__':
    unittest.main()
