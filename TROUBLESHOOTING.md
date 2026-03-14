# 蜘蛛纸牌 — 开发排错手册

本文档记录了整个开发过程中遇到的所有问题及解决方案。
下次开发类似项目（Python + Kivy + Buildozer → Android APK）时，请先通读一遍。

---

## 1. 中文字体显示为方块 / 乱码

**现象**: 界面上所有中文字符显示为 □□□ 方块。

**根因**: Kivy 默认字体 Roboto 不包含中文字符。即使放了 chinese.ttf，如果文件内容实际是 DejaVuSans 的副本（741KB），也没有中文字形。

**解决方案**:
- 使用 DroidSansFallbackFull.ttf（约 4MB，49382 个字形）作为中文字体
- 注册为独立字体名 `CJK`，不要覆盖默认 Roboto
- 所有中文 Label 加 `font_name='CJK'`

**验证方法**: 检查字体文件大小，741KB 是假的，4MB 才是真的。
```python
# 用 fontTools 检查字形数量
from fontTools.ttLib import TTFont
font = TTFont('chinese.ttf')
print(len(font.getGlyphOrder()))  # 应该 > 40000
```

---

## 2. ASCII 字符在 CJK 字体中显示为方块

**现象**: 用了 CJK 字体后，中文正常了，但按钮里的 `-`、`(`、`)` 和数字显示为方块。

**根因**: DroidSansFallbackFull 只有 CJK 字符，**完全没有 ASCII/Latin 字符**（连 0-9、A-Z 都没有）。

**解决方案 — 双字体策略**:
1. DejaVuSans 注册为默认 `Roboto` → 覆盖 Latin、数字、符号（♠♥♦♣）
2. DroidSansFallbackFull 注册为 `CJK` → 仅用于纯中文文本
3. **关键规则**: `font_name='CJK'` 的 Label 中**不能出现任何 ASCII 字符**
   - ✗ `"初级 - 一种花色"` → `-` 会变方块
   - ✓ `"初级：一种花色"` → 用全角 `：` 代替半角 `-`
4. 需要混合中英文时，拆成两个 Label：一个用 CJK 写中文，一个用默认字体写数字/符号

---

## 3. 卡牌在屏幕上溢出（10列放不下）

**现象**: 10 列卡牌超出屏幕宽度，右边几列看不见。

**根因**: theme.py 里 `CARD_WIDTH = dp(60)`，10 列 = 600dp，但 Mate 40 预览窗口只有 420px。

**解决方案**: 动态计算卡牌大小。
```python
def _calc_card_size(self):
    w = self.width
    gap = dp(2)
    cw = (w - gap * 11) / 10  # 10列 + 11个间隙
    ch = cw * 1.45             # 保持牌的比例
    cr = cw * 0.12             # 圆角
    return cw, ch, cr
```

---

## 4. 卡牌上的文字被裁剪

**现象**: 牌面上的数字和花色符号显示不全，被卡牌边缘裁剪。

**根因**: 字体大小 `cw * 0.45` 对于小卡牌来说太大，Label 区域不够。

**解决方案**:
- 将 rank 和 suit 合并为一个两行 Label：`text=f'{rank}\n{suit}'`
- 字体缩小到 `cw * 0.35`（rank）和 `cw * 0.50`（suit）
- Label 区域扩大到卡牌的 70% 宽度 × 50% 高度

---

## 5. J 看起来像 I

**现象**: 小尺寸卡牌上 J 的底部弯钩太细，看起来像字母 I。

**根因**: DejaVuSans 在小字号下 J 的 descender（下伸部分）渲染太细。

**缓解方案**: 增大字体尺寸，把 rank+suit 合并排列让可用空间更大。这是字体渲染的固有限制，完美解决需要换字体或用自定义绘制。

---

## 6. 空列规则错误（只允许 K）

**现象**: 无法将非 K 的牌移动到空列。

**根因**: `rules.py` 里写的是普通接龙规则（只有 K 能放空列），但蜘蛛纸牌的规则是**任何牌都可以放到空列**。

**解决方案**:
```python
# 修改前（错误）
if not target_col:
    return moving_card.rank == 13

# 修改后（正确）
if not target_col:
    return True
```

**教训**: 蜘蛛纸牌和普通接龙的规则区别要提前确认。

---

## 7. 拖放容差太严格

**现象**: 必须精确拖到目标列正中才能放牌成功，稍有偏差就放不上。

**根因**: 原始容差 = 1× 卡牌宽度 ≈ 40px，手机触屏操作太难精确。

**解决方案**:
```python
tolerance = max(cw * 2.5, dp(80))  # 至少 80dp
```

---

## 8. git index.lock 错误

