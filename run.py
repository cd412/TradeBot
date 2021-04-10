#!/usr/bin/env python

from binance_api import Binance
from tcommas_api import API3Commas
from pprint import pprint
import argparse
import sys
import time
import run_config
from datetime import datetime
from time import gmtime, strftime
import signal

#----------------------------------
'''
Usage:-

- Run main program:
time python3 run.py --show_all --beep --colors --auto --keep_running --stop_at 2 --bot_start_bursts 1 --pair_allowance 375

- On a seperate machine, run safe mode in case main one gets killed so this one can stop all bots if things go wrong:
time python3 run.py --colors --auto --pair_allowance 250 --keep_running --stop_at 2.5 --keep_running_timer 600 --safe



Notes:-

- Make sure 'Futures' is in the name of the account or use --binance_account_flag to specify part of name

- Add 'do not start' to the name of the bots you do not want to start automatically

- To set up SMS notification when Margin Ratio is critical add to config file
    ifttt_url = 'https://maker.ifttt.com/trigger/Event_Name/with/key/xyz'
    and set up IFTTT webhook to SMS link



ToDo:-

- Add notification through email or Google Home? (IFTTT is done for MR >= critical)

- Add script to create bots from existing one (not simple!!!)
    - ask to select account
    - ask for pair (to upper)
    - confirm before creation
    - create short and long

- Allow hardcoded Generate list of pairs sorted by how good they have been (or user input pairs)



XYZ:-


'''
#----------------------------------


parser = argparse.ArgumentParser()


parser.add_argument("--dry", help='Dry run, do not start/stop bots', action='store_true', default=None)
parser.add_argument("--auto", help='Auto Stop/Start bots based on Margin Ratio', action='store_true', default=None)
parser.add_argument("--stop_at", help='Stop bots when Margin Ratio >= value', type=float, default=2.5)
parser.add_argument("--start_at", help='Start bots when Margin Ratio <= value', type=float, default=1.5)
parser.add_argument("--bot_start_bursts", help='Number of bots to start each time', type=int, default=3)
parser.add_argument("--bots_per_position_ratio", help='Open a max number of bots ratio for each needed position', type=int, default=3)
parser.add_argument("--binance_account_flag", help='Part of binance account name identifier', default="Futures")

parser.add_argument("--show_all", help='Show all info', action='store_true', default=None)
parser.add_argument("--show_positions", help='Show current open positions', action='store_true', default=None)
parser.add_argument("--show_bots", help='Show bots details', action='store_true', default=None)
parser.add_argument("--show_deals", help='Show deals details', action='store_true', default=None)
parser.add_argument("--pair_allowance", help='How much money each pair is allowed, default is $500.00 (agg is $250)', type=float, default=500.0)

parser.add_argument("--beep", help='Beep when issues detected', action='store_true', default=None)
parser.add_argument("--colors", help='Add colors if system supports it', action='store_true', default=None)

#parser.add_argument("--pairs", help="A list of pairs ordered from best down, e.g. --pairs EOS ENJ AXS", nargs='+', default=None)
parser.add_argument("--keep_running", help='Loop forever (Ctrl+c to stop)', action='store_true', default=None)
parser.add_argument("--keep_running_timer", help='Time to sleep between runs in seconds (default 60)', type=int, default=60)
parser.add_argument("--safe", help='Run in safe mode (as a backup) with different values to make sure to stop (and not start) bots', action='store_true', default=None)
parser.add_argument("--debug", help='debug', action='store_true', default=None)

args = parser.parse_args()

if args.start_at >= args.stop_at:
    print("Error: start_at can't be more than or equal to stop_at")
    exit(1)

#----------------------------------

beep_time = 30
if args.colors:
    ENDC   = '\033[0m'
    RED    = '\033[91m'
    GREEN  = '\033[92m'
    YELLOW = '\033[93m'
else:
    ENDC   = ''
    RED    = ''
    GREEN  = ''
    YELLOW = ''


#----------------------------------

do_ifttt = True
try:
    _ = run_config.ifttt_url
except Exception:
    do_ifttt = False

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


def xstr(s):
    return '' if s is None else str(s)


