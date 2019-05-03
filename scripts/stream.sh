#!/bin/bash

source /home/pi/scripts/config.sh

STATE=`cat $STATE_FILE`
if [ "$STATE" != "idle" ]; then
  echo "Cannot start streaming as state[$STATE] is not idle"
  exit 1
fi

echo "streaming" > $STATE_FILE

raspivid -l -o tcp://$WORKERIP:2222 -t 0 -n -l -b 1000000 -ih -pf baseline -w 640 -h 480 -fps 30
#raspivid -l -o tcp://$WORKERIP:2222 -t 0 -n -l -b 1000000 -ih -pf baseline -md 2

echo "idle" > $STATE_FILE
