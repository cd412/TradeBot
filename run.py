#!/usr/bin/env python

from binance_api import Binance
from tcommas_api import API3Commas
from pprint import pprint
import argparse
import sys
import time
import run_config


#----------------------------------
'''

e.g. time python3 run.py --show_all --beep --auto --pair_allowance 375 --keep_running --stop_at 2

Notes:-

- Make sure 'Futures' is in the name of the account
- Add 'do not start' to the name of the bots you do not want to start automatically



ToDo:-
- Add notification through email or Google Home?
- Add script to create bots
    - ask to select account
    - ask for pair (to upper)
    - confirm before creation
    - create short and long



- Consider multipliers when accounting for values
- Handle multiple accounts

- Generate list of pairs sorted by how good they have been (or user input pairs)
- Manually create a lot of bots for all pairs possible (do not start them)
- Calculate how many bot pairs you can have running (max bot pairs)
    - balance/?
- count active positions
- if active positions is under max bot pairs, start more bots

- start all bots at that stage?
- if we need to stop, should we only stop ones from bottom of pairs list and how many to stop?

- always check Margin Ratio before starting bots
- add flag to bot so it is not started automatically, e.g. bot name including 'do not start'


top best -> worst
pair1, pair2, ...., pairN (e.g. 30)


example/use case:-

***check every 1 minutes***

$5000/375 = 15 pairs potential target
m = 2.7
STOP all


15 pairs target positions
m 0.8
positions = 3
12 bellow target
START (top 10% rounded up - JM think of math) that are stopped


15 pairs target positions
m 1.1
positions = 18
3 above target
stop ALL bots



- margin >= stop limit
    - stop all bots
    - exit
- margin <= start limit
    - if not enough positions opened
        - do nothing OR stop bots
        - start targeted bots incrementally
    - else if more position opened than target
        - stop all bots


'''
#----------------------------------


parser = argparse.ArgumentParser()


parser.add_argument("--dry", help='Dry run, do not start/stop bots', action='store_true', default=None)
parser.add_argument("--auto", help='Auto Stop/Start bots based on Margin Ratio', action='store_true', default=None)
parser.add_argument("--stop_at", help='Stop bots when Margin Ratio >= value', type=float, default=2.5)
parser.add_argument("--start_at", help='Start bots when Margin Ratio <= value', type=float, default=1.5)
parser.add_argument("--bot_start_bursts", help='Number of bots to start each time', type=int, default=3)
parser.add_argument("--binance_account_flag", help='Part of binance account name identifier', default="Futures")

parser.add_argument("--show_all", help='Show all info', action='store_true', default=None)
parser.add_argument("--show_positions", help='Show current open positions', action='store_true', default=None)
parser.add_argument("--show_bots", help='Show bots details', action='store_true', default=None)
parser.add_argument("--pair_allowance", help='How much money each pair is allowed, default is $500.00 (agg is $250)', type=float, default=500.0)
parser.add_argument("--beep", help='Beep when issues detected', action='store_true', default=None)
#parser.add_argument("--pairs", help="A list of pairs ordered from best down, e.g. --pairs EOS ENJ AXS", nargs='+', default=None)
parser.add_argument("--keep_running", help='Loop forever (Ctrl+c to stop)', action='store_true', default=None)
parser.add_argument("--keep_running_timer", help='Time to sleep between runs in seconds (default 60)', action='store_true', default=60)
parser.add_argument("--debug", help='debug', action='store_true', default=None)

args = parser.parse_args()

if args.start_at >= args.stop_at:
    print("Error: start_at can't be more than or equal to stop_at")
    exit(1)

#----------------------------------

beep_time = 30

ENDC    = '\033[0m'
RED    = '\033[91m'
GREEN  = '\033[92m'
YELLOW = '\033[93m'


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


def countdown(t):
    while t:
        mins, secs = divmod(t, 60)
        timer = '{:02d}:{:02d}'.format(mins, secs)
        print(timer, end="\r")
        time.sleep(1)
        t -= 1

