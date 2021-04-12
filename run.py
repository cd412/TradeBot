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
import signal

#----------------------------------
'''
Usage:-

- Run main program:
Suggested:
time python3 run.py --show_all --beep --colors --auto --keep_running --stop_at 2 --bot_start_bursts 1 --bots_per_position_ratio 2 --pair_allowance 375 --binance_account_flag "Main"





Actual:

time python3 run.py --show_all --beep --colors --auto --keep_running --stop_at 2.5 --bot_start_bursts 3 --bots_per_position_ratio 3 --keep_running_timer 90 --pair_allowance 250 --binance_account_flag "Main"

time python3 run.py --show_all --beep --colors --auto --keep_running --stop_at 2.5 --bot_start_bursts 3 --bots_per_position_ratio 3 --keep_running_timer 90 --pair_allowance 250 --binance_account_flag "Sub 01"


- On a seperate machine, run safe mode in case main one gets killed so this one can stop all bots if things go wrong:
nohup python3 run.py --colors --auto --pair_allowance 200 --keep_running --stop_at 2.5 --keep_running_timer 600 --safe --binance_account_flag "Main" &
nohup python3 run.py --colors --auto --pair_allowance 200 --keep_running --stop_at 2.5 --keep_running_timer 600 --safe --binance_account_flag "Sub 01" &
tail -f nohup.out




Notes:-

- Make sure 'Futures' is in the name of the account or use --binance_account_flag to specify part of name

- Add 'do not start' to the name of the bots you do not want to start automatically

- To set up SMS notification when Margin Ratio is critical add to config file
    ifttt_url = 'https://maker.ifttt.com/trigger/Event_Name/with/key/xyz'
    and set up IFTTT webhook to SMS link



ToDo:-

- deal with connection reset errors
    - wait for a bit and try again

- Fix potential None to float errors in reports

- make deal line COLOR when %profit +/-

- move functions to utils
    - fix color issue in utils.py

- Need to consider multiplier when starting/stopping bots an counting them, not just for positions as now ???

- create files to dump all pairs in all futures accounts sorted by best to worst

- generate stats on deals history per pair (how much, multiplier, how long, add short and long, $/hr, etc)

- Merge deals and positions view and show if any deltas

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
parser.add_argument("--binance_account_flag", help='Part of binance account name identifier', default="Main")

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
        print(show_bots(bots, account_id))
        print("--------------------")
    '''
    if args.show_positions or args.show_all:
        print(show_positions(account['positions']))
        print("--------------------")
    '''
    if args.show_deals or args.show_positions or args.show_all:
        try:
            deals=get3CommasAPI().getDeals(OPTIONS=f"?account_id={account_id}&scope=active&limit=100")
            print(show_deals_positions(deals, account['positions'], args.colors))
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
        if margin_ratio >= args.stop_at:
            print(f"{RED}Hight margin_ratio, stopping bots...{ENDC}")
            stop_all_bots(bots, account_id, args.dry)
            if do_ifttt:
                import urllib.request
                ifttt_contents = urllib.request.urlopen(run_config.ifttt_url).read()
                print(ifttt_contents)
        else:
            top_stopped_pairs = get_top_stopped_pairs(bots, account_id)
            totalMarginBalance = get_totalMarginBalance(account)
            totalMaintMargin = get_totalMaintMargin(account)
            max_bot_pairs = get_max_bot_pairs(totalMarginBalance, args.pair_allowance)
            active_positions_count = get_active_positions_count(account['positions'], bots)
            total_bot_pair_count, active_bot_pair_count = get_bot_pair_count(bots, account_id)

            print(f"Total Margin Balance = ${totalMarginBalance:<.2f} (${totalMaintMargin:<.2f})")
            print(f"Bots Active/Total: {active_bot_pair_count}/{total_bot_pair_count}")
            stopped_bots_count = total_bot_pair_count - active_bot_pair_count
            position_delta_factor = (margin_ratio/args.stop_at - margin_ratio/args.start_at) * max_bot_pairs                
            position_delta_factor = round(position_delta_factor) if position_delta_factor > 0 else 0
            bots_pairs_to_start = round(max_bot_pairs - position_delta_factor - active_positions_count)
            print(f"Positions delta ({bots_pairs_to_start}) = target ({round(max_bot_pairs)}) - MR factor ({position_delta_factor}) - running ({active_positions_count})")

            if bots_pairs_to_start > 0 and not args.safe: # need more positions
                if len(top_stopped_pairs) > 0:
                    stopped_bots_with_positions = get_stopped_bots_with_positions(bots, account_id, account['positions'])
                    if len(stopped_bots_with_positions) > 0:
                        print(f"Starting {len(stopped_bots_with_positions)} stopped bots with active positions...")
                        for bot_to_start in stopped_bots_with_positions:
                            print(f"Starting {bot_to_start} bot pairs...")
                            start_bot_pair(bots, account_id, bot_to_start, args.dry)
                    else: # no stopped bots with positions to start, start from ones without active positions
                        max_bots_running = bots_pairs_to_start * args.bots_per_position_ratio
                        print (f"Need to start a max of {max_bots_running} stopped bot pairs...")

                        count_of_started_bots_without_positions = get_count_of_started_bots_without_positions(bots, account_id, account['positions'])
                        max_bots_running = max_bots_running - count_of_started_bots_without_positions
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
            elif bots_pairs_to_start < 0: # running too much positions
                if args.safe:
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

    if args.beep and margin_ratio >= args.stop_at:
        beep(beep_time)

    if args.beep:
        beep(1)


#----------------------------------
#----------------------------------
#----------------------------------

signal.signal(signal.SIGINT, signal_handler)

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
        print (account_txt)
        print ("-----------------------------------------------------------------")
        try:
            run_account(account, Binance_API_KEY, Binance_API_SECRET)
            sys.stdout.flush()
        except Exception as e:
            print(e)
            pass

        #ts_txt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        #print(f"      - {ts_txt}", end='')
        if args.dry:
            print("*************************")
            print("***Running in DRY mode***")
            print("*************************")
        sys.stdout.flush()
        countdown(args.keep_running_timer)
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


