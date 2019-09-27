#!/bin/bash

echo "continuous" > /home/pi/state

# start recording, background process, store PID
source /home/pi/scripts/config.sh

# record to temp filename to avoid rsync issues
TEMP_FN="/home/pi/current.h264"

# make sure there is room for the video by purging any old videos
bash /home/pi/scripts/purge_videos.sh

# record (continuously)
raspivid -o $TEMP_FN $RASPIVID_CONTINUOUS_OPTS &
RECORD_PID=$!

# save RECORD_PID
echo $RECORD_PID > /home/pi/.continuous_record.pid

echo "Started continuous recording"