def beep(btime):
    for i in range(btime):
        sys.stdout.write('\r\a')
        sys.stdout.flush()
        time.sleep(0.5)


def show_positions(positions):
    txt = f"SYM   Amt   entryPrice Margin     PNL       \n"
    for position in sorted(positions, key=lambda k: (k['symbol'])):
        if float(position['positionAmt']) != 0.0:
            txt += f"{position['symbol'].replace('USDT',''):5} {position['positionAmt']:5} {position['entryPrice']:10} {position['positionInitialMargin']:10} {position['unrealizedProfit']}\n"
    return txt[:-1]


def get_active_positions_count(positions):
    count = 0
    for position in positions:
        if float(position['positionAmt']) != 0.0:
            count += 1
    return count


def get_margin_ratio(a_data):
    return float(a_data['totalMaintMargin']) / float(a_data['totalMarginBalance']) * 100


def get_totalMarginBalance(a_data):
    return float(a_data['totalMarginBalance'])


def get_totalMaintMargin(a_data):
    return float(a_data['totalMaintMargin'])


def get_max_bot_pairs(balance):
    return balance/args.pair_allowance


def show_bots(bots):
    total = 0.0
    txt = f"{'Enabled':<7} {'Pair':<10} {'Strategy':<5} {'Bot Name':<25} {'AD':<3} {'Total':<6}\n"
    for bot in sorted(bots, key=lambda k: (str(k['is_enabled']), ''.join(k['pairs']), k['strategy'])):
        if args.binance_account_flag in bot['account_name']:
            total += float(bot['finished_deals_profit_usd'])
            txt += f"{str(bot['is_enabled']):<7} {''.join(bot['pairs']):<10} {bot['strategy']:<8} {bot['name']:<25} {bot['active_deals_count']:<3} ${float(bot['finished_deals_profit_usd']):<6.2f}\n"
    txt += f"{'':57} ${total:<6.2f}\n"
    return txt[:-1]


def get_bot_pair_count(bots):
    a_count = 0
    count = 0
    for bot in bots:
        if args.binance_account_flag in bot['account_name'] and bot['strategy'] == 'long':
            count += 1
            if bot['is_enabled']:
                a_count += 1
    return count, a_count


def stop_all_bots(bots):
    for bot in sorted(bots, key=lambda k: (''.join(k['pairs']))):
        if args.binance_account_flag in bot['account_name']:
            if bot['is_enabled']:
                print(f"Stopping {bot['name']}...")
                if not args.dry:
                    xbot = get3CommasAPI().disableBot(BOT_ID=f"{bot['id']}")
                    if xbot['is_enabled']:
                        print(f"{RED}Error: Could not disable bot{ENDC}")
                    else:
                        print("Bot is now disabled")
            else:
                #print("Bot is already disabled")
                pass


def start_all_bots(bots):
    for bot in sorted(bots, key=lambda k: (''.join(k['pairs']))):
        if args.binance_account_flag in bot['account_name']:
            if bot['is_enabled'] or 'do not start' in bot['name']:
                pass # nothing to do
            else:
                print(f"Starting {bot['name']}...")
                if not args.dry:
                    xbot = get3CommasAPI().enableBot(BOT_ID=f"{bot['id']}")
                    if xbot['is_enabled']:
                        print("Bot is now enabled")
                    else:
                        print(f"{RED}Error: Could not enable bot{ENDC}")


# Maybe can combine both functions with default None
def start_bot_pair(bots, pair_to_start):
    for bot in sorted(bots, key=lambda k: (''.join(k['pairs']))):
        if args.binance_account_flag in bot['account_name']:
            if bot['is_enabled'] or 'do not start' in bot['name'] or not ''.join(bot['pairs']).endswith(pair_to_start):
                pass # nothing to do
            else:
                print(f"Starting {bot['name']}...")
                if not args.dry:
                    xbot = get3CommasAPI().enableBot(BOT_ID=f"{bot['id']}")
                    if xbot['is_enabled']:
                        print("Bot is now enabled")
                    else:
                        print(f"{RED}Error: Could not enable bot{ENDC}")


