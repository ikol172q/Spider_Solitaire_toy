# 本地测试 & 华为 Mate 40 安装指南

---

## 一、本地测试（电脑上运行游戏）

### 1.1 环境准备

你的电脑上需要 Python 3.8+。打开终端（Windows 用 PowerShell 或 CMD）：

```bash
# 确认 Python 版本
python3 --version   # macOS/Linux
python --version    # Windows
```

### 1.2 安装步骤

```bash
# 1) 克隆仓库
git clone https://github.com/ikol172q/Spider_Solitaire_toy.git
cd Spider_Solitaire_toy

# 2) 创建虚拟环境
python3 -m venv spider_env          # macOS/Linux
python -m venv spider_env           # Windows

# 3) 激活虚拟环境
source spider_env/bin/activate      # macOS/Linux
spider_env\Scripts\activate         # Windows (CMD)
spider_env\Scripts\Activate.ps1     # Windows (PowerShell)

# 4) 安装 Kivy
pip install kivy==2.3.1

# 5) 运行游戏！
python main.py
```

### 1.3 你会看到什么

游戏启动后会弹出一个 420×920 的窗口（模拟 Mate 40 竖屏比例）：

1. **菜单界面**：深绿色背景，显示"蜘蛛纸牌"标题和三个难度按钮
2. 点击任一难度按钮进入游戏
3. **游戏界面**：
   - 顶部：分数、步数、计时器、难度
   - 中央：10 列卡牌（白色正面、蓝色背面）
   - 底部：撤销、新游戏、菜单按钮
   - 右下角：待发牌堆（点击发牌）

### 1.4 操作方式（鼠标模拟触屏）

| 操作 | 鼠标动作 |
|------|----------|
| 移牌 | 点击一张正面朝上的牌 → 拖动到目标列 → 松开 |
| 发新牌 | 点击右下角的"发牌"牌堆 |
| 撤销 | 点击底部"撤销"按钮 |
| 新游戏 | 点击底部"新游戏"按钮 |
| 返回菜单 | 点击底部"菜单"按钮 |

### 1.5 运行单元测试

```bash
# 确保虚拟环境已激活
pip install pytest
pytest tests/ -v
```

应该看到 39 个测试全部 PASSED：
```
tests/test_game.py::TestCard::test_card_creation PASSED
tests/test_game.py::TestCard::test_card_comparison PASSED
...
tests/test_game.py::TestGameState::test_is_won PASSED
============================== 39 passed ==============================
```

### 1.6 常见问题

**Q: 运行 `python main.py` 报错 `No module named 'kivy'`**
→ 确认虚拟环境已激活（终端提示符前应有 `(spider_env)`）

**Q: Windows 上 Kivy 安装失败**
→ 试试：`pip install kivy[base]`

**Q: 画面显示异常**
→ 尝试设置环境变量：`export KIVY_GL_BACKEND=angle_sdl2`（Windows）

---

## 二、构建 Android APK

### 2.1 系统要求

- **操作系统**：Linux（推荐 Ubuntu 20.04/22.04）或 macOS
- **磁盘空间**：至少 5GB（Android SDK + NDK 较大）
- **内存**：4GB+ RAM
- **Windows 用户**：请使用 WSL2（Windows Subsystem for Linux）

### 2.2 安装系统依赖（Ubuntu）

```bash
sudo apt update
sudo apt install -y \
    git zip unzip \
    openjdk-17-jdk \
    autoconf libtool \
    pkg-config \
    zlib1g-dev \
    libncurses5-dev libncursesw5-dev \
    cmake \
    libffi-dev libssl-dev \
    python3-pip python3-venv
```

### 2.3 安装 Python 依赖

```bash
cd Spider_Solitaire_toy
python3 -m venv spider_env
source spider_env/bin/activate
pip install kivy==2.3.1 buildozer cython
```

### 2.4 构建 APK

```bash
# 构建 debug APK（首次构建约 15-30 分钟，会自动下载 Android SDK/NDK）
buildozer android debug

# 构建完成后，APK 在 bin/ 目录：
ls bin/
# → spidersolitaire-1.0.0-arm64-v8a-debug.apk
```

### 2.5 构建常见问题

**Q: 报错 `javac: command not found`**
→ 安装 JDK：`sudo apt install openjdk-17-jdk`

**Q: 报错 `No module named 'cython'`**
→ `pip install cython`

**Q: 构建中途网络超时**
→ Android SDK/NDK 需要从 Google 下载，确保网络通畅。如在中国大陆，可能需要设置代理。

**Q: macOS 上构建**
→ 先安装 Homebrew，然后：
```bash
brew install autoconf automake libtool pkg-config
brew install --cask temurin   # Java JDK
pip install buildozer cython
buildozer android debug
```

---

## 三、在华为 Mate 40 上安装

### 3.1 准备工作

1. **获取 APK 文件**：完成上一步构建后，在 `bin/` 目录找到 `.apk` 文件
2. **传输到手机**：通过以下任一方式：
   - USB 数据线连接电脑 → 复制到手机存储
   - 微信/QQ 发送给自己
   - 邮件附件发送
   - 百度网盘/华为云空间上传后下载

### 3.2 允许安装未知来源应用

华为 Mate 40 默认不允许安装非应用市场的 APK，需要手动开启：

1. 打开手机 **设置**
2. 进入 **安全** → **更多安全设置**
3. 找到 **安装未知应用** 或 **外部来源应用**
4. 选择你用来打开 APK 的应用（如"文件管理器"），打开"允许安装"开关

> 不同 EMUI/HarmonyOS 版本路径可能略有不同：
> - HarmonyOS 2/3：设置 → 安全 → 更多安全设置 → 安装未知应用
> - EMUI 11：设置 → 安全 → 更多设置 → 安装未知应用

### 3.3 安装 APK

1. 打开手机的 **文件管理器**
2. 找到传输过来的 `spidersolitaire-1.0.0-arm64-v8a-debug.apk`
3. 点击该文件
4. 系统会弹出安装确认，点击 **安装**
5. 等待安装完成，点击 **打开** 即可开始游戏

### 3.4 游戏操作（触屏）

| 操作 | 手势 |
|------|------|
| 移牌 | 手指按住一张牌 → 拖动到目标列 → 松开手指 |
| 移动一组牌 | 按住同花色递减序列最上面的牌 → 拖动整组 |
| 发新牌 | 点击右下角牌堆 |
| 撤销 | 点击底部"撤销"按钮 |
| 新游戏 | 点击底部"新游戏"按钮 |

### 3.5 卸载

设置 → 应用和服务 → 应用管理 → 找到"Spider Solitaire" → 卸载

---

## 四、快速参考

```
# 本地运行
python main.py

# 运行测试
pytest tests/ -v

# 构建 APK
buildozer android debug

# APK 位置
bin/spidersolitaire-1.0.0-arm64-v8a-debug.apk
```
