#!/usr/bin/env python

from binance_api import Binance
from tcommas_api import API3Commas
from pprint import pprint
import argparse
import sys
import time
import run_config


#----------------------------------


parser = argparse.ArgumentParser()


parser.add_argument("--auto", help='Auto Stop/Start bots based on Margin Ratio', action='store_true', default=None)
parser.add_argument("--stop_at", help='Stop bots when Margin Ratio >= value', type=float, default=2.5)
parser.add_argument("--start_at", help='Start bots when Margin Ratio <= value', type=float, default=1.5)
parser.add_argument("--show_positions", help='Show current open positions', action='store_true', default=None)
parser.add_argument("--show_bots", help='Show bots details', action='store_true', default=None)
parser.add_argument("--beep", help='Beep when issues detected', action='store_true', default=None)

args = parser.parse_args()

#----------------------------------

beep_time = 30

END   = '\033[0m'
RED   = '\033[91m'
GREEN = '\033[92m'


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

def beep(btime):
    for i in range(btime):
        sys.stdout.write('\r\a')
        sys.stdout.flush()
        time.sleep(0.5)

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
                    print(f"{RED}Error: Could not disable bot{ENDC}")
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
                    print(f"{RED}Error: Could not enable bot{ENDC}")



#----------------------------------
#----------------------------------
#----------------------------------

account=getBinanceAPI().futuresAccount()

if args.show_positions:
    print(show_positions(account['positions']))
    print("--------------------")


margin_ratio = get_margin_ratio(account)
print(f"Margin Ratio = {margin_ratio:0.2f}%")
print("--------------------")


if args.auto or args.show_bots:
    bots=get3CommasAPI().getBots()

if args.auto:
    if margin_ratio >= args.stop_at:
        print(f"{RED}Hight margin_ratio, stopping bots...{ENDC}")
        stop_bots(bots)

    if margin_ratio <= args.start_at:
        #print(f"{GREEN}Low margin_ratio, starting bots...{ENDC}")
        start_bots(bots)

#account=get3CommasAPI().getAccounts()

if args.show_bots:
    print(show_bots(bots))
    print("--------------------")


if args.beep and margin_ratio >= args.stop_at:
    beep(beep_time)



beep(1)


