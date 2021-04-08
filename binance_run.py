#!/usr/bin/env python

from binance_api import Binance
from pprint import pprint
import binance_config



#----------------------------------

def show_positions(positions):
    txt = f"SYM   Amt   entryPrice Margin     PNL       \n"
    for position in sorted(positions, key=lambda k: (k['symbol'])):
        if float(position['positionAmt']) != 0.0:
            #pprint(position)
            txt += f"{position['symbol'].replace('USDT',''):5} {position['positionAmt']:5} {position['entryPrice']:10} {position['positionInitialMargin']:10} {position['unrealizedProfit']}\n"
    return txt[:-1]

def get_margin_ratio(a_data):
    return float(a_data['totalMaintMargin']) / float(a_data['totalMarginBalance']) * 100


#----------------------------------
#----------------------------------

bot = Binance(
    API_KEY=binance_config.Binance_API_KEY,
    API_SECRET=binance_config.Binance_API_SECRET
)

account=bot.futuresAccount()

#----------------------------------

print(show_positions(account['positions']))
margin_ratio = get_margin_ratio(account)
print("--------------------")
print(f"margin_ratio = {margin_ratio:0.2f}%")


