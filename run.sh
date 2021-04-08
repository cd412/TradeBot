#!/bin/bash

TIMEFORMAT=%R
printf '\e[?5l'

while true; do
    ts=$(date '+%Y%m%d%H%M%S')
    time python3 run.py --show_bots --show_positions --beep --auto 2>&1 | tee logs/run_${ts}.out
    cp logs/run_${ts}.out /media/fuse/drivefs-a31dccd3a6968c88c6d04d46354ec036/root/_My\ Documents/Finance/logs/run_latest.out

    #sleep 300 # 5 minutes
    secs=$((5 * 60))
    while [ $secs -gt 0 ]; do
       echo -ne "$secs\033[0K\r"
       sleep 1
       : $((secs--))
    done
done


