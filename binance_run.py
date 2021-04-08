#!/usr/bin/env python

from binance_api import Binance
from pprint import pprint


bot = Binance(
    API_KEY='',
    API_SECRET=''
)

account=bot.futuresAccount()

print(f"SYM   Amt   entryPrice Margin     PNL       ")
for position in account['positions']:
    if float(position['positionAmt']) != 0.0:
        #pprint(position)
        print(f"{position['symbol'].replace('USDT',''):5} {position['positionAmt']:5} {position['entryPrice']:10} {position['positionInitialMargin']:10} {position['unrealizedProfit']}")



margin_ratio = float(account['totalMaintMargin']) / float(account['totalMarginBalance']) * 100
print("--------------------")
print(f"margin_ratio = {margin_ratio:0.2f}%")


