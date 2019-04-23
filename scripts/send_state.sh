#!/bin/bash

# source configuration
source /home/pi/scripts/config.sh

# get space left in video directory
DF=`df -h $VIDEO_DIR | tail -n 1 | awk '{print $2,$3,$5}'`

# make state message
HOSTNAME=`hostname`
MSG="{\"hostname\": \"$HOSTNAME\", \"state\": \"`cat $STATE_FILE`\", \"df\": \"$DF\"}"

# send state message to queen
echo "Sending $MSG"
echo $MSG | nc $QUEEN 5005 -w 1
