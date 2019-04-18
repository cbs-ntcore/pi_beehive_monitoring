#!/bin/bash

source /home/pi/scripts/config.sh

# check state
STATE=`cat $STATE_FILE`
if [ "$STATE" != "recording" ]; then
   # remove cron job for recording
   (crontab -l) | sed '/record/d' | crontab -
   exit 0
fi

# make videos directory
mkdir -p $VIDEO_DIR

# make new filename
FN=$VIDEO_DIR/`date +%y%m%d_%H%M`_`hostname`.h264

echo "Recording to $FN"

# record for 20 seconds
raspivid -o $FN -t 20000 -n -fps 3

echo "Done recording"