def signal_handler(sig, frame):
    print('\nYou pressed Ctrl+C!')
    sys.exit(0)


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
    txt = f"Sym   Amt   entryPrice Margin     PNL       \n"
    for position in sorted(positions, key=lambda k: (k['symbol'])):
        if float(position['positionAmt']) != 0.0:
            txt += f"{position['symbol'].replace('USDT',''):5} {position['positionAmt']:5} {position['entryPrice']:10} {position['positionInitialMargin']:10} {position['unrealizedProfit']}\n"
    return txt[:-1]


def get_active_positions_count(positions, bots):
    count = 0
    for position in positions:
        if float(position['positionAmt']) != 0.0:
            for bot in bots:
                if position['symbol'].replace('USDT','') == ''.join(bot['pairs']).replace('USDT_','') and bot['strategy'] == 'long':
                    count += int((float(bot['base_order_volume'])//10) - 1)
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


def show_bots(bots, account_id):
    total = 0.0
    txt = f"\u2B9E {'Pair':<6} {'M':2} {'AD':<3} {'Total':<7} {'L/S':<5} {'Bot Name':<25}\n"
    #for bot in sorted(bots, key=lambda k: (str(k['is_enabled']), ''.join(k['pairs']), k['strategy'])):
    for bot in sorted(bots, key=lambda k: (''.join(k['pairs']), k['strategy'])):
        #if args.binance_account_flag in bot['account_name']:
        if account_id == bot['account_id']:
            notes = ""
            if 'do not start' in bot['name'].lower():
                notes += "\u26D4"
            if ''.join(bot['pairs']).replace('USDT_','') not in bot['name']:
                notes += " - Pair does not match bot name"
            total += float(bot['finished_deals_profit_usd'])
            up_down_flag = '\u2B9D' if bot['is_enabled'] else '\u2B9F'
            multiplier = int((float(bot['base_order_volume'])//10))
            txt += f"{up_down_flag} {''.join(bot['pairs']).replace('USDT_',''):<6} {multiplier}X {bot['active_deals_count']:<3} ${float(bot['finished_deals_profit_usd']):<6.2f} {bot['strategy']:<5} {bot['name']:<25} {notes}\n"
    txt += f"\u2B9C {'':13} ${total:<6.2f}\n"
    return txt[:-1]


def get_bot_pair_count(bots, account_id):
    a_count = 0
    count = 0
    for bot in bots:
        #if args.binance_account_flag in bot['account_name'] and bot['strategy'] == 'long':
        if account_id == bot['account_id'] and bot['strategy'] == 'long':
            count += 1
            if bot['is_enabled']:
                a_count += 1
    return count, a_count


def stop_all_bots(bots, account_id):
    for bot in sorted(bots, key=lambda k: (''.join(k['pairs']))):
        #if args.binance_account_flag in bot['account_name']:
        if account_id == bot['account_id']:
            if bot['is_enabled']:
                print(f"Stopping {bot['name']}... ", end='')
                if not args.dry:
                    xbot = get3CommasAPI().disableBot(BOT_ID=f"{bot['id']}")
                    if xbot['is_enabled']:
                        print(f"{RED}Error: Could not disable bot{ENDC}")
                    else:
                        print("Bot is now disabled")
                else:
                    print("")
            else:
                #print("Bot is already disabled")
                pass


def start_all_bots(bots, account_id):
    for bot in sorted(bots, key=lambda k: (''.join(k['pairs']))):
        #if args.binance_account_flag in bot['account_name']:
        if account_id == bot['account_id']:
            if bot['is_enabled'] or 'do not start' in bot['name']:
                pass # nothing to do
            else:
                print(f"Starting {bot['name']}... ", end='')
                if not args.dry:
                    xbot = get3CommasAPI().enableBot(BOT_ID=f"{bot['id']}")
                    if xbot['is_enabled']:
                        print("Bot is now enabled")
                    else:
                        print(f"{RED}Error: Could not enable bot{ENDC}")
                else:
                    print("")


# Maybe can combine both functions with default None
def start_bot_pair(bots, account_id, pair_to_start):
    for bot in sorted(bots, key=lambda k: (''.join(k['pairs']))):
        #if args.binance_account_flag in bot['account_name']:
        if account_id == bot['account_id']:
            if bot['is_enabled'] or 'do not start' in bot['name'] or not ''.join(bot['pairs']).endswith(pair_to_start):
                pass # nothing to do
            else:
                print(f"Starting {bot['name']}... ", end='')
                if not args.dry:
                    xbot = get3CommasAPI().enableBot(BOT_ID=f"{bot['id']}")
                    if xbot['is_enabled']:
                        print("Bot is now enabled")
                    else:
                        print(f"{RED}Error: Could not enable bot{ENDC}")
                else:
                    print("")


def stop_bot_pair(bots, account_id, pair_to_stop):
    for bot in sorted(bots, key=lambda k: (''.join(k['pairs']))):
        #if args.binance_account_flag in bot['account_name']:
        if account_id == bot['account_id']:
            if bot['is_enabled'] and ''.join(bot['pairs']).endswith(pair_to_stop):
                print(f"Stopping {bot['name']}... ", end='')
                if not args.dry:
                    xbot = get3CommasAPI().disableBot(BOT_ID=f"{bot['id']}")
                    if xbot['is_enabled']:
                        print(f"{RED}Error: Could not disable bot{ENDC}")
                    else:
                        print("Bot is now disabled")
                else:
                    print("")


# Get sorted list of stopped pairs by profit accounting for multiplier...
def get_top_stopped_pairs(bots, account_id):
    l = []
    for bot in sorted(bots, key=lambda k: (float(k['finished_deals_profit_usd'])/float(k['base_order_volume'])), reverse = True):
        #if args.binance_account_flag in bot['account_name'] and bot['strategy'] == "long" and not bot['is_enabled'] and 'do not start' not in bot['name']:
        if account_id == bot['account_id'] and bot['strategy'] == "long" and not bot['is_enabled'] and 'do not start' not in bot['name']:
            l.append(''.join(bot['pairs']).replace('USDT_',''))
    # intersect with args.pairs and keep order from args.pairs...
    return l


# Combine both with and without functions
# stopped bots with positions
def get_stopped_bots_with_positions(bots, account_id, positions):
    positions_l = []
    for position in sorted(positions, key=lambda k: (k['symbol'])):
        if float(position['positionAmt']) != 0.0:
            positions_l.append(position['symbol'].replace('USDT',''))

    bot_l = []
    for bot in sorted(bots, key=lambda k: (float(k['finished_deals_profit_usd'])/float(k['base_order_volume'])), reverse = True):
        if account_id == bot['account_id'] and bot['strategy'] == "long" and not bot['is_enabled'] and 'do not start' not in bot['name']:
            if ''.join(bot['pairs']).replace('USDT_','') in positions_l:
                bot_l.append(''.join(bot['pairs']).replace('USDT_',''))
    return bot_l


# sorted stopped bots without positions
def get_stopped_bots_without_positions(bots, account_id, positions):
    positions_l = []
    for position in sorted(positions, key=lambda k: (k['symbol'])):
        if float(position['positionAmt']) != 0.0:
            positions_l.append(position['symbol'].replace('USDT',''))

    bot_l = []
    for bot in sorted(bots, key=lambda k: (float(k['finished_deals_profit_usd'])/float(k['base_order_volume'])), reverse = True):
        if account_id == bot['account_id'] and bot['strategy'] == "long" and not bot['is_enabled'] and 'do not start' not in bot['name']:
            if ''.join(bot['pairs']).replace('USDT_','') not in positions_l:
                bot_l.append(''.join(bot['pairs']).replace('USDT_',''))
    return bot_l


# get count of stopped bots without active positions
def get_count_of_stopped_bots_without_positions(bots, account_id, positions):
    positions_l = []
    for position in sorted(positions, key=lambda k: (k['symbol'])):
        if float(position['positionAmt']) != 0.0:
            positions_l.append(position['symbol'].replace('USDT',''))

    count = 0
    for bot in bots:
        if account_id == bot['account_id'] and bot['strategy'] == "long" and not bot['is_enabled'] and 'do not start' not in bot['name']:
            if ''.join(bot['pairs']).replace('USDT_','') not in positions_l:
                count += 1
    return count


# get count of started bots without active positions
def get_count_of_started_bots_without_positions(bots, account_id, positions):
    positions_l = []
    for position in sorted(positions, key=lambda k: (k['symbol'])):
        if float(position['positionAmt']) != 0.0:
            positions_l.append(position['symbol'].replace('USDT',''))

    count = 0
    for bot in bots:
        if account_id == bot['account_id'] and bot['strategy'] == "long" and bot['is_enabled'] and 'do not start' not in bot['name']:
            if ''.join(bot['pairs']).replace('USDT_','') not in positions_l:
                count += 1
    return count


# get a list of started bots without active positions
def get_started_bots_without_positions(bots, account_id, positions):
    positions_l = []
    for position in sorted(positions, key=lambda k: (k['symbol'])):
        if float(position['positionAmt']) != 0.0:
            positions_l.append(position['symbol'].replace('USDT',''))

    bot_l = []
    for bot in bots:
        if account_id == bot['account_id'] and bot['strategy'] == "long" and bot['is_enabled'] and 'do not start' not in bot['name']:
            if ''.join(bot['pairs']).replace('USDT_','') not in positions_l:
                bot_l.append(''.join(bot['pairs']).replace('USDT_',''))
    return bot_l


# return first matching accountID
def getAccountID():
    accounts=get3CommasAPI().getAccounts()
    for account in accounts:
        if account['exchange_name'] == "Binance Futures USDT-M" and args.binance_account_flag in account['exchange_name']:
            txt = f"Using {account['name']} from exchange {account['exchange_name']}"
            return account['id'], txt




def show_deals(deals):

    # Get field from structure
    def gf(data, field):
        return data[field]

    def get_deal_cost_reserved(deal):
        current_active_safety_orders = gf(deal, 'current_active_safety_orders')
        completed_safety_orders_count = deal['completed_safety_orders_count']
        safety_order_volume = float(gf(deal, 'safety_order_volume'))
        martingale_volume_coefficient = float(gf(deal, 'martingale_volume_coefficient'))
        active_safety_orders_count = gf(deal, 'active_safety_orders_count')
        max_safety_orders = gf(deal, 'max_safety_orders')

        cost = 0
        max_cost = 0
        for i in range(completed_safety_orders_count, current_active_safety_orders + completed_safety_orders_count):
            cost += safety_order_volume * martingale_volume_coefficient ** i    
        for i in range(completed_safety_orders_count, max_safety_orders):
            max_cost += safety_order_volume * martingale_volume_coefficient ** i
        return cost, max_cost


    ts = datetime.utcnow()
    ts_txt = ts.strftime('%Y-%m-%dT%H:%M:%SZ')
    total_bought_volume = 0.0
    total_deals_cost_reserved = 0.0
    txt = ""

    active_deals = sorted(deals, key=lambda k: (float(k['bought_volume'])))#, reverse = True)
    txt = f"{'Pair':6} : {'SOs':9} : ${'Bought':8} : ${'Reserve':7} : {'%Profit':7}\n"

    for ad in active_deals:
        error_message = f"{RED}{xstr(ad['error_message'])}{xstr(ad['failed_message'])}{ENDC}"
        a_flag = ''
        if ad['current_active_safety_orders_count'] == 0:
            a_flag = f'{RED}***Zero Active***{ENDC}'
            if ad['completed_safety_orders_count'] != ad['max_safety_orders']:
                a_flag = f'{GREEN}***Closing/Opening***{ENDC}'
            else:
                zero_active = True

        actual_usd_profit = float(ad['actual_usd_profit'])
        created_at_ts = datetime.strptime(ad['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        created_at_ts_diff = ts - created_at_ts
        reserved_cost, max_reserved_cost = get_deal_cost_reserved(ad)

        txt += f"{ad['pair'].replace('USDT_',''):6} : c{ad['completed_safety_orders_count']} a{ad['current_active_safety_orders_count']} m{ad['max_safety_orders']} : ${float(ad['bought_volume']):8.2f} : ${reserved_cost:7.2f} : {ad['actual_profit_percentage']:6}% : ({created_at_ts_diff.days}d {int((created_at_ts_diff.total_seconds()/3600)%24)}h {int(((created_at_ts_diff.total_seconds()/3600) - int(created_at_ts_diff.total_seconds()/3600))*60)}m) {a_flag}{error_message}\n"

        total_bought_volume += float(ad['bought_volume'])
        total_deals_cost_reserved += reserved_cost
    txt += f"{'':18} : ${total_bought_volume:8.2f} : ${total_deals_cost_reserved:7.2f}"
    return txt

#----------------------------------
#----------------------------------
#----------------------------------
def run_account(account_id):

    account=getBinanceAPI().futuresAccount()

    margin_ratio = get_margin_ratio(account)

    if args.auto or args.show_bots or args.show_all:
        chunks = 100
        count = 0
        bots = []
        while True:
            tbots=get3CommasAPI().getBots(OPTIONS=f"?limit={chunks}&offset={chunks*count}")
            count += 1
            if len(tbots) > 0:
                bots.extend(tbots)
            else:
                break

    if args.show_bots or args.show_all:
        print(show_bots(bots, account_id))
        print("--------------------")

    if args.show_positions or args.show_all:
        print(show_positions(account['positions']))
        print("--------------------")

    if args.show_deals or args.show_all:
        try:
            deals=get3CommasAPI().getDeals(OPTIONS=f"?account_id={account_id}&scope=active&limit=100")
            print(show_deals(deals))
        except Exception as e:
            print(e)
            pass
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
            stop_all_bots(bots, account_id)
            if do_ifttt:
                import urllib.request
                ifttt_contents = urllib.request.urlopen(run_config.ifttt_url).read()
                print(ifttt_contents)
        else:
            if margin_ratio <= args.start_at:
                #print(f"{GREEN}Low Margin Ratio, starting bots...{ENDC}")

                top_stopped_pairs = get_top_stopped_pairs(bots, account_id)
                totalMarginBalance = get_totalMarginBalance(account)
                totalMaintMargin = get_totalMaintMargin(account)
                max_bot_pairs = get_max_bot_pairs(totalMarginBalance)
                active_positions_count = get_active_positions_count(account['positions'], bots)
                total_bot_pair_count, active_bot_pair_count = get_bot_pair_count(bots, account_id)

                print(f"totalMarginBalance = ${totalMarginBalance:<.2f} (${totalMaintMargin:<.2f})")
                print(f"Bots Active/Total: {active_bot_pair_count}/{total_bot_pair_count}")
                stopped_bots_count = total_bot_pair_count - active_bot_pair_count
                #print(f"stopped_bots_count = {stopped_bots_count}")
                position_delta_factor = (margin_ratio/args.stop_at - margin_ratio/args.start_at) * max_bot_pairs                
                #position_delta_factor = (margin_ratio/args.stop_at) * max_bot_pairs                
                #print(f"position_delta_factor = {position_delta_factor }")
                position_delta_factor = round(position_delta_factor) if position_delta_factor > 0 else 0
                #print(f"position_delta_factor = {position_delta_factor }")

                bots_pairs_to_start = round(max_bot_pairs - position_delta_factor - active_positions_count)
                print(f"Positions delta ({bots_pairs_to_start}) = target ({round(max_bot_pairs)}) - MR factor ({position_delta_factor}) - running ({active_positions_count})")
                #print(f"top_stopped_pairs = {top_stopped_pairs}")

                if bots_pairs_to_start > 0 and not args.safe: # need more positions
                    if len(top_stopped_pairs) > 0:
                        stopped_bots_with_positions = get_stopped_bots_with_positions(bots, account_id, account['positions'])
                        if len(stopped_bots_with_positions) > 0:
                            print(f"Starting {len(stopped_bots_with_positions)} stopped bots with active positions...")
                            for bot_to_start in stopped_bots_with_positions:
                                print(f"Starting {bot_to_start} bot pairs...")
                                start_bot_pair(bots, account_id, bot_to_start)
                        else: # no stopped bots with positions to start, start from ones without active positions
                            max_bots_running = bots_pairs_to_start * args.bots_per_position_ratio
                            print (f"Need to start a max of {max_bots_running} stopped bot pairs...")
                            
                            count_of_started_bots_without_positions = get_count_of_started_bots_without_positions(bots, account_id, account['positions'])
                            max_bots_running = max_bots_running - count_of_started_bots_without_positions
                            #print(f"max_bots_running = {max_bots_running}")
                            
                            stopped_bots_without_positions = get_stopped_bots_without_positions(bots, account_id, account['positions'])
                            actual_bots_to_start = min(max_bots_running, args.bot_start_bursts, len(stopped_bots_without_positions), max_bots_running)
                            actual_bots_to_start = 0 if actual_bots_to_start <= 0 else actual_bots_to_start # Make sure it's not a negative number
                            
                            print (f"Incrementally starting {actual_bots_to_start} stopped bots without positions...")
                            burst_pairs_to_start = stopped_bots_without_positions[:actual_bots_to_start] # Assume list is sorted
                            for bot_to_start in burst_pairs_to_start:
                                print(f"Starting {bot_to_start} bot pairs...")
                                start_bot_pair(bots, account_id, bot_to_start)

                        '''
                        max_bots_running = bots_pairs_to_start * args.bots_per_position_ratio
                        print (f"Need to start a max of {max_bots_running} stopped bot pairs...")
                        
                        count_of_stopped_bots_without_positions = get_count_of_stopped_bots_without_positions(bots, account_id, account['positions'])
                        print(f"Stopped bots without positions = {count_of_stopped_bots_without_positions}")
                        
                        count_of_stopped_bots_with_positions = stopped_bots_count - count_of_stopped_bots_without_positions
                        #print(f"count_of_stopped_bots_with_positions = {count_of_stopped_bots_with_positions}")

                        actual_bots_to_start = min(max_bots_running, args.bot_start_bursts, count_of_stopped_bots_without_positions, count_of_stopped_bots_with_positions)
                        
                        #delta_bots_running = max_bots_running - active_bot_pair_count
                        #burst_start = args.bot_start_bursts if args.bot_start_bursts <= bots_pairs_to_start else bots_pairs_to_start
                        #actual_bots_to_start = min(delta_bots_running, burst_start)
                        
                        actual_bots_to_start = 0 if actual_bots_to_start <= 0 else actual_bots_to_start # Make sure it's not a negative number
                        print (f"Incrementally starting up to {actual_bots_to_start} this time...")
                        
- if bots_pairs_to_start > 0
    - if stopped bots with positions > 0
        - start them all
    - else
        - start count min(burst, bots_pairs_to_start * args.bots_per_position_ratio)
        - start sorted stopped bots without positions

                        stopped_bots_without_positions = get_stopped_bots_without_positions(bots, account_id, account['positions'])
                        print("stopped_bots_without_positions:")
                        pprint(stopped_bots_without_positions)
                        print("stopped_bots_with_positions:")
                        pprint(stopped_bots_with_positions)
                        
                        burst_pairs_to_start = top_stopped_pairs[:actual_bots_to_start] # Assume list is sorted
                        for bot_to_start in burst_pairs_to_start:
                            print(f"Starting {bot_to_start} bot pairs...")
                            start_bot_pair(bots, account_id, bot_to_start)
                        '''
                    else:
                        print("No stopped bots to start...")
                elif bots_pairs_to_start < 0: # running too much positions
                    if args.safe:
                        print("Hight positions count, stopping all running bots...")
                        stop_all_bots(bots, account_id)
                    else:
                        started_bots_without_positions = get_started_bots_without_positions(bots, account_id, account['positions'])
                        print(f"Hight positions count, stopping {len(started_bots_without_positions)} bots without positions")
                        for bot_to_stop in started_bots_without_positions:
                            print(f"Stopping {bot_to_stop} bot pairs...")
                            stop_bot_pair(bots, account_id, bot_to_stop)
                else: # the right ammount of positions running
                    print("No change to positions count needed...")

    if args.beep and margin_ratio >= args.stop_at:
        beep(beep_time)

    if args.beep:
        beep(1)


#----------------------------------
#----------------------------------
#----------------------------------

signal.signal(signal.SIGINT, signal_handler)

account, account_txt = getAccountID()
print (account_txt)
print ("-------------------------------------------------------------")

if args.keep_running:
    while True:
        try:
            run_account(account)
        except Exception as e:
            print(e)
            pass

        ts_txt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(ts_txt)
        countdown(args.keep_running_timer)
else:
    run_account(account)


