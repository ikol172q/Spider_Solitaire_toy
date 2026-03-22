"""蜘蛛纸牌规则验证模块"""


def is_valid_move(card_or_sequence, target_col):
    """验证移动是否合法

    规则：
    - 卡牌可以放在比其级别高1的卡牌上（例如3可以放在4上）
    - 如果目标列为空，任何牌都可以放入（蜘蛛纸牌标准规则）
    - 花色可以不同（但只有同花色序列才能被整体移动或收集）

    参数：
        card_or_sequence: 单张卡牌或卡牌序列（列表）
        target_col: 目标列（列表）

    返回：
        True 如果移动合法，False 否则
    """
    # 处理序列或单张卡牌
    if isinstance(card_or_sequence, list):
        moving_card = card_or_sequence[0]  # 序列的顶部卡牌
    else:
        moving_card = card_or_sequence

    # 目标列为空，任何牌都可以放入（蜘蛛纸牌标准规则）
    if not target_col:
        return True

    target_top_card = target_col[-1]

    # 移动的卡牌级别必须是目标卡牌级别减1
    return moving_card.rank == target_top_card.rank - 1


def is_complete_sequence(cards):
    """检查是否为完整的King→Ace同花色序列

    完整序列的条件：
    - 13张卡牌，从K（13）到A（1）
    - 所有卡牌花色相同
    - 严格递减

    参数：
        cards: 卡牌列表

    返回：
        True 如果是完整序列，False 否则
    """
    if len(cards) != 13:
        return False

    # 检查花色是否相同
    suit = cards[0].suit
    if not all(card.suit == suit for card in cards):
        return False

    # 检查级别是否从K到A严格递减
    for i, card in enumerate(cards):
        if card.rank != 13 - i:
            return False

    return True


def is_movable_sequence(cards):
    """检查序列是否同花色递减可移动

    可移动序列的条件：
    - 所有卡牌花色相同
    - 级别严格递减

    参数：
        cards: 卡牌列表

    返回：
        True 如果可移动，False 否则
    """
    if not cards:
        return False

    suit = cards[0].suit

    # 检查所有卡牌花色是否相同
    if not all(card.suit == suit for card in cards):
        return False

    # 检查级别是否严格递减
    for i in range(len(cards) - 1):
        if cards[i].rank != cards[i + 1].rank + 1:
            return False

    return True


def can_deal(columns):
    """检查是否可以发新牌

    发牌的前置条件：
    - 所有10列都必须非空

    参数：
        columns: 10个列表，表示10列牌堆

    返回：
        True 如果可以发牌，False 否则
    """
    return all(column for column in columns)
