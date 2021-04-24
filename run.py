#!/usr/bin/env python


from binance_api import Binance
from tcommas_api import API3Commas
from utils import *
from pprint import pprint
import argparse
import sys
import time
import run_config
from datetime import datetime
from time import gmtime, strftime
#import signal
from timeout import timeout

#----------------------------------
'''

Goal:-

The goal here is to maximize the amount of positions you have while maintaining your safety levels when using Block Party Future Sniper bot with Binance Futures in 3Commas.
We do this by creating way more bots than we need and starting/stopping them as needed to get to the optimal positions count for the account.
E.g. for a $5000 account, assuming you want $500 per position, you will need 10 positions opened.  With 10 bots you will mostly stay under than number.
Here we add more bots and once we get to the 10 positions, we stop all the other bots.  We restart them (~in order of profitability based on history) once we drop bellow targetted positions.



If you find this useful, Buy me a Bubly:-
ETH: 0xce998ec4898877e17492af9248014d67590c0f46
BTC: 1BQT7tZxStdgGewcgiXjx8gFJAYA4yje6J



Disclaimer:-
Use this at your own risk.  There are inherent risks in bot trading and in adding this layer of automation on top of it.  I'm not responsible for anything :)
This is still work in progress.


Usage:-

- Run main program:
Suggested:
time python3 run.py --show_all --beep --colors --auto --keep_running --stop_at 2 --bot_start_bursts 1 --bots_per_position_ratio 2 --pair_allowance 375 --binance_account_flag "Main"


Actual:

cd ~/Downloads/3CommasAPI/
x time python3 run.py --show_all --beep --colors --auto --keep_running --stop_at 2 --bot_start_bursts 3 --bots_per_position_ratio 3 --keep_running_timer 60 --pair_allowance 500 --binance_account_flag "Main"
x time python3 run.py --show_all --beep --colors --auto --keep_running --stop_at 2 --bot_start_bursts 3 --bots_per_position_ratio 3 --keep_running_timer 65 --pair_allowance 500 --binance_account_flag "Sub 01"
x time python3 run.py --show_all --beep --colors --auto --keep_running --stop_at 2 --bot_start_bursts 3 --bots_per_position_ratio 3 --keep_running_timer 70 --pair_allowance 500 --binance_account_flag "Sub 02"

time python3 run.py --show_all --beep --colors --auto --keep_running --stop_at 1 --start_at 0.75 --bot_start_bursts 2 --bots_per_position_ratio 3 --keep_running_timer 65 --pair_allowance 375 --binance_account_flag "Main"

time python3 run.py --show_all --beep --colors --auto --keep_running --stop_at 1 --start_at 0.75 --bot_start_bursts 2 --bots_per_position_ratio 3 --keep_running_timer 65 --pair_allowance 375 --binance_account_flag "Sub 01"

time python3 run.py --show_all --beep --colors --auto --keep_running --stop_at 1 --start_at 0.75 --bot_start_bursts 2 --bots_per_position_ratio 3 --keep_running_timer 65 --pair_allowance 375 --binance_account_flag "Sub 02" --randomize_bots

- On a 2 seperate machines, run safe mode in case main one gets killed so this one can stop all bots if things go wrong:
nohup python3 run.py --colors --auto --pair_allowance 240 --keep_running --stop_at 2.5 --keep_running_timer 1800 --no_start --binance_account_flag "Main" &
nohup python3 run.py --colors --auto --pair_allowance 240 --keep_running --stop_at 2.5 --keep_running_timer 1800 --no_start --binance_account_flag "Sub 01" &
nohup python3 run.py --colors --auto --pair_allowance 240 --keep_running --stop_at 2.5 --keep_running_timer 1800 --no_start --binance_account_flag "Sub 02" &
tail -f nohup.out




Notes:-

- Make sure run_config.py has your 3commas names for accounts, --binance_account_flag to specify part of name that uniqly identifies the account

- Add 'do not start' to the name of the bots you do not want to start automatically

- To set up SMS notification when Margin Ratio is critical add to config file
    ifttt_url = 'https://maker.ifttt.com/trigger/Event_Name/with/key/xyz'
    and set up IFTTT webhook to SMS link



ToDo:-
- make bots_per_position_ratio dynamic based on how many positions needed...
    - delta/target * bots_per_position_ratio

- Detect if deals have more than one of the same pair (S/L)

- if error and +ve profit, sell at market (not currently working)

- Need to consider multiplier when starting/stopping bots an counting them, not just for positions as now

- generate stats on deals history per pair (how much, multiplier, how long, add short and long, $/hr, etc)

- Add notification through email or Google Home? (IFTTT is done for MR >= critical)

- Allow hardcoded Generate list of pairs sorted by first to start.


'''
#----------------------------------


parser = argparse.ArgumentParser()