def get_top_stopped_pairs(bots):
    l = []
    for bot in sorted(bots, key=lambda k: (float(k['finished_deals_profit_usd'])), reverse = True):
        if args.binance_account_flag in bot['account_name'] and bot['strategy'] == "long" and not bot['is_enabled'] and 'do not start' not in bot['name']:
            l.append(''.join(bot['pairs']).replace('USDT_',''))
    # interset with args.pairs and keep order from args.pairs...
    return l



#----------------------------------
#----------------------------------
#----------------------------------
def run_main():
    account=getBinanceAPI().futuresAccount()

    margin_ratio = get_margin_ratio(account)

    if args.auto or args.show_bots or args.show_all:
        bots=get3CommasAPI().getBots()


    #account=get3CommasAPI().getAccounts()

    if args.show_bots or args.show_all:
        print(show_bots(bots))
        print("--------------------")

    if args.show_positions or args.show_all:
        print(show_positions(account['positions']))
        print("--------------------")

    color = YELLOW
    if margin_ratio >= args.stop_at:
        color = RED
    if margin_ratio <= args.start_at:
        color = GREEN
    print(f"{color}Margin Ratio = {margin_ratio:0.2f}%{ENDC}")
    print("--------------------")



    if args.auto:
        if margin_ratio >= args.stop_at:
            print(f"{RED}Hight margin_ratio, stopping bots...{ENDC}")
            stop_all_bots(bots)
        else:
            if margin_ratio <= args.start_at:
                #print(f"{GREEN}Low Margin Ratio, starting bots...{ENDC}")

                top_stopped_pairs = get_top_stopped_pairs(bots)
                totalMarginBalance = get_totalMarginBalance(account)
                totalMaintMargin = get_totalMaintMargin(account)
                max_bot_pairs = get_max_bot_pairs(totalMarginBalance)
                active_positions_count = get_active_positions_count(account['positions'])
                total_bot_pair_count, active_bot_pair_count = get_bot_pair_count(bots)
                bots_pairs_to_start = round(max_bot_pairs - active_positions_count)

                print(f"totalMarginBalance = ${totalMarginBalance:<.2f} (${totalMaintMargin:<.2f})")
                print(f"Bots Active/Total: {active_bot_pair_count}/{total_bot_pair_count}")
                print(f"Delta positions ({bots_pairs_to_start}) = target ({round(max_bot_pairs)}) - running ({active_positions_count})")
                #print(f"top_stopped_pairs = {top_stopped_pairs}")

                if bots_pairs_to_start > 0: # need more positions
                    if len(top_stopped_pairs) > 0:
                        print (f"Need to start {bots_pairs_to_start} bot pairs...")
                        burst_start = args.bot_start_bursts if args.bot_start_bursts <= bots_pairs_to_start else bots_pairs_to_start
                        print (f"Incrementally starting {burst_start} this time...")
                        burst_pairs_to_start = top_stopped_pairs[:burst_start] # Assume list is sorted
                        for bot_to_start in burst_pairs_to_start:
                            print(f"Starting {bot_to_start} bot pairs...")
                            start_bot_pair(bots, bot_to_start)
                    else:
                        print("No stopped bots to start...")
                elif bots_pairs_to_start < 0: # running too much positions
                    print("Hight positions count, stopping all running bots...")
                    stop_all_bots(bots)
                else: # the right ammount of positions running
                    print("No change to positions count needed...")

    if args.beep and margin_ratio >= args.stop_at:
        beep(beep_time)

    if args.beep:
        beep(1)


#----------------------------------
#----------------------------------
#----------------------------------

if args.keep_running:
    while True:
        try:
            run_main()
        except Exception as e:
            print(e)
            pass
        countdown(args.keep_running_timer)
else:
    run_main()


