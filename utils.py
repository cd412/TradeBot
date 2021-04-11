from binance_api import Binance
from tcommas_api import API3Commas
from pprint import pprint
import sys
import time
import run_config
from datetime import datetime
from time import gmtime, strftime


#----------------------------------

beep_time = 30

ENDC   = ''
RED    = ''
GREEN  = ''
YELLOW = ''


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


def get_max_bot_pairs(balance, pair_allowance):
    return balance/pair_allowance


def show_bots(bots, account_id):
    total = 0.0
    txt = f"\u2B9E {'Pair':<6} {'M':2} {'AD':<3} {'Total':<7} {'L/S':<5} {'Bot Name':<25}\n"
    #for bot in sorted(bots, key=lambda k: (str(k['is_enabled']), ''.join(k['pairs']), k['strategy'])):
    for bot in sorted(bots, key=lambda k: (''.join(k['pairs']), k['strategy'])):
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


def list_bot_pairs(bots, account_id):
    txt = ""
    for bot in sorted(bots, key=lambda k: (''.join(k['pairs']), k['strategy'])):
        if account_id == bot['account_id'] and bot['strategy'] == 'long':
            txt += f"{''.join(bot['pairs']).replace('USDT_','')}\n"
    return txt[:-1]


def get_bot_pair_count(bots, account_id):
    a_count = 0
    count = 0
    for bot in bots:
        if account_id == bot['account_id'] and bot['strategy'] == 'long':
            count += 1
            if bot['is_enabled']:
                a_count += 1
    return count, a_count


def stop_all_bots(bots, account_id, dry):
    for bot in sorted(bots, key=lambda k: (''.join(k['pairs']))):
        if account_id == bot['account_id']:
            if bot['is_enabled']:
                print(f"Stopping {bot['name']}... ", end='')
                if not dry:
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


def start_all_bots(bots, account_id, dry):
    for bot in sorted(bots, key=lambda k: (''.join(k['pairs']))):
        #if args.binance_account_flag in bot['account_name']:
        if account_id == bot['account_id']:
            if bot['is_enabled'] or 'do not start' in bot['name']:
                pass # nothing to do
            else:
                print(f"Starting {bot['name']}... ", end='')
                if not dry:
                    xbot = get3CommasAPI().enableBot(BOT_ID=f"{bot['id']}")
                    if xbot['is_enabled']:
                        print("Bot is now enabled")
                    else:
                        print(f"{RED}Error: Could not enable bot{ENDC}")
                else:
                    print("")


# Maybe can combine both functions with default None
def start_bot_pair(bots, account_id, pair_to_start, dry):
    for bot in sorted(bots, key=lambda k: (''.join(k['pairs']))):
        #if args.binance_account_flag in bot['account_name']:
        if account_id == bot['account_id']:
            if bot['is_enabled'] or 'do not start' in bot['name'] or not ''.join(bot['pairs']).endswith(pair_to_start):
                pass # nothing to do
            else:
                print(f"Starting {bot['name']}... ", end='')
                if not dry:
                    xbot = get3CommasAPI().enableBot(BOT_ID=f"{bot['id']}")
                    if xbot['is_enabled']:
                        print("Bot is now enabled")
                    else:
                        print(f"{RED}Error: Could not enable bot{ENDC}")
                else:
                    print("")


def stop_bot_pair(bots, account_id, pair_to_stop, dry):
    for bot in sorted(bots, key=lambda k: (''.join(k['pairs']))):
        #if args.binance_account_flag in bot['account_name']:
        if account_id == bot['account_id']:
            if bot['is_enabled'] and ''.join(bot['pairs']).endswith(pair_to_stop):
                print(f"Stopping {bot['name']}... ", end='')
                if not dry:
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


# return FIRST matching accountID
def getAccountID(binance_account_flag):
    accounts=get3CommasAPI().getAccounts()
    for account in accounts:
        if account['exchange_name'] == "Binance Futures USDT-M" and binance_account_flag in account['exchange_name']:
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
    txt = f"{'Pair':6} : {'SOs':9} : ${'Bought':8} : ${'Reserve':7} : {'%Profit':7} : Age(DHM)\n"

    for ad in active_deals:
        error_message = f"{RED}{xstr(ad['error_message'])}{xstr(ad['failed_message'])}{ENDC}"
        a_flag = ''
        if ad['current_active_safety_orders_count'] == 0:
            a_flag = f'{RED}***Zero Active***{ENDC}'
            #if ad['completed_safety_orders_count'] != ad['max_safety_orders']:
            if ad['completed_safety_orders_count'] == 0:
                a_flag = f'{GREEN}***Closing/Opening***{ENDC}'
            else:
                a_flag = f'{YELLOW}***SO***{ENDC}'

        actual_usd_profit = float(ad['actual_usd_profit'])
        created_at_ts = datetime.strptime(ad['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        created_at_ts_diff = ts - created_at_ts
        reserved_cost, max_reserved_cost = get_deal_cost_reserved(ad)
        
        age_d = created_at_ts_diff.days
        age_d_str = str(age_d).rjust(2, '0')+' ' if age_d > 0 else '   '
        age_h = int((created_at_ts_diff.total_seconds()/3600)%24)
        age_h_str = str(age_h).rjust(2, '0')+':' if age_h > 0 else '   '
        age_m = int(((created_at_ts_diff.total_seconds()/3600) - int(created_at_ts_diff.total_seconds()/3600))*60)
        age_m_str = str(age_m).rjust(2, '0')# if age_m > 0 else '  '
        age = f"{age_d_str:3}{age_h_str:3}{age_m_str:2}"

        txt += f"{ad['pair'].replace('USDT_',''):6} : c{ad['completed_safety_orders_count']} a{ad['current_active_safety_orders_count']} m{ad['max_safety_orders']} : ${float(ad['bought_volume']):8.2f} : ${reserved_cost:7.2f} : {ad['actual_profit_percentage']:6}% : {age} {a_flag}{error_message}\n"

        total_bought_volume += float(ad['bought_volume'])
        total_deals_cost_reserved += reserved_cost
    txt += f"{'':18} : ${total_bought_volume:8.2f} : ${total_deals_cost_reserved:7.2f}"
    return txt

#----------------------------------
#----------------------------------
#----------------------------------



