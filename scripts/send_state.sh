#!/bin/bash

# source configuration
source /home/pi/scripts/config.sh

# make state message
HOSTNAME=`hostname`
MSG="{\"hostname\": \"$HOSTNAME\", \"state\": \"`cat $STATE_FILE`\"}"

# send state message to queen
echo "Sending $MSG"
echo $MSG | nc $QUEEN 5005 -w 1
