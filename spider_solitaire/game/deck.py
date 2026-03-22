"""牌组管理模块"""

import random
from .card import Card

ALL_SUITS = ['spade', 'heart', 'diamond', 'club']


def create_deck(difficulty):
    """根据难度创建104张牌，花色随机选择

    参数：
        difficulty: 难度等级 ('easy', 'medium', 'hard')
            - easy: 1花色（随机选1种），8套共104张
            - medium: 2花色（随机选2种），各4套共104张
            - hard: 4花色，各2套共104张

    返回：
        包含104张Card对象的列表
    """
    if difficulty == 'easy':
        # 经典设计：只用黑桃，8套
        suits = ['spade'] * 8
    elif difficulty == 'medium':
        # 经典设计：固定用黑桃(黑)和红心(红)，各4套
        # Windows 经典蜘蛛纸牌中级一直使用这两种花色，一黑一红天然易区分
        suits = ['spade', 'heart'] * 4
    elif difficulty == 'hard':
        # 4种花色，各2套
        suits = ALL_SUITS * 2
    else:
        raise ValueError(f"无效的难度: {difficulty}")

    deck = []
    for suit_type in suits:
        # 每种花色创建13张牌（A到K）
        for rank in range(1, 14):
            deck.append(Card(suit_type, rank, face_up=False))

    return deck


def shuffle_deck(deck):
    """洗牌

    参数：
        deck: 牌组列表
    """
    random.shuffle(deck)
