"""蜘蛛纸牌 UI 主题配置"""

import os
from kivy.metrics import dp

# 字体路径
_ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), 'assets', 'fonts')
FONT_CJK = os.path.join(_ASSETS, 'chinese.ttf')   # CJK 字体
FONT_DEFAULT = 'Roboto'                            # Kivy 默认（Latin + 符号）

# 颜色主题 (RGBA)
BACKGROUND_COLOR = (0.15, 0.4, 0.15, 1)      # 深绿色牌桌
CARD_COLOR = (1, 1, 1, 1)                    # 白色卡面
CARD_BACK_COLOR = (0.1, 0.15, 0.4, 1)        # 深蓝色牌背
RED_SUIT_COLOR = (0.85, 0.1, 0.1, 1)         # 红色花色 (heart, diamond)
BLACK_SUIT_COLOR = (0.1, 0.1, 0.1, 1)        # 黑色花色 (spade, club)
HIGHLIGHT_COLOR = (1, 1, 0, 0.3)             # 选中高亮 (黄色半透明)
EMPTY_SLOT_COLOR = (1, 1, 1, 0.2)            # 空位边框 (白色半透明)
TEXT_COLOR = (0.2, 0.2, 0.2, 1)              # 文本颜色 (深灰色)
BUTTON_COLOR = (0.2, 0.5, 0.2, 1)            # 按钮颜色 (绿色)
BUTTON_HOVER_COLOR = (0.3, 0.6, 0.3, 1)      # 按钮悬停颜色
BUTTON_PRESS_COLOR = (0.1, 0.35, 0.1, 1)     # 按钮按下颜色

# 卡牌尺寸（dp单位，相对大小）
# 基准：Huawei Mate 30 - 2376×1080，宽度为410mm≈1080dp
CARD_WIDTH = dp(60)                          # 卡牌宽度
CARD_HEIGHT = dp(85)                         # 卡牌高度
CARD_RADIUS = dp(4)                          # 圆角半径

# 卡牌间距
CARD_OVERLAP_CLOSED = dp(15)                 # 背面卡牌重叠距离
CARD_OVERLAP_OPEN = dp(25)                   # 正面卡牌重叠距离
CARD_SPACING = dp(8)                         # 列间距

# 字体大小
FONT_SIZE_LARGE = dp(28)                     # 大标题
FONT_SIZE_TITLE = dp(18)                     # 标题
FONT_SIZE_NORMAL = dp(14)                    # 普通文字
FONT_SIZE_SMALL = dp(12)                     # 小文字
FONT_SIZE_SUIT = dp(20)                      # 花色符号大小

# 其他尺寸
BUTTON_WIDTH = dp(80)                        # 按钮宽度
BUTTON_HEIGHT = dp(40)                       # 按钮高度
STATUS_BAR_HEIGHT = dp(56)                   # 状态栏高度（标签+数值双行）
PADDING = dp(10)                             # 内边距
MARGIN = dp(15)                              # 外边距

# 动画时长（秒）
CARD_MOVE_DURATION = 0.3                     # 卡牌移动动画
