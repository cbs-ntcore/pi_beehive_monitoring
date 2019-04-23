#!/bin/bash

source /home/pi/scripts/config.sh

# check state
STATE=`cat $STATE_FILE`
if [ "$STATE" != "recording" ]; then
   # remove cron job for recording
   (crontab -l) | sed '/record/d' | crontab -
   exit 0
fi

# make directory for today
DAYDIR=$VIDEO_DIR/`date +%y%m%d`
mkdir -p $DAYDIR

# record to temp filename to avoid rsync issues
TEMP_FN="/home/pi/current.h264"

# make new filename
FN=$DAYDIR/`date +%y%m%d_%H%M`_`hostname`.h264

echo "Recording to $FN"

# record for 20 seconds
raspivid -o $TEMP_FN -t 20000 -n -fps 3

# move temp file to videos directory
mv $TEMP_FN $FN

echo "Done recording"
