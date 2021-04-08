#!/usr/bin/env python

from binance_api import Binance
from tcommas_api import API3Commas
from pprint import pprint
import run_config



#----------------------------------

def getBinanceAPI():
    api = Binance(
        API_KEY=run_config.Binance_API_KEY,
        API_SECRET=run_config.Binance_API_SECRET
    )
    return api

def get3CommasAPI():
    api = API3Commas(
        API_KEY=run_config.TCommas_API_KEY,
        API_SECRET=run_config.TCommas_API_SECRET
    )
    return api

def show_positions(positions):
    txt = f"SYM   Amt   entryPrice Margin     PNL       \n"
    for position in sorted(positions, key=lambda k: (k['symbol'])):
        if float(position['positionAmt']) != 0.0:
            #pprint(position)
            txt += f"{position['symbol'].replace('USDT',''):5} {position['positionAmt']:5} {position['entryPrice']:10} {position['positionInitialMargin']:10} {position['unrealizedProfit']}\n"
    return txt[:-1]

def get_margin_ratio(a_data):
    return float(a_data['totalMaintMargin']) / float(a_data['totalMarginBalance']) * 100

def show_bots(bots):
    txt = f"{'Enabled':<7} {'Pair':<10} {'Strategy':<5} {'Bot Name':<25} {'AD':<3} {'Total':<6}\n"
    for bot in sorted(bots, key=lambda k: (float(k['finished_deals_profit_usd']))):
        if 'Futures' in bot['account_name']:
            txt += f"{str(bot['is_enabled']):<7} {''.join(bot['pairs']):<10} {bot['strategy']:<8} {bot['name']:<25} {bot['active_deals_count']:<3} ${float(bot['finished_deals_profit_usd']):<6.2f}\n"
    return txt[:-1]

def stop_bots(bots):
    for bot in sorted(bots, key=lambda k: (''.join(k['pairs']))):
        if 'Futures' in bot['account_name']:
            if bot['is_enabled']:
                print(f"Stopping {bot['name']}...")
                xbot = api.disableBot(BOT_ID=bot['id'])
                if xbot['is_enabled']:
                    print("Error: Could not disable bot")
                else:
                    print("Bot is now disabled")
            else:
                print("Bot is already disabled")


def start_bots(bots):
    for bot in sorted(bots, key=lambda k: (''.join(k['pairs']))):
        if 'Futures' in bot['account_name']:
            if bot['is_enabled']:
                pass # nothing to do
            else:
                print(f"Starting {bot['name']}...")
                xbot = api.disableBot(BOT_ID=bot['id'])
                if xbot['is_enabled']:
                    print("Bot is now enabled")
                else:
                    print("Error: Could not enable bot")



#----------------------------------
#----------------------------------
#----------------------------------

account=getBinanceAPI().futuresAccount()
print(show_positions(account['positions']))
print("--------------------")


margin_ratio = get_margin_ratio(account)
print(f"margin_ratio = {margin_ratio:0.2f}%")
print("--------------------")


bots=get3CommasAPI().getBots()

if margin_ratio >= 2.5:
    print("Hight margin_ratio, stopping bots...")
    stop_bots(bots)

if margin_ratio <= 1.5:
    print("Low margin_ratio, starting bots...")
    start_bots(bots)

#account=get3CommasAPI().getAccounts()

print(show_bots(bots))
print("--------------------")




'''
xbot = api.disableBot(BOT_ID='3403747')
pprint(xbot)


xbot = api.enableBot(BOT_ID='3403747')
pprint(xbot)
'''









