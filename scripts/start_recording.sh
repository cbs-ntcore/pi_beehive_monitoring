#!/bin/bash

echo "recording" > /home/pi/state

source /home/pi/scripts/config.sh

# setup cron job to start recording
if ! crontab -l | grep /home/pi/scripts/record.sh; then
    # add to crontab
    echo "Adding line to crontab: $CRON_LINE"
    (crontab -l; echo "$CRON_LINE") | crontab -
fi