**现象**: `git add` 报错 `fatal: Unable to create '.git/index.lock': File exists.`

**根因**: 上次 git 操作异常中断，遗留了锁文件。

**解决方案**:
```bash
rm -f .git/index.lock
```

---

## 9. GitHub Actions 构建失败 — libffi autoreconf 错误

**现象**:
```
configure.ac:215: error: possibly undefined macro: LT_SYS_SYMBOL_USCORE
autoreconf: error: /usr/bin/autoconf failed with exit status: 1
```

**根因**: `ubuntu-latest`（2024年起 = Ubuntu 24.04）的 autoconf 2.72 与 python-for-android 自带的 libffi 旧版 configure.ac 不兼容。Ubuntu 24 的 autoconf 对废弃宏的处理更严格，导致 `LT_SYS_SYMBOL_USCORE` 未定义。

**解决方案**:
1. **锁定 `runs-on: ubuntu-22.04`**（最关键的一步）
2. 安装 `libtool-bin`（提供缺失的 libtool 宏）
3. 补全所有系统依赖：`cmake`, `lld`, `ccache`, `libncurses5-dev`, `liblzma-dev`, `libsqlite3-dev`, `libreadline-dev`
4. 固定 `buildozer==1.5.0` 和 `cython==0.29.36`，不用浮动版本
5. 超时从 30 分钟放宽到 60 分钟（首次构建下载 NDK/SDK 很慢）
6. 加 Buildozer 缓存（`~/.buildozer`），二次构建快很多

---

## 10. buildozer.spec 遗漏字体文件

**现象**: APK 安装后中文仍然乱码（字体文件没被打包进去）。

**根因**: `source.include_exts` 没有包含 `ttf` 后缀。

**解决方案**:
```ini
source.include_exts = py,png,jpg,kv,atlas,json,ttf
```

---

## 11. 历史记录重装后丢失

**现象**: 卸载重装 app 后，游戏统计数据全部消失。

**根因**: 数据存在应用私有目录 (`/data/data/.../`)，卸载时被系统清除。

**解决方案 — 双重存储 + 时间戳合并**:
1. 主存储：应用私有目录 `~/.spider_solitaire/stats.json`
2. 备份：Android 外部存储 `/sdcard/SpiderSolitaire/stats.json`（卸载不删除）
3. 每条记录带 `ts` 时间戳
4. 启动时读取两边，按 `(ts, difficulty, score, moves)` 去重合并
5. 合并后回写两边，保持一致
6. `buildozer.spec` 需要声明权限：`WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE`

---

## 12. Kivy Animation 注意事项

**发牌动画**: 多张牌依次飞出时，用 `Clock.schedule_once` 设置延迟（0.06s 间隔），每张牌用独立的 `Animation` 实例。动画期间设置 `_animating = True` 阻止触摸输入。

**完成动画**: 13 张牌依次飞向左下角时，需要在动画完成回调里才真正从列中移除牌，否则会出现视觉闪烁。

**Z 轴管理**: 拖拽时需要 `remove_widget` + `add_widget` 把卡牌提到最上层，否则会被其他卡牌遮挡。

---

## 13. dp 单位与物理像素

**规则**: Kivy 的 `dp()` 是密度无关像素。桌面预览 420×920 对应 Mate 40 的 1080×2376（比例 9:19.8）。

**常见错误**: 在计算位置时混用 dp 和像素值。所有 UI 尺寸都应使用 dp 或者从 widget 的 width/height 动态计算。

---

## 14. GitHub Actions Release 权限 403 错误

**现象**:
```
⚠️ GitHub release failed with status: 403
{"message":"Resource not accessible by integration"}
```

**根因**: GitHub Actions 的默认 `GITHUB_TOKEN` 权限是只读的，无法创建 Release 或上传附件。

**解决方案**: 在 workflow 文件的顶层（`on:` 同级）加上权限声明：
```yaml
permissions:
  contents: write
```

---

## 快速检查清单（新项目启动前过一遍）

- [ ] 中文字体文件大小 > 3MB？
- [ ] `source.include_exts` 包含 `ttf`？
- [ ] CJK 字体的 Label 里没有 ASCII 字符？
- [ ] 卡牌尺寸是动态计算的（不是硬编码 dp 值）？
- [ ] 蜘蛛纸牌规则：空列可放任何牌，不只是 K？
- [ ] 拖放容差 ≥ 80dp？
- [ ] GitHub Actions 用 `ubuntu-22.04` 不是 `ubuntu-latest`？
- [ ] Buildozer 和 Cython 版本已固定？
- [ ] 外部存储权限已声明？
- [ ] 动画期间已屏蔽触摸输入？
- [ ] workflow 加了 `permissions: contents: write`？
