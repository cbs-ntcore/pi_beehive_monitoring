#!/bin/bash

# setup cron job to start recording
if ! crontab -l | grep /home/pi/scripts/run_queen.sh; then
    # add to crontab
    LINE="@reboot /home/pi/scripts/run_queen.sh"
    echo "Adding line to crontab: $LINE"
    (crontab -l; echo "$LINE") | crontab -
fi

# make log directory
mkdir -p /home/pi/logs

# make log filename
FN="/home/pi/logs/queen_`date %y%m%d_%H%M%S`"

# start up queen, writing to log file
python3 /home/pi/Repositories/cbs-ntcore/pi_beehive_monitoring/queen.py &> $FN
