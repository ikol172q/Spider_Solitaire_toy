# 发布 & 测试指南

## 一、日常开发流程

```bash
# 1. 进入项目目录 & 激活虚拟环境
cd ~/Desktop/Spiker_Solitaire/Spider_Solitaire_toy
spider_env

# 2. 修改代码后，本地运行测试
python -m pytest tests/ -v --tb=short

# 3. 本地桌面预览（可选）
python main.py

# 4. 提交代码
git add -A
git commit -m "描述你的改动"
git push origin main
```

---

## 二、发布新版本 APK

### 方式 A：发布新版本号（推荐）

```bash
git tag v0.1.4
git push origin v0.1.4
```

GitHub Actions 自动触发构建，版本号从 tag 名自动提取。构建完成后（约 30-60 分钟），APK 出现在：
`https://github.com/ikol172q/Spider_Solitaire_toy/releases/tag/v0.1.4`

### 方式 B：覆盖现有版本号重新构建

```bash
# 删除本地和远程的旧 tag
git tag -d v0.1.3
git push origin :refs/tags/v0.1.3

# 在最新 commit 上重新打 tag
git tag v0.1.3
git push origin v0.1.3
```

### 查看构建状态

浏览器打开：`https://github.com/ikol172q/Spider_Solitaire_toy/actions`

---

## 三、Android Studio 模拟器测试

### 首次设置（只需做一次）

1. 打开 Android Studio → 欢迎页 → **More Actions** → **Virtual Device Manager**
2. 点 **+** → **New Hardware Profile**
3. 填入 Mate 30 参数：
   - Device Name: `Huawei Mate 30`
   - Screen Size: `6.62`
   - Resolution: `1080 x 2340`
   - RAM: `4096`
4. 点 Finish → 选中 Mate 30 → Next
5. API 选 **API 33 "Tiramisu"**，架构 **ARM 64 v8a** → 下载 → Finish

### 每次测试流程

```bash
# 1. 启动模拟器（在 Device Manager 里点播放按钮，或用命令行）
emulator -avd Huawei_Mate_30

# 2. 卸载旧版本（必须！debug 签名每次不同）
adb uninstall org.spidertoy.spidersolitaire

# 3. 安装新 APK（二选一）
# 方式 a: 命令行
adb install ~/Downloads/SpiderSolitaire-0.1.3-arm64-v8a-debug.apk
# 方式 b: 直接把 APK 文件拖到模拟器窗口上

# 4. 打开日志监控（另开一个终端窗口）
adb logcat -s python

# 5. 在模拟器里点击 Spider Solitaire 图标启动 app
# 如果闪退，终端会立即显示 Python traceback
```

### 常用 adb 命令

```bash
# 查看已连接设备
adb devices

# 卸载 app
adb uninstall org.spidertoy.spidersolitaire

# 安装 APK
adb install path/to/your.apk

# 查看 Python 日志（闪退排查）
adb logcat -s python

# 保存完整日志到文件
adb logcat -s python | tee crash.log

# 截图
adb exec-out screencap -p > screenshot.png
```

### 安装失败处理

| 错误 | 解决方法 |
|------|---------|
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | 先运行 `adb uninstall org.spidertoy.spidersolitaire` |
| `INSTALL_FAILED_OLDER_SDK` | 检查 buildozer.spec 的 `android.minapi` |
| 拖拽安装无反应 | 用 `adb install` 命令行安装 |

---

## 四、真机安装（华为 Mate 30）

1. 从 GitHub Releases 下载 APK 到手机（或电脑传到手机）
2. 设置 → 安全 → 允许安装未知来源应用
3. 文件管理器找到 APK → 点击安装
4. 弹出"未经华为安全检测"→ 选"仍然安装"

---

## 五、完整发布检查清单

- [ ] `python -m pytest tests/ -v` 全部通过
- [ ] `python main.py` 桌面预览正常
- [ ] 代码已 push 到 main
- [ ] 打 tag 触发 GitHub Actions 构建
- [ ] GitHub Actions 构建成功（绿色 ✓）
- [ ] 模拟器卸载旧版 → 安装新 APK
- [ ] 模拟器上 app 正常启动（不闪退）
- [ ] 竖屏 & 横屏都正常显示
- [ ] 中文文字不乱码
- [ ] 长按弹窗可读
- [ ] 辅助浮框显示正确
- [ ] 发牌、拖拽、撤销功能正常
- [ ] 真机安装测试（可选）
