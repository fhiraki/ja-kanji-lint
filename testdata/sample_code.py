# -*- coding: utf-8 -*-
"""サンプルモジュール: コメントに中国語系の漢字が混入している。"""


def calc_total(items):
    # 合计を計算する。负の値は无視する。
    total = 0
    for price in items:
        total += price
    return total


class Receipt(object):
    """領収書を表す。"""
    def __init__(self, shop):
        self.shop = shop  # 販壳元の名称
        self.items = []

    def add(self, price):
        # 电话番号は記録しない(玒中の個人情報に注意)
        self.items.append(price)
        return "https://example.com/開発/支出"  # URL の文字列は走査対象外


def render(receipt):
    """HTML を組み立てる。"""
    # 諸费用を集计して返す
    html = "<p>合計: %d</p>" % calc_total(receipt.items)
    return html
