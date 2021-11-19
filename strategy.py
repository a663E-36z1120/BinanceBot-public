from typing import Dict, Tuple


class Strategy:
    def __init__(self, baseline, multiplier_24hr, multiplier_latest, trend_inversion):
        # Identity Configuration
        self.name = {'BASELINE': baseline.name, '24HR': multiplier_24hr.name,
                     'LATEST': multiplier_latest.name, 'INVERSION': trend_inversion.name}

        self.interval = baseline.interval

        self.snapshot_refresh_rate = (baseline.snapshot_refresh_rate *
                                      multiplier_24hr.snapshot_refresh_rate *
                                      multiplier_latest.snapshot_refresh_rate *
                                      trend_inversion.snapshot_refresh_rate)

        self.latest_snapshot_count = (baseline.latest_snapshot_count *
                                      multiplier_24hr.latest_snapshot_count *
                                      multiplier_latest.latest_snapshot_count *
                                      trend_inversion.latest_snapshot_count)

        # Trading
        self.cf_delta_threshold = (baseline.cf_delta_threshold *
                                   multiplier_24hr.cf_delta_threshold *
                                   multiplier_latest.cf_delta_threshold *
                                   trend_inversion.cf_delta_threshold)
        self.cf_rebound_ratio = (baseline.cf_rebound_ratio *
                                 multiplier_24hr.cf_rebound_ratio *
                                 multiplier_latest.cf_rebound_ratio *
                                 trend_inversion.cf_rebound_ratio)

        self.fc_delta_threshold = (baseline.fc_delta_threshold *
                                   multiplier_24hr.fc_delta_threshold *
                                   multiplier_latest.fc_delta_threshold *
                                   trend_inversion.fc_delta_threshold)
        self.fc_rebound_ratio = (baseline.fc_rebound_ratio *
                                 multiplier_24hr.fc_rebound_ratio *
                                 multiplier_latest.fc_rebound_ratio *
                                 trend_inversion.fc_rebound_ratio)

        self.rebound_wait_time = (baseline.rebound_wait_time *
                                  multiplier_24hr.rebound_wait_time *
                                  multiplier_latest.rebound_wait_time *
                                  trend_inversion.rebound_wait_time)

        self.trading_cooldown_time = (baseline.trading_cooldown_time *
                                      multiplier_24hr.trading_cooldown_time *
                                      multiplier_latest.trading_cooldown_time *
                                      trend_inversion.trading_cooldown_time)

        # Pruning
        self.suspension_threshold = (baseline.suspension_threshold *
                                     multiplier_24hr.suspension_threshold *
                                     multiplier_latest.suspension_threshold *
                                     trend_inversion.suspension_threshold)
        self.suspension_time = (baseline.suspension_time *
                                multiplier_24hr.suspension_time *
                                multiplier_latest.suspension_time *
                                trend_inversion.suspension_time)

        # Profit retention
        self.profit_retention_activation_positive = \
            (baseline.profit_retention_activation_positive *
             multiplier_24hr.profit_retention_activation_positive *
             multiplier_latest.profit_retention_activation_positive *
             trend_inversion.profit_retention_activation_positive)
        self.profit_retention_activation_negative = \
            (baseline.profit_retention_activation_negative *
             multiplier_24hr.profit_retention_activation_negative *
             multiplier_latest.profit_retention_activation_negative *
             trend_inversion.profit_retention_activation_negative)

        # Delayed confirmation
        self.sell_confirmation_repetition = round(
            baseline.sell_confirmation_repetition *
            multiplier_24hr.sell_confirmation_repetition *
            multiplier_latest.sell_confirmation_repetition *
            trend_inversion.sell_confirmation_repetition)
        self.sell_confirmation_time = (baseline.sell_confirmation_time *
                                       multiplier_24hr.sell_confirmation_time *
                                       multiplier_latest.sell_confirmation_time *
                                       trend_inversion.sell_confirmation_time)

        self.buy_confirmation_repetition = round(
            baseline.buy_confirmation_repetition *
            multiplier_24hr.buy_confirmation_repetition *
            multiplier_latest.buy_confirmation_repetition *
            trend_inversion.buy_confirmation_repetition)
        self.buy_confirmation_time = (baseline.buy_confirmation_time *
                                      multiplier_24hr.buy_confirmation_time *
                                      multiplier_latest.buy_confirmation_time *
                                      trend_inversion.buy_confirmation_time)


class Strategy_Baseline:
    def __init__(self,
                 identity: Dict,
                 snapshot_refresh_rate: float,
                 latest_snapshot_count: int,
                 trading_configuration: Dict,
                 pruning_configuration: Dict,
                 profit_retention_configuration: Tuple,
                 corfirmation_configuration: Dict):
        # Identity Configuration
        self.name = identity['NAME']
        self.interval = identity['INTERVAL']

        self.snapshot_refresh_rate = snapshot_refresh_rate
        self.latest_snapshot_count = latest_snapshot_count

        # Trading
        self.cf_delta_threshold = trading_configuration['CF'][0]
        self.cf_rebound_ratio = trading_configuration['CF'][1]

        self.fc_delta_threshold = trading_configuration['FC'][0]
        self.fc_rebound_ratio = trading_configuration['FC'][1]

        self.rebound_wait_time = trading_configuration['REBOUND_WAIT_TIME']
        self.trading_cooldown_time = trading_configuration['TRADING_COOLDOWN_TIME']

        # Pruning
        self.suspension_threshold = pruning_configuration['SNAPSHOT'][0]
        self.suspension_time = pruning_configuration['SNAPSHOT'][1]

        # Profit retention
        self.profit_retention_activation_positive = \
            profit_retention_configuration[0]
        self.profit_retention_activation_negative = \
            profit_retention_configuration[1]

        # Delayed confirmation
        self.sell_confirmation_repetition = corfirmation_configuration['SELL'][
            0]
        self.sell_confirmation_time = corfirmation_configuration['SELL'][1]

        self.buy_confirmation_repetition = corfirmation_configuration['BUY'][0]
        self.buy_confirmation_time = corfirmation_configuration['BUY'][1]


class Strategy_Multiplier(Strategy_Baseline):
    pass