parser.add_argument("--dry", help='Dry run, do not start/stop bots', action='store_true', default=None)
parser.add_argument("--auto", help='Auto Stop/Start bots based on Margin Ratio', action='store_true', default=None)
parser.add_argument("--stop_at", help='Stop bots when Margin Ratio >= value', type=float, default=2.5)
parser.add_argument("--start_at", help='Start bots when Margin Ratio <= value', type=float, default=1.5) # not really used currently
parser.add_argument("--bot_start_bursts", help='Number of bots to start each time', type=int, default=3)
parser.add_argument("--bots_per_position_ratio", help='Open a max number of bots ratio for each needed position', type=int, default=3)
parser.add_argument("--binance_account_flag", help='Part of binance account name identifier', default="Main")
parser.add_argument("--randomize_bots", help='Select pairs/bots to start in random order', action='store_true', default=None)

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
parser.add_argument("--no_start", help='Run in safe mode (as a backup) with different values to make sure to stop (and not start) bots', action='store_true', default=None)
parser.add_argument("--debug", help='debug', action='store_true', default=None)

args = parser.parse_args()

if args.start_at >= args.stop_at:
    print("Error: start_at can't be more than or equal to stop_at")
    exit(1)

#----------------------------------

beep_time = 2
if args.colors:
    ENDC   = '\033[0m'
    RED    = '\033[91m'
    GREEN  = '\033[92m'
    YELLOW = '\033[93m'
    BLINK  = '\033[5m'
    BOLD   = '\033[1m'
else:
    ENDC   = ''
    RED    = ''
    GREEN  = ''
    YELLOW = ''
    BLINK  = ''
    BOLD   = ''


#----------------------------------

do_ifttt = True
try:
    _ = run_config.ifttt_url
except Exception:
    do_ifttt = False

#----------------------------------


#----------------------------------
#----------------------------------
#----------------------------------
@timeout(100)
def run_account(account_id, api_key, api_secret):

    account=getBinanceAPI(api_key, api_secret).futuresAccount()

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
        try:
            print(show_bots(bots, account_id))
            print("--------------------")
        except Exception as e:
            print(e)
            pass
    '''
    if args.show_positions or args.show_all:
        print(show_positions(account['positions']))
        print("--------------------")
    '''
    if args.show_deals or args.show_positions or args.show_all:
        try:
            deals=get3CommasAPI().getDeals(OPTIONS=f"?account_id={account_id}&scope=active&limit=100")
            show_deals_positions_txt = show_deals_positions(deals, account['positions'], args.colors)
            #print(show_deals_positions(deals, account['positions'], args.colors))
            print(show_deals_positions_txt)
            if "Error" in show_deals_positions_txt:
                beep(5)
                #if do_ifttt:
                #    import urllib.request
                #    ifttt_contents = urllib.request.urlopen(run_config.ifttt_url).read()
                #    print(ifttt_contents)
            #print(show_deals(deals))
        except Exception as e:
            print(e)
            pass
        #print("--------------------")

    color = YELLOW+BLINK
    if margin_ratio >= args.stop_at:
        color = RED+BLINK+BOLD
    if margin_ratio <= args.start_at:
        color = GREEN

    print(f"{color}****************************{ENDC}")
    print(f"{color}*** Margin Ratio = {margin_ratio:0.2f}% ***{ENDC}")
    print(f"{color}****************************{ENDC}")
    #print("--------------------")

    if args.auto:
        top_stopped_pairs = get_top_stopped_pairs(bots, account_id)
        totalMarginBalance = get_totalMarginBalance(account)
        totalMaintMargin = get_totalMaintMargin(account)
        max_bot_pairs = get_max_bot_pairs(totalMarginBalance, args.pair_allowance)
        active_positions_count = get_active_positions_count(account['positions'], bots)
        total_bot_pair_count, active_bot_pair_count, dns_bot_pair_count = get_bot_pair_count(bots, account_id)

        print(f"Total Margin Balance = ${totalMarginBalance:<.2f} (${totalMaintMargin:<.2f})")
        print(f"Bots Active/Total: {active_bot_pair_count}/{total_bot_pair_count} (-{dns_bot_pair_count})")
        stopped_bots_count = total_bot_pair_count - active_bot_pair_count
        position_delta_factor = (margin_ratio/args.stop_at - margin_ratio/args.start_at) * max_bot_pairs
        position_delta_factor = round(position_delta_factor) if position_delta_factor > 0 else 0
        bots_pairs_to_start = round(max_bot_pairs - position_delta_factor - active_positions_count)
        print(f"Positions delta ({bots_pairs_to_start}) = target ({round(max_bot_pairs)}) - MR factor ({position_delta_factor}) - running ({active_positions_count})")
        if margin_ratio >= args.stop_at:
            print(f"{RED}Hight margin_ratio, stopping bots...{ENDC}")
            stop_all_bots(bots, account_id, args.dry)
            if do_ifttt and margin_ratio >= 5:
                import urllib.request
                ifttt_contents = urllib.request.urlopen(run_config.ifttt_url).read()
                print(ifttt_contents)
        else:
            if bots_pairs_to_start > 0: # need more positions
                if not args.no_start:
                    if margin_ratio < args.start_at:
                        if len(top_stopped_pairs) > 0:
                            stopped_bots_with_positions = get_stopped_bots_with_positions(bots, account_id, account['positions'])
                            if len(stopped_bots_with_positions) > 0:
                                print(f"Starting {len(stopped_bots_with_positions)} stopped bots with active positions...")
                                for bot_to_start in stopped_bots_with_positions:
                                    print(f"Starting {bot_to_start} bot pairs...")
                                    start_bot_pair(bots, account_id, bot_to_start, args.dry)
                            else: # no stopped bots with positions to start, start from ones without active positions
                                dynamic_bots_per_position_ratio = round((bots_pairs_to_start/max_bot_pairs) * args.bots_per_position_ratio) + 1
                                #print(f"dynamic_bots_per_position_ratio = {dynamic_bots_per_position_ratio}")
                                max_bots_running = bots_pairs_to_start * dynamic_bots_per_position_ratio
                                print (f"Need to start a max of {max_bots_running} stopped bot pairs...")

                                count_of_started_bots_without_positions = get_count_of_started_bots_without_positions(bots, account_id, account['positions'])
                                max_bots_running = max_bots_running - count_of_started_bots_without_positions
                                if args.randomize_bots:
                                    stopped_bots_without_positions = get_stopped_bots_without_positions_random(bots, account_id, account['positions'])
                                else:
                                    stopped_bots_without_positions = get_stopped_bots_without_positions(bots, account_id, account['positions'])
                                actual_bots_to_start = min(max_bots_running, args.bot_start_bursts, len(stopped_bots_without_positions), max_bots_running)
                                actual_bots_to_start = 0 if actual_bots_to_start <= 0 else actual_bots_to_start # Make sure it's not a negative number

                                print (f"Incrementally starting {actual_bots_to_start} stopped bots without positions...")
                                burst_pairs_to_start = stopped_bots_without_positions[:actual_bots_to_start] # Assume list is sorted
                                for bot_to_start in burst_pairs_to_start:
                                    print(f"Starting {bot_to_start} bot pairs...")
                                    start_bot_pair(bots, account_id, bot_to_start, args.dry)
                        else:
                            print("No stopped bots to start...")
                    else:
                        print(f"{YELLOW}Hight margin_ratio, not starting any bots...{ENDC}")

            elif bots_pairs_to_start < 0: # running too much positions
                if args.no_start:
                    print("Hight positions count, stopping all running bots...")
                    stop_all_bots(bots, account_id, args.dry)
                else:
                    started_bots_without_positions = get_started_bots_without_positions(bots, account_id, account['positions'])
                    print(f"Hight positions count, stopping {len(started_bots_without_positions)} bots without positions")
                    for bot_to_stop in started_bots_without_positions:
                        print(f"Stopping {bot_to_stop} bot pairs...")
                        stop_bot_pair(bots, account_id, bot_to_stop, args.dry)
            else: # the right ammount of positions running
                print("No change to positions count needed...")
                started_bots_without_positions = get_started_bots_without_positions(bots, account_id, account['positions'])
                print(f"Correct positions count, stopping {len(started_bots_without_positions)} bots without positions")
                for bot_to_stop in started_bots_without_positions:
                    print(f"Stopping {bot_to_stop} bot pairs...")
                    stop_bot_pair(bots, account_id, bot_to_stop, args.dry)

    if args.beep and margin_ratio >= args.stop_at:
        beep(beep_time)

    #if args.beep:
    #    beep(1)


