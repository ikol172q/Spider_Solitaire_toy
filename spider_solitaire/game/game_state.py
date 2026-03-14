"""游戏状态管理模块"""

import copy
import time
from .card import Card
from .deck import create_deck, shuffle_deck
from .rules import is_valid_move, is_complete_sequence, is_movable_sequence, can_deal


class GameState:
    """蜘蛛纸牌游戏状态

    属性：
        columns: 10个列表，表示10列牌堆
        stock: 待发牌堆（最多5组，每组10张）
        completed: 已完成的牌组列表（每个元素是13张完整序列）
        score: 分数（初始500，每次移牌-1，完成一组+100）
        moves: 移动次数
        elapsed_time: 已用时间（秒）
        start_time: 游戏开始时间戳
        history: 撤销历史栈
        difficulty: 难度等级
    """

    def __init__(self, difficulty='easy'):
        """初始化游戏状态

        参数：
            difficulty: 难度等级 ('easy', 'medium', 'hard')
        """
        self.difficulty = difficulty
        self.columns = [[] for _ in range(10)]
        self.stock = []
        self.completed = []
        self.score = 500
        self.moves = 0
        self.elapsed_time = 0
        self.start_time = None
        self.history = []

    def new_game(self, difficulty=None):
        """开始新游戏

        参数：
            difficulty: 难度等级，如果提供则覆盖初始难度
        """
        if difficulty:
            self.difficulty = difficulty

        # 重置游戏状态
        self.columns = [[] for _ in range(10)]
        self.stock = []
        self.completed = []
        self.score = 500
        self.moves = 0
        self.elapsed_time = 0
        self.start_time = time.time()
        self.history = []

        # 创建和洗牌
        deck = create_deck(self.difficulty)
        shuffle_deck(deck)

        # 初始发牌
        self.deal_initial(deck)

        # 将剩余牌放入stock
        self.stock = deck

    def deal_initial(self, deck):
        """初始发牌（左4列6张，右6列5张，仅最底下的正面朝上）

        参数：
            deck: 已洗好的牌组列表（该方法会将使用过的卡牌从deck中移除）
        """
        # 左4列每列6张
        for col_idx in range(4):
            for _ in range(6):
                card = deck.pop(0)
                card.face_up = False
                self.columns[col_idx].append(card)

        # 右6列每列5张
        for col_idx in range(4, 10):
            for _ in range(5):
                card = deck.pop(0)
                card.face_up = False
                self.columns[col_idx].append(card)

        # 将所有最顶部的卡牌翻正
        for col_idx in range(10):
            if self.columns[col_idx]:
                self.columns[col_idx][-1].face_up = True

    def deal_row(self):
        """从stock发一行牌（10张，每列1张）

        前置条件：
        - 所有列必须非空
        - stock必须至少有10张牌

        返回：
            True 如果成功发牌，False 否则
        """
        # 检查是否所有列都非空
        if not can_deal(self.columns):
            return False

        # 检查stock是否有足够的牌
        if len(self.stock) < 10:
            return False

        self.save_state()

        # 发牌
        for col_idx in range(10):
            card = self.stock.pop()
            card.face_up = True
            self.columns[col_idx].append(card)

        self.score -= 1
        self.moves += 1

        return True

    def move_cards(self, from_col, card_index, to_col):
        """移动卡牌

        参数：
            from_col: 源列索引 (0-9)
            card_index: 源列中的卡牌索引
            to_col: 目标列索引 (0-9)

        返回：
            True 如果移动成功，False 否则
        """
        # 验证参数
        if not 0 <= from_col < 10 or not 0 <= to_col < 10:
            return False

        if not 0 <= card_index < len(self.columns[from_col]):
            return False

        # 获取要移动的卡牌序列
        moving_sequence = self.columns[from_col][card_index:]

        # 检查移动的合法性
        if not self.can_move(from_col, card_index, to_col):
            return False

        self.save_state()

        # 执行移动
        self.columns[to_col].extend(moving_sequence)
        del self.columns[from_col][card_index:]

        # 翻开源列的顶部卡牌
        self.flip_top_card(from_col)

        self.score -= 1
        self.moves += 1

        # 检查目标列是否有完整序列
        self.check_complete(to_col)

        return True

    def can_move(self, from_col, card_index, to_col):
        """检查是否可以移动

        参数：
            from_col: 源列索引
            card_index: 源列中的卡牌索引
            to_col: 目标列索引

        返回：
            True 如果可以移动，False 否则
        """
        # 同列不能移动
        if from_col == to_col:
            return False

        # 源列必须存在该卡牌
        if card_index >= len(self.columns[from_col]):
            return False

        # 获取移动的序列
        moving_sequence = self.columns[from_col][card_index:]

        # 检查移动的序列是否合法（必须是同花色递减）
        if not is_movable_sequence(moving_sequence):
            return False

        # 检查目标位置是否合法
        return is_valid_move(moving_sequence[0], self.columns[to_col])

    def check_complete(self, col):
        """检查某列是否有完成的K→A序列，如有则移除

        参数：
            col: 列索引
        """
        # 检查是否至少有13张卡牌
        if len(self.columns[col]) < 13:
            return

        # 获取最后13张卡牌
        sequence = self.columns[col][-13:]

        # 如果是完整序列则移除
        if is_complete_sequence(sequence):
            self.completed.append(sequence[:])  # 复制序列
            del self.columns[col][-13:]
            self.score += 100
            self.flip_top_card(col)

    def flip_top_card(self, col):
        """翻开某列最上面的暗牌

        参数：
            col: 列索引
        """
        if self.columns[col] and not self.columns[col][-1].face_up:
            self.columns[col][-1].face_up = True

    def undo(self):
        """撤销上一步

        返回：
            True 如果撤销成功，False 如果历史栈为空
        """
        if not self.history:
            return False

        state = self.history.pop()
        self.columns = state['columns']
        self.stock = state['stock']
        self.completed = state['completed']
        self.score = state['score']
        self.moves = state['moves']

        return True

    def save_state(self):
        """保存当前状态用于撤销"""
        state = {
            'columns': copy.deepcopy(self.columns),
            'stock': copy.deepcopy(self.stock),
            'completed': copy.deepcopy(self.completed),
            'score': self.score,
            'moves': self.moves
        }
        self.history.append(state)

    def is_won(self):
        """判断是否胜利（8组完成）

        返回：
            True 如果已完成8组，False 否则
        """
        return len(self.completed) == 8

    def get_movable_sequence(self, col, card_index):
        """获取可移动的序列（同花色递减）

        参数：
            col: 列索引
            card_index: 卡牌在列中的索引

        返回：
            卡牌序列列表，如果不可移动则返回None
        """
        if card_index >= len(self.columns[col]):
            return None

        sequence = self.columns[col][card_index:]

        if is_movable_sequence(sequence):
            return sequence

        return None

    def to_dict(self):
        """序列化游戏状态为字典"""
        return {
            'difficulty': self.difficulty,
            'columns': [[card.to_dict() for card in col] for col in self.columns],
            'stock': [card.to_dict() for card in self.stock],
            'completed': [
                [card.to_dict() for card in sequence]
                for sequence in self.completed
            ],
            'score': self.score,
            'moves': self.moves,
            'elapsed_time': self.elapsed_time
        }

    @staticmethod
    def from_dict(data):
        """从字典反序列化游戏状态"""
        game = GameState(data['difficulty'])
        game.columns = [
            [Card.from_dict(card_data) for card_data in col]
            for col in data['columns']
        ]
        game.stock = [Card.from_dict(card_data) for card_data in data['stock']]
        game.completed = [
            [Card.from_dict(card_data) for card_data in sequence]
            for sequence in data['completed']
        ]
        game.score = data['score']
        game.moves = data['moves']
        game.elapsed_time = data['elapsed_time']
        return game

    def update_elapsed_time(self):
        """更新已用时间"""
        if self.start_time:
            self.elapsed_time = int(time.time() - self.start_time)
