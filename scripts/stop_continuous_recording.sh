#!/bin/bash
# find stored PID of continuous recording, kill process

source /home/pi/scripts/config.sh

if [ -e /home/pi/.continuous_record.pid ]; then
    echo "Found file"
    RECORD_PID=`cat /home/pi/.continuous_record.pid`
    echo "Found pid: $RECORD_PID"
    n=0
    while [ $n -lt 20 ]; do
        if ps -p $RECORD_PID > /dev/null; then
            echo "Sending kill to $RECORD_PID"
            kill $RECORD_PID
        else
            break
        fi
        sleep 0.1
        (( n++ ))
    done
    if ps -p $RECORD_PID > /dev/null; then
        echo "Sending kill 9 to $RECORD_PID"
        kill -9 $RECORD_PID
    fi
fi

if [ -f /home/pi/current.h264 ]; then
    # make directory for today
    DAY=`date +%y%m%d`
    DAYDIR=$VIDEO_DIR/$DAY
    mkdir -p $DAYDIR

    # make new filename
    BFN=`date +%y%m%d_%H%M%S`_`hostname`_cont.h264
    FN=$DAYDIR/$BFN
    echo "New video: $FN"
    mv /home/pi/current.h264 $FN
fi


echo "idle" > /home/pi/state
