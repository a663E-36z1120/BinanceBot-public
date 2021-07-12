import time

from bucket import Bucket
from strategy import Strategy_Baseline
import api
from bot import Bot

from strategies_avg_baselines import *
from strategies_24hr_multipliers import *
from strategies_latest_multipliers import *



STRATEGY_BASELINE = [bear_minus, bear, bear_plus, bull_minus, bull, bull_plus, bull_plus_plus]
STRATEGY_MULITIPLIER_24HR = [m1_bear_minus, m1_bear, m1_bear_plus, m1_bull_minus, m1_bull, m1_bull_plus]
STRATEGY_MULITIPLIER_LATEST = [m2_bear_minus, m2_bear, m2_bear_plus, m2_bull_minus, m2_bull, m2_bull_plus]
STRATEGY_CONFIGURATION = {'BASELINE': STRATEGY_BASELINE, '24HR': STRATEGY_MULITIPLIER_24HR, 'LATEST': STRATEGY_MULITIPLIER_LATEST}

# Bucket Configuration
################################################################################
BUCKET = Bucket(
                ['COMPUSDT', 'AAVEUSDT', 'ADAUSDT', 'XLMUSDT', 'EOSUSDT',
                 'XMRUSDT', 'UNIUSDT', 'CRVUSDT', 'LINKUSDT', 'SOLUSDT',
                 'XRPUSDT', 'MANAUSDT', 'ENJUSDT', 'LUNAUSDT', 'ETHUSDT',
                 'BTCUSDT', 'RENUSDT', 'YFIUSDT', 'DOTUSDT', 'BATUSDT',
                 'GRTUSDT', 'HBARUSDT', 'ATOMUSDT', 'FILUSDT',
                 'BNBUSDT', 'LTCUSDT'],
                SNAPSHOT_QUEUE_SIZE)
################################################################################

bot = Bot(STRATEGY_CONFIGURATION, BUCKET, 'USDT')
bot.run()
