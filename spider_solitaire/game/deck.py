"""牌组管理模块"""

import random
from .card import Card


def create_deck(difficulty):
    """根据难度创建104张牌

    参数：
        difficulty: 难度等级 ('easy', 'medium', 'hard')
            - easy: 1花色，8套黑桃（104张）
            - medium: 2花色，4套黑桃+4套红心（104张）
            - hard: 4花色，2套四种花色各26张（104张）

    返回：
        包含104张Card对象的列表
    """
    if difficulty == 'easy':
        # 8套黑桃
        suits = ['spade'] * 8
    elif difficulty == 'medium':
        # 4套黑桃和4套红心
        suits = ['spade'] * 4 + ['heart'] * 4
    elif difficulty == 'hard':
        # 2套各种花色
        suits = ['spade', 'heart', 'diamond', 'club'] * 2
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
