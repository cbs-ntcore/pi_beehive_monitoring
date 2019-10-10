#!/bin/bash

echo "continuous" > /home/pi/state

# start recording, background process, store PID
source /home/pi/scripts/config.sh

# record to temp filename to avoid rsync issues
TEMP_FN="/home/pi/current.h264"

# make sure there is room for the video by purging any old videos
bash /home/pi/scripts/purge_videos.sh

# record (continuously)
nohup raspivid -o $TEMP_FN $RASPIVID_CONTINUOUS_OPTS &
RECORD_PID=$!

# save RECORD_PID
echo $RECORD_PID > /home/pi/.continuous_record.pid

echo "disowning pid: $RECORD_PID"
disown -h

echo "giving some time to start"
sleep 1s

echo "Started continuous recording"
bash /home/pi/scripts/send_state.sh noblock
