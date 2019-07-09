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
DAY=`date +%y%m%d`
DAYDIR=$VIDEO_DIR/$DAY
mkdir -p $DAYDIR

# record to temp filename to avoid rsync issues
TEMP_FN="/home/pi/current.h264"

# make new filename
BFN=`date +%y%m%d_%H%M%S`_`hostname`.h264
FN=$DAYDIR/$BFN

echo "Recording to $FN"

# make sure there is room for the video by purging any old videos
bash /home/pi/scripts/purge_videos.sh

# record for 20 seconds
raspivid -o $TEMP_FN -t 20000 -n -fps 3 -md 2 -co 25 -ag 1.5 -br 45 -awb cloud

# move temp file to videos directory
mv $TEMP_FN $FN

# update symlink for most recent
#cd $VIDEO_DIR
#SFN=`hostname`.h264
#rm $SFN
#ln -s $DAY/$BFN $SFN

echo "Done recording"
