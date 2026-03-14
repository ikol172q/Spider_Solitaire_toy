"""蜘蛛纸牌的卡牌模型"""

# 花色常量
SUITS = {
    'spade': '♠',
    'heart': '♥',
    'diamond': '♦',
    'club': '♣'
}

# 级别名称
RANK_NAMES = {
    1: 'A', 2: '2', 3: '3', 4: '4', 5: '5',
    6: '6', 7: '7', 8: '8', 9: '9', 10: '10',
    11: 'J', 12: 'Q', 13: 'K'
}


class Card:
    """代表一张纸牌

    属性：
        suit: 花色 ('spade', 'heart', 'diamond', 'club')
        rank: 级别 (1-13, 1=A, 13=K)
        face_up: 是否正面朝上
    """

    def __init__(self, suit, rank, face_up=False):
        """初始化卡牌

        参数：
            suit: 花色字符串
            rank: 级别整数 (1-13)
            face_up: 是否正面朝上，默认为False
        """
        if suit not in SUITS:
            raise ValueError(f"无效的花色: {suit}")
        if not 1 <= rank <= 13:
            raise ValueError(f"无效的级别: {rank}")

        self.suit = suit
        self.rank = rank
        self.face_up = face_up

    def __eq__(self, other):
        """比较两张卡牌是否相等"""
        if not isinstance(other, Card):
            return False
        return self.suit == other.suit and self.rank == other.rank

    def __lt__(self, other):
        """比较卡牌级别大小"""
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank < other.rank

    def __le__(self, other):
        """比较卡牌级别是否小于等于"""
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank <= other.rank

    def __gt__(self, other):
        """比较卡牌级别大小"""
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank > other.rank

    def __ge__(self, other):
        """比较卡牌级别是否大于等于"""
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank >= other.rank

    def __repr__(self):
        """返回卡牌的详细字符串表示"""
        return f"Card({self.suit}, {self.rank}, face_up={self.face_up})"

    def __str__(self):
        """返回卡牌的简洁字符串表示，如 'A♠', 'K♥' 等"""
        if not self.face_up:
            return "🂠"  # 背面牌符号
        rank_name = RANK_NAMES[self.rank]
        suit_symbol = SUITS[self.suit]
        return f"{rank_name}{suit_symbol}"

    def to_dict(self):
        """序列化卡牌为字典"""
        return {
            'suit': self.suit,
            'rank': self.rank,
            'face_up': self.face_up
        }

    @staticmethod
    def from_dict(data):
        """从字典反序列化卡牌"""
        return Card(data['suit'], data['rank'], data['face_up'])
