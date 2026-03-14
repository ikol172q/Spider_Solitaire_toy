# 蜘蛛纸牌 (Spider Solitaire)

经典蜘蛛纸牌游戏的 Android 版本，使用 Python + Kivy 开发，可安装在华为 Mate 40 等 Android 手机上。

## 游戏特点

- **三种难度**：初级（1种花色）、中级（2种花色）、高级（4种花色）
- **触屏操作**：拖拽移牌，点击发牌
- **撤销功能**：无限撤销
- **计分计时**：记录分数、步数和用时
- **自动存档**：退出时自动保存，下次可继续

## 游戏规则

使用 104 张牌，分发到 10 列牌堆：

- 左边 4 列各 6 张，右边 6 列各 5 张，只有每列最底下的牌正面朝上
- 剩余 50 张放在右下角待发牌堆（可发 5 次，每次 10 张）
- 可以将牌移到空列，或移到点数比它大 1 的牌上面（不限花色）
- 同花色、递减排列的连续序列可以作为整体移动
- 当同花色从 K 到 A 完整排列后，自动移除
- 发新牌前所有列必须非空
- 8 组全部收完即为胜利

## 项目结构

```
├── main.py                    # 应用入口
├── buildozer.spec             # Android APK 打包配置
├── spider_solitaire/
│   ├── game/                  # 游戏逻辑（纯 Python）
│   │   ├── card.py            # 卡牌模型
│   │   ├── deck.py            # 牌组管理
│   │   ├── game_state.py      # 游戏状态
│   │   └── rules.py           # 规则引擎
│   └── ui/                    # Kivy 界面
│       ├── card_widget.py     # 卡牌绘制
│       ├── board_widget.py    # 棋盘布局与触摸
│       ├── game_screen.py     # 游戏主界面
│       ├── menu_screen.py     # 菜单界面
│       └── theme.py           # 主题配色
├── tests/
│   └── test_game.py           # 单元测试（39 个）
└── LICENSE                    # MIT 许可证
```

## 桌面运行（开发调试）

```bash
# 创建虚拟环境
python3 -m venv spider_env
source spider_env/bin/activate

# 安装依赖
pip install kivy==2.3.1

# 运行
python main.py

# 运行测试
pip install pytest
pytest tests/ -v
```

## 构建 Android APK

需要在 Linux 或 macOS 上使用 Buildozer：

```bash
# 安装系统依赖（Ubuntu）
sudo apt install -y git zip unzip openjdk-17-jdk autoconf libtool \
    pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
    cmake libffi-dev libssl-dev

# 安装 Buildozer
pip install buildozer cython

# 构建 debug APK
buildozer android debug

# APK 产出路径
ls bin/spidersolitaire-1.0.0-arm64-v8a-debug.apk
```

构建好的 APK 可以直接安装到华为 Mate 40 上运行。

## 发布版本 (GitHub Releases)

本项目已配置 GitHub Actions 自动构建。当推送版本标签时，会自动构建 APK 并创建 Release 页面（含下载链接）。

### 自动发布流程

```bash
# 1. 确保代码已提交并推送
git add -A
git commit -m "你的提交信息"
git push origin main

# 2. 创建版本标签
git tag v0.1.0

# 3. 推送标签 → 触发自动构建
git push origin v0.1.0
```

推送标签后，GitHub Actions 会自动：构建 APK → 创建 Release 页面 → 附上 APK 下载链接。

进度可在仓库的 **Actions** 标签页查看，完成后在 **Releases** 页面即可下载 APK。

### 手动发布

也可以在 GitHub 网页上手动创建 Release：

1. 进入仓库页面，点击右侧 **Releases**
2. 点击 **Draft a new release**
3. 在 "Choose a tag" 输入新标签名（如 `v0.1.0`）并创建
4. 填写标题和说明
5. 在底部 "Attach binaries" 区域上传本地构建好的 APK 文件
6. 点击 **Publish release**

### 版本号规范

建议使用语义版本号：`v主版本.次版本.修订号`，例如 `v0.1.0`（首个测试版）、`v1.0.0`（正式版）。

## 技术栈

- **Python 3.10+** — 游戏逻辑和界面
- **Kivy 2.3.1** — 跨平台 GUI 框架（MIT 许可）
- **Buildozer 1.5.0** — Android APK 打包工具（MIT 许可）

## 版权说明

- 游戏代码：MIT License
- 所有卡牌图形由代码绘制，无外部图片依赖
- 花色符号使用 Unicode 字符（公共领域）
- 蜘蛛纸牌是传统纸牌游戏，规则不受版权保护
- 字体：DroidSansFallback（Apache License 2.0，免费）、DejaVuSans（Bitstream Vera License，免费）
- Kivy 框架：MIT License（免费）
- Buildozer：MIT License（免费）
