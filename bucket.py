from typing import Dict, List, Tuple
from api import client
import time


class Bucket:
    def __init__(self, lst: List[str], snapshot_queue_size):
        self.lst = lst
        self.suspension_queue = []

        self.snapshot_queue_size = snapshot_queue_size
        self.snapshot_queue = []
        self.average_snapshot = None
        self.cache_snapshot = None

        self.prices = self.get_prices()

    def max_fall(self) -> Tuple[str, float]:
        symbol = self.lst[0][:-4]
        price = self.prices[0][symbol][0]
        snapshot = self.average_snapshot[0][symbol][0]
        max_ = (price - snapshot) / snapshot * 100

        for i in range(1, len(self.lst)):
            symbol_new = self.lst[i][:-4]
            price_new = self.prices[0][symbol_new][0]
            snapshot_new = self.average_snapshot[0][symbol_new][0]
            max_new = (price_new - snapshot_new) / snapshot_new * 100
            if max_new < max_:
                max_ = max_new
                symbol = symbol_new
        return symbol, max_

    def max_rise(self) -> Tuple[str, float]:
        symbol = self.lst[0][:-4]
        price = self.prices[0][symbol][0]
        snapshot = self.average_snapshot[0][symbol][0]
        max_ = (price - snapshot) / snapshot * 100

        for i in range(1, len(self.lst)):
            symbol_new = self.lst[i][:-4]
            price_new = self.prices[0][symbol_new][0]
            snapshot_new = self.average_snapshot[0][symbol_new][0]
            max_new = (price_new - snapshot_new) / snapshot_new * 100
            if max_new > max_:
                max_ = max_new
                symbol = symbol_new
        return symbol, max_

    def suspend(self, coin: str):
        pair = coin + 'USDT'
        price = self.prices[0][coin][0]
        self.lst.remove(pair)
        self.suspension_queue.append((pair, time.time(), price))

    def unsuspend(self, index=0):
        self.lst.append(self.suspension_queue.pop(index)[0])

    def take_snapshot(self):
        """Take a snapshot and calculate the average in the queue"""
        self.snapshot_queue.append(self.get_prices())

        if len(self.snapshot_queue) > self.snapshot_queue_size:
            self.snapshot_queue.pop(0)

        dict_ = {}
        for coin in self.snapshot_queue[0][0]:
            lst_snapshot = []
            lst_24hr = []
            for i in range(len(self.snapshot_queue)):
                lst_snapshot.append(self.snapshot_queue[i][0][coin][0])
                lst_24hr.append(self.snapshot_queue[i][0][coin][1])
            avg_snapshot = sum(lst_snapshot) / len(lst_snapshot)
            avg_24hr = sum(lst_24hr) / len(lst_24hr)
            dict_[coin] = avg_snapshot, avg_24hr

        self.average_snapshot = dict_, self.snapshot_queue[-1][1]

    def get_prices(self) -> Tuple[Dict, float]:
        dict = {}
        for pair in self.lst:
            dict[pair[:-4]] = (float(client.get_symbol_ticker(symbol=pair)['price']),
                               float(client.get_ticker(symbol=pair)['priceChangePercent']))
        for symbol in self.suspension_queue:
            dict[symbol[0][:-4]] = (float(client.get_symbol_ticker(symbol=symbol[0])['price']),
                                    float(client.get_ticker(symbol=symbol[0])['priceChangePercent']))
        return dict, time.time()

    def get_24hr_avg_delta(self):
        sum_ = 0
        for pair in self.lst:
            sum_ += self.prices[0][pair[:-4]][1]
        for symbol in self.suspension_queue:
            sum_ += self.prices[0][symbol[0][:-4]][1]
        return sum_ / (len(self.lst) + len(self.suspension_queue))
