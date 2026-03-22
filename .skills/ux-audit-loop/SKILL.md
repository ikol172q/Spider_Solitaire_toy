---
name: ux-audit-loop
description: |
  自动化 UX 审计循环：围绕"用户轻松快乐玩游戏，贴近经典体验"的核心诉求，
  执行 N 轮"搜索→审计→修复→验证"循环。每轮独立搜索新角度，避免重复材料，
  直到找不到新问题为止。用户只需说"审计 N 轮"即可启动。
  USE THIS SKILL whenever: 用户要求审计游戏体验、检查 bug、搜索经典设计对比、
  站在用户角度检查、杜绝问题、或要求"再搜索检查一遍"。
---

# UX 审计循环 (UX Audit Loop)

## 核心原则

玩家要的不是"正确的程序"，而是"放空脑子、进入心流、轻松快乐"的体验。
每一轮审计都必须站在**一个从未玩过这个游戏的普通玩家**的角度，
问自己："前 30 秒会不会觉得哪里不对劲？"

## 触发方式

用户会说类似这样的话：
- "审计 5 轮"
- "搜索检查 3 次"
- "站在用户角度检查，重复 N 次"

## 审计记录文件

每次审计的结果必须追加写入 `AUDIT_LOG.md`（与 CHANGELOG.md 同级目录）。
这个文件是整个审计过程的"记忆"——后续轮次必须先读取它，跳过已审计的角度。

### AUDIT_LOG.md 格式

```markdown
# 审计记录

## 已覆盖角度
- [x] 经典规则细节 (轮次 1, 日期)
- [x] 玩家投诉 (轮次 2, 日期)
- [ ] 竞品音效设计 (未审计)

## 审计历史

### 第 N 轮 — YYYY-MM-DD
**角度**: ...
**搜索关键词**: "...", "..."
**发现**: N 个
**修复**: N 个
**测试**: 492 passed

| # | 问题 | 严重度 | 来源 | 修复 |
|---|------|--------|------|------|

**验证无问题的项**:
- ✅ ...
```

## 每轮循环（5 步）

### Step 0: 读取审计历史（避免重复）

1. 读取 `AUDIT_LOG.md`，获取已覆盖的角度列表
2. 从角度清单中选择**未覆盖的角度**
3. 如果所有角度都覆盖了，进入"深度延伸"模式（从已发现问题中衍生新搜索）

### Step 1: 搜索（2-3 次全新搜索）

角度清单（按优先级排列）：

| 角度 | 搜索关键词示例 |
|------|---------------|
| 经典规则细节 | spider solitaire "empty column" "any card" rule standard |
| 玩家投诉/bug | spider solitaire "cards stuck" "can't move" "won't let me" |
| UX 交互特性 | spider solitaire "tap card" "auto move" "best position" behavior |
| 视觉设计 | spider solitaire card design "suit symbol" size color contrast |
| 触摸/拖拽 | spider solitaire "drag" "snap back" "follow finger" mobile touch |
| 边缘场景 | spider solitaire "deal" "empty column" "no more moves" stuck |
| 适老化/无障碍 | solitaire "elderly" "senior" accessibility "large text" touch target |
| 性能稳定性 | kivy android performance "too many widgets" "canvas" optimization |
| 竞品对比 | spider solitaire app "feature comparison" "must have" 2025 |
| 视觉一致性 | playing card design standard "top left" corner "rank" "suit" |
| 音效/触感 | solitaire "sound effect" "haptic" "vibration" satisfying feedback |
| 新手引导 | spider solitaire "tutorial" "first time" "how to play" onboarding |

每次搜索使用**具体的英文关键词**，避免和之前轮次重复。

### Step 2: 代码审计

用 Agent（Explore 类型）对照搜索结果做深度代码审计：

1. **规则符合性**：搜索到的标准 vs 我们的代码
2. **玩家体验**：搜索提到的好体验我们有没有
3. **bug 追踪**：模拟玩家操作路径，追踪代码执行
4. **对比表**：经典行为 vs 我们的行为

### Step 3: 修复

对每个发现的问题：
1. 确认是否是真正的问题（不是误报）
2. 写出最小化的修复（不过度重构）
3. 修复后立即运行 `python -m pytest tests/ --tb=short`
4. 如果测试失败，修复测试或修复代码

### Step 4: 记录本轮结果

将本轮结果追加到 `AUDIT_LOG.md`，格式见上。

### Step 5: 判断是否继续

- 连续 **2 轮 0 问题** → 进入全量回归验证
- 达到用户指定的轮次数 N → 进入全量回归验证
- 否则 → 继续下一轮

## 全量回归验证（收尾阶段）

审计轮次结束后（无论是提前终止还是达到 N 轮），必须执行：

1. **运行全部测试**：`python -m pytest tests/ -v --tb=short`
2. **兼容性验证脚本**：运行 Python 脚本验证核心游戏逻辑：
   - 三个难度牌堆数量（104张）
   - 经典花色选择（初级♠、中级♠♥）
   - 初始发牌布局（4×6 + 6×5）
   - 空列规则、移动规则、完成序列检测
   - 撤销恢复、计时器保存/加载
   - 50步模拟卡牌守恒
3. **输出最终总结**：
   - 累计修复清单
   - 全量测试结果
   - git 提交命令
   - 更新 CHANGELOG.md

## 搜索技巧

- 英文搜索效果远好于中文
- 搜索**具体行为**而不是泛泛概念：
  - ❌ "spider solitaire UX"
  - ✅ "spider solitaire tap card nothing happens why"
- 搜索**竞品具体功能**：
  - ✅ "MobilityWare spider solitaire auto complete feature"
- 搜索**玩家投诉**：
  - ✅ "spider solitaire cards stuck can't move"
- **避免重复**：每轮搜索前检查 AUDIT_LOG.md 中的"搜索关键词"记录

## 代码审计技巧

- 读完整文件，不要只 grep 关键词
- 模拟完整操作路径：touch_down → touch_move → touch_up
- 检查所有 `return False` 和 `return None`——"无反馈"的可能来源
- 检查所有动画回调——旋转/退出时是否安全
- 检查所有索引访问——是否可能越界
- 检查所有 `if` 条件——是否覆盖了所有分支