#----------------------------------
#----------------------------------
#----------------------------------
'''
try:
    _ = signal.SIGALRM
    signal.signal(signal.SIGINT, signal_handler)
except:
    pass
'''
print ("-----------------------------------------------------------------")
print ("-----------------------------------------------------------------")

found_account = False
try:
    _ = run_config.Binance_APIs
    for Binance_API in run_config.Binance_APIs:
        #print(
        if args.binance_account_flag in Binance_API['account_name']:
            found_account = True
            account_name = Binance_API['account_name']
            Binance_API_KEY = Binance_API['Binance_API_KEY']
            Binance_API_SECRET = Binance_API['Binance_API_SECRET']
except Exception:
    found_account = True
    account_name = args.binance_account_flag
    Binance_API_KEY = run_config.Binance_API_KEY
    Binance_API_SECRET = run_config.Binance_API_KEY

if not found_account:
    print(f"Error: could not find account with flag {args.binance_account_flag}")
    exit(1)


account, account_txt = getAccountID(account_name)

if args.keep_running:
    while True:
        keep_running_timer = args.keep_running_timer
        print (account_txt)
        print ("-----------------------------------------------------------------")
        try:
            run_account(account, Binance_API_KEY, Binance_API_SECRET)
            sys.stdout.flush()
        except Exception as e:
            print(e)
            keep_running_timer = int(args.keep_running_timer/10)
            pass

        #ts_txt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        #print(f"      - {ts_txt}", end='')
        if args.dry:
            print("*************************")
            print("***Running in DRY mode***")
            print("*************************")
        sys.stdout.flush()
        countdown(keep_running_timer)
        print()
        print ("-----------------------------------------------------------------")
else:
    print (account_txt)
    print ("-----------------------------------------------------------------")
    run_account(account, Binance_API_KEY, Binance_API_SECRET)
    if args.dry:
        print("*************************")
        print("***Running in DRY mode***")
        print("*************************")
    sys.stdout.flush()


