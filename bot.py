import time
from typing import Dict, Tuple
from strategy import *
from bucket import Bucket

import math

from api import client


class Bot:
    def __init__(self, strategy_configuration, bucket: Bucket,
                 initial_holding: str, initial_value=None):

        # Bucket Initialization
        self.bucket = bucket

        self.strategy_baselines = strategy_configuration['BASELINE']
        self.strategy_multipliers_24hr = strategy_configuration['24HR']
        self.strategy_multipliers_latest = strategy_configuration['LATEST']

        self.strategy_baseline = strategy_configuration['BASELINE'][0]
        self.strategy_multiplier_24hr = strategy_configuration['24HR'][0]
        self.strategy_multiplier_latest = strategy_configuration['LATEST'][0]

        self.strategy = Strategy(self.strategy_baseline, self.strategy_multiplier_24hr,
                                 self.strategy_multiplier_latest)
        # Portfolio and Market Initialization

        self.current_holding = initial_holding
        if initial_holding != 'USDT':
            price = float(
                client.get_symbol_ticker(symbol=initial_holding + 'USDT')[
                    'price'])
        else:
            price = 1

        initial_balance = float(
            client.get_asset_balance(asset=initial_holding)['free'])

        self.initial_value = initial_balance * price
        print(f'Trading started with {initial_balance} {initial_holding}'
              f'    (worth ${self.initial_value} USDT)')
        if initial_value is not None:
            self.initial_value = initial_value

        self.bucket.take_snapshot()
        print('Price snapshot enqueued')

        # Profit Retention Initialization
        self.profit_snapshot = self.current_profit()
        self.profit_delta = None
        self.priming = False

        self.last_trade_time = time.time()

    def run(self):
        try:
            exit_ = False
            while not exit_:
                self.bucket.prices = self.bucket.get_prices()

                # Analyze market and mutate strategy
                self._strategize()

                # Bucket pruning logic and loop
                self._pruning_loop()

                if self.current_holding == 'USDT':
                    # Fiat-Crypto trading activation logic and loop
                    self._fc_trading_loop()
                else:
                    # Crypto-Fiat trading activation logic and loop
                    self._cf_trading_loop()

                # Check exit strategy
                exit_ = self._exit()

                # Profit retention mechanism
                self._profit_retention()

                # Price and profit snapshot refresh
                self._snapshot_refresh()

                print(self.get_status())

        except Exception as e:
            print(f'Exception raised'
                  f'\n{e}'
                  f'\nRestarting...')
            self.run()

    # Helpers
    ################################################################################

    def get_price(self, symbol: str) -> float:
        """
        Return price as a float of given symbol.
        """
        return self.bucket.prices[0][symbol][0]

    def get_24hr_change(self, symbol: str) -> float:
        """
        Return 24Hr change as a float of given symbol.
        """
        return self.bucket.prices[0][symbol][1]

    def get_status(self) -> str:
        balance = self.get_balance()

        if self.current_holding != 'USDT':
            self.bucket.prices = self.bucket.get_prices()
            price = self.get_price(self.current_holding)
            s = f'Current balance: ' \
                f'{balance} {self.current_holding}' \
                f'  @{price} USDT/{self.current_holding}' \
                f'  ${float(price) * balance} USDT' \
                f'   ||   Current profit: ' \
                f'${float(price) * balance - self.initial_value} USDT'\
                f'\nCurrent strategy: ' \
                f'{self.strategy.name}'
        else:
            s = f'Current balance: ' \
                f'{balance} USDT' \
                f'   ||   Current profit: ' \
                f'${balance - self.initial_value} USDT' \
                f'\nCurrent strategy: ' \
                f'{self.strategy.name}'
        return s

    def _strategize(self) -> bool:

        cardinality = len(self.bucket.prices[0])
        sum_avg = 0
        sum_24hr = 0
        sum_latest = 0

        for coin in self.bucket.prices[0]:

            current_price = self.get_price(coin)
            if current_price > self.bucket.average_snapshot[0][coin][0]:
                sum_avg += 1
            if current_price > self.bucket.snapshot_queue[-1][0][coin][0]:
                sum_latest += 1
            if self.get_24hr_change(coin) > 0:
                sum_24hr += 1

        switched = False

        for baseline in self.strategy_baselines:
            if cardinality * baseline.interval[0] <= \
                    sum_avg <= \
                    cardinality * baseline.interval[1]:

                if self.strategy_baseline.name != baseline.name:
                    print(
                        f'Switching strategy baseline: {self.strategy_baseline.name} -> {baseline.name}')
                    switched |= True
                    self.strategy_baseline = baseline
                break

        for m24hr in self.strategy_multipliers_24hr:
            if cardinality * m24hr.interval[0] <= \
                    sum_24hr <= \
                    cardinality * m24hr.interval[1]:

                if self.strategy_multiplier_24hr.name != m24hr.name:
                    print(
                        f'Switching 24Hr strategy multiplier: {self.strategy_multiplier_24hr.name} -> {m24hr.name}')
                    switched |= True
                    self.strategy_multiplier_24hr = m24hr
                break

        for mlatest in self.strategy_multipliers_latest:
            if cardinality * mlatest.interval[0] <= \
                    sum_latest <= \
                    cardinality * mlatest.interval[1]:

                if self.strategy_multiplier_latest.name != mlatest.name:
                    print(
                        f'Switching latest strategy multiplier: {self.strategy_multiplier_latest.name} -> {mlatest.name}')
                    switched |= True
                    self.strategy_multiplier_latest = mlatest
                break

        if switched:
            self.strategy = Strategy(self.strategy_baseline, self.strategy_multiplier_24hr,
                                     self.strategy_multiplier_latest)

        return switched

    def _pruning_loop(self):
        if self.bucket.lst:
            avg = self.bucket.get_24hr_avg_delta()
            for pair in self.bucket.lst:
                diff = self.bucket.prices[0][pair[:-4]][1] - avg
                if abs(diff) > self.strategy.suspension_threshold:
                    self.bucket.suspend(pair[:-4])
                    print(
                        f'Suspension threshold exceeded for {pair[:-4]} @{diff}% above 24hr average'
                        f'\n{pair[:-4]} suspended from trading for {self.strategy.suspension_time}s')

            # Unsuspend time
            if self.bucket.suspension_queue and time.time() - \
                    self.bucket.suspension_queue[0][
                        1] > self.strategy.suspension_time:
                self.bucket.unsuspend()
                print(
                    f'Suspension time reached for {self.bucket.suspension_queue[0][0][:-4]}'
                    f'\n{self.bucket.suspension_queue[0][0][:-4]} now unsuspended from trading')

        else:
            print('Bucket is empty, resetting suspension queue...')
            while self.bucket.suspension_queue:
                self.bucket.unsuspend()

    def _fc_trading_loop(self):
        bucket_delta = self.bucket.max_fall()

        target_price = self.get_price(bucket_delta[0])
        target_price_snapshot = self.bucket.average_snapshot[0][bucket_delta[0]][0]

        target_delta = 100 * (
                target_price - target_price_snapshot) / target_price_snapshot
        print(
            f'[Fiat-Crypto] delta = {-(target_delta)}% with {bucket_delta[0]} (latest price snapshot average)')

        # Realignment Mechanism
        if target_delta >= 0:
            print('Realignment mechanism triggered')
            self.bucket.take_snapshot()
            print('Price snapshot enqueued')

        if target_delta < -self.strategy.fc_delta_threshold:
            print(
                f'Fiat-Crypto delta threshold exceeded for {bucket_delta[0]}\n'
                f'Waiting for rebound...')

            start_time = time.time()
            t_delta = time.time() - start_time
            traded = False
            aborted = False

            while t_delta < self.strategy.rebound_wait_time:

                switched = self._strategize()

                bucket_delta_new = self.bucket.max_fall()
                target_price_snapshot = self.bucket.average_snapshot[0][
                    bucket_delta_new[0]][0]
                self.bucket.prices = self.bucket.get_prices()

                t_delta = time.time() - start_time
                new_price = self.get_price(bucket_delta_new[0])
                new_target_delta = (new_price - target_price_snapshot) / target_price_snapshot * 100

                rebound_ratio = (target_delta - new_target_delta) / target_delta

                print(
                    f'    rebound_ratio = {rebound_ratio} for {bucket_delta_new[0]} '
                    f'    delta = {new_target_delta}%'
                    f'    @t_delta = {t_delta}s')

                if switched and not (new_target_delta < -self.strategy.fc_delta_threshold):
                    print(
                        f'Delta threshold is no longer exceeded for the current strategy, aborting trading loop...')
                    aborted = True
                    break

                if rebound_ratio > self.strategy.fc_rebound_ratio:
                    print(
                        f'Rebound threshold exceeded for {bucket_delta_new[0]}\n'
                        f'Confirming...')

                    if self.confirm(self._fc_confirmation_logic, target_delta,
                                    self.strategy.buy_confirmation_repetition, self.strategy.buy_confirmation_time):

                        print('Trading...')

                        bucket_delta_new = self.bucket.max_fall()

                        self.buy(bucket_delta_new[0])
                        self.last_trade_time = time.time()
                        self.current_holding = bucket_delta_new[0]
                        self.bucket.take_snapshot()
                        print('Price snapshot enqueued')
                        self.profit_snapshot = self.current_profit()
                        print('Profit snapshot taken')
                        traded = True
                        break

                if rebound_ratio < 0:
                    target_delta = new_target_delta

            if (not aborted) and (not traded):
                bucket_delta_new = self.bucket.max_fall()

                print(
                    f'    Waiting time exceeded for {bucket_delta_new[0]}\n'
                    f'    Trading...')

                self.buy(bucket_delta_new[0])
                self.last_trade_time = time.time()
                self.bucket.take_snapshot()
                print('Price snapshot enqueued')
                self.profit_snapshot = self.current_profit()
                print('Profit snapshot taken')

    def _fc_confirmation_logic(self, target_delta):

        bucket_delta_new = self.bucket.max_fall()
        target_price_snapshot = self.bucket.average_snapshot[0][
            bucket_delta_new[0]][0]

        new_price = self.get_price(bucket_delta_new[0])
        new_target_delta = (new_price - target_price_snapshot) / target_price_snapshot * 100

        rebound_ratio = (target_delta - new_target_delta) / target_delta

        return rebound_ratio > self.strategy.fc_rebound_ratio

    def _cf_trading_loop(self):
        holding_price = self.bucket.prices[0][self.current_holding][0]
        snapshot_price = self.bucket.average_snapshot[0][self.current_holding][0]

        price_delta = 100 * (holding_price - snapshot_price) / snapshot_price
        print(f'[Crypto-Fiat] delta = {price_delta}% with USDT (latest price '
              f'snapshot average)')

        if price_delta > self.strategy.cf_delta_threshold:

            print(
                f'Crypto-Fiat delta threshold exceeded for USDT\n'
                f'Waiting for rebound...')

            start_time = time.time()
            t_delta = time.time() - start_time
            traded = False

            while t_delta < self.strategy.rebound_wait_time:

                t_delta = time.time() - start_time

                switched = self._strategize()
                self.bucket.prices = self.bucket.get_prices()

                new_price = self.get_price(self.current_holding)
                new_price_delta = (
                                          new_price - snapshot_price) / snapshot_price * 100

                rebound_ratio = (price_delta - new_price_delta) / price_delta

                print(
                    f'    rebound_ratio = {rebound_ratio} '
                    f'    new_price_delta = {new_price_delta}%'
                    f'    @t_delta = {t_delta}s')

                if switched and not (price_delta > self.strategy.cf_delta_threshold):
                    print(
                        f'Delta threshold is no longer exceeded for the current strategy, aborting trading loop...')
                    aborted = True
                    break

                if rebound_ratio > self.strategy.cf_rebound_ratio:
                    print(
                        f'Rebound threshold exceeded for USDT\n'
                        f'Confirming...')

                    if self.confirm(self._cf_confirmation_logic, price_delta,
                                    self.strategy.sell_confirmation_repetition, self.strategy.buy_confirmation_time):

                        print('Trading...')

                        self.sell(self.current_holding)
                        self.last_trade_time = time.time()
                        self.current_holding = 'USDT'
                        self.bucket.take_snapshot()
                        print('Price snapshot enqueued')
                        self.profit_snapshot = self.current_profit()
                        print('Profit snapshot taken')
                        traded = True
                        self.priming = False
                        break

                if rebound_ratio < 0:
                    price_delta = new_price_delta

                traded = self._profit_retention()
                if traded:
                    break

            if not traded:
                bucket_delta_new = self.bucket.max_fall()

                print(
                    f'    Waiting time exceeded\n'
                    f'    Trading...')

                self.sell(bucket_delta_new[0])
                self.last_trade_time = time.time()
                self.bucket.take_snapshot()
                print('Price snapshot enqueued')
                self.profit_snapshot = self.current_profit()
                print('Profit snapshot taken')
                self.priming = False

            self.profit_delta = None

    def _cf_confirmation_logic(self, price_delta):

        snapshot_price = self.bucket.average_snapshot[0][self.current_holding][0]

        new_price = self.get_price(self.current_holding)
        new_price_delta = (new_price - snapshot_price) / snapshot_price * 100
        rebound_ratio = (price_delta - new_price_delta) / price_delta

        return rebound_ratio > self.strategy.cf_rebound_ratio



    def _snapshot_refresh(self):
        if time.time() - self.bucket.average_snapshot[1] > self.strategy.snapshot_refresh_rate:
            self.bucket.take_snapshot()
            print(
                f'Snapshot refresh time of {self.strategy.snapshot_refresh_rate}s has elapsed since last saved snapshot, new price snapshot enqueued')
            self.profit_snapshot = self.current_profit()
            print('Profit snapshot taken')

    def _profit_retention(self) -> bool:
        triggered = False

        if self.current_holding != 'USDT':
            if self.profit_delta is None:
                self.profit_delta = self.current_profit() - self.profit_snapshot
            else:
                current_profit_delta = self.current_profit() - self.profit_snapshot
                if current_profit_delta > self.profit_delta:
                    self.profit_delta = current_profit_delta

                activation_positive = \
                    self.strategy.profit_retention_activation_positive / 100 * self.current_balance()

                activation_negative = \
                    self.strategy.profit_retention_activation_negative / 100 * self.current_balance()

                primed = current_profit_delta > activation_positive
                if self.priming == False and primed == True:
                    self.priming = True

                if current_profit_delta > 0:
                    trigger = (self.priming
                               and (current_profit_delta - self.profit_delta) / self.profit_delta < -self.strategy.cf_rebound_ratio)
                else:
                    trigger = ((abs(current_profit_delta) > activation_negative))

                if self.priming:
                    print('Positive profit retention mechanism has been primed')

                if trigger:
                    print('Profit retention mechanism triggered\n'
                          'Confirming...')
                    if self.confirm(self._profit_retention_confirmation_logic, None, self.strategy.sell_confirmation_repetition, self.strategy.sell_confirmation_time):
                        print('Trading...')
                        triggered = True

                        self.sell(self.current_holding)
                        self.last_trade_time = time.time()
                        self.current_holding = 'USDT'
                        self.bucket.take_snapshot()
                        print('Price snapshot enqueued')
                        self.profit_snapshot = self.current_profit()
                        print('Profit snapshot taken')
                        self.priming = False

                        self.profit_delta = None

        return triggered

    def _profit_retention_confirmation_logic(self, parameter):
        activation_negative = \
            self.strategy.profit_retention_activation_negative / 100 * self.current_balance()

        current_profit_delta = self.current_profit() - self.profit_snapshot
        if current_profit_delta > self.profit_delta:
            self.profit_delta = current_profit_delta

        if current_profit_delta > 0:
            trigger = (self.priming
                       and (current_profit_delta - self.profit_delta) / self.profit_delta < -self.strategy.cf_rebound_ratio)
        else:
            trigger = ((abs(current_profit_delta) > activation_negative))

        return trigger

    def confirm(self, logic, parameter, repetition, delay):
        self.bucket.prices = self.bucket.get_prices()
        prices = self.bucket.prices

        for i in range(repetition):
            if logic(parameter):
                print(f'Confirmation {i} successful')
                self.bucket.prices = self.bucket.get_prices()
                while self.bucket.prices[1] - prices[1] < delay:
                    self.bucket.prices = self.bucket.get_prices()
            else:
                print(f'Confirmation {i} failed')
                return False
        return True

    def _exit(self) -> bool:
        return False

    # Interfacing Methods
    ############################################################################
    def get_balance(self) -> float:
        return float(
            client.get_asset_balance(asset=self.current_holding)['free'])

    def sell(self, coin: str):
        balance = float(client.get_asset_balance(asset=coin)['free'])

        tick = None

        for filt in client.get_symbol_info(coin + 'USDT')['filters']:
            if filt['filterType'] == 'LOT_SIZE':
                tick = filt['stepSize'].find('1') - 2
                break

        order_quantity = math.floor(balance * 10 ** tick) / float(10 ** tick)
        order = client.order_market_sell(
            symbol=coin + 'USDT',
            quantity=order_quantity)

        while order['status'] != 'FILLED':
            print('    Pending order fulfillment...')
            time.sleep(0.5)

        print('    Order successful')

    def current_profit(self) -> float:
        balance = float(
            client.get_asset_balance(asset=self.current_holding)['free'])
        if self.current_holding != 'USDT':
            price = self.get_price(self.current_holding)
            return float(price) * balance - self.initial_value
        else:
            return balance - self.initial_value

    def current_balance(self) -> float:
        balance = float(
            client.get_asset_balance(asset=self.current_holding)['free'])
        if self.current_holding != 'USDT':
            price = self.get_price(self.current_holding)
            return float(price) * balance
        else:
            return balance

    def buy(self, coin: str):
        try:

            balance = float(client.get_asset_balance(asset='USDT')['free'])

            tick = None

            for filt in client.get_symbol_info(coin + 'USDT')['filters']:
                if filt['filterType'] == 'LOT_SIZE':
                    tick = filt['stepSize'].find('1') - 2
                    break

            price = float(
                client.get_symbol_ticker(symbol=coin + 'USDT')['price'])
            target = balance / price
            order_quantity = math.floor(target * 10 ** tick) / float(10 ** tick)

            order = client.order_market_buy(
                symbol=coin + 'USDT',
                quantity=order_quantity)

            while order['status'] != 'FILLED':
                print('    Pending order fulfillment...')
                time.sleep(0.5)

            print('    Order successful')

        except:
            print('    Exception detected, re-attemtpting order')
            self.buy(coin)
