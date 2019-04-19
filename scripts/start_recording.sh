#!/bin/bash

echo "recording" > /home/pi/state

# setup cron job to start recording
if ! crontab -l | grep /home/pi/scripts/record.sh; then
    # add to crontab
    LINE="* * * * * /home/pi/scripts/record.sh"
    echo "Adding line to crontab: $LINE"
    (crontab -l; echo "$LINE") | crontab -
fi
