#!/bin/bash

# source configuration
source /home/pi/scripts/config.sh

# get space left in video directory
DF=`df -h $VIDEO_DIR | tail -n 1 | awk '{print $2,$3,$5}'`

# make state message
HOSTNAME=`hostname`

# get current state
STATE=`cat $STATE_FILE`

# send state message to queen
MSG="{\"hostname\": \"$HOSTNAME\", \"state\": \"`cat $STATE_FILE`\", \"df\": \"$DF\"}"
#echo "Sending $MSG"
#echo $MSG | nc $QUEEN 5005 -w 1

EMSG=`python3 -c "import urllib.parse; print(urllib.parse.urlencode($MSG))"`
curl -d "$EMSG" -X POST http://$QUEEN:8888/worker
