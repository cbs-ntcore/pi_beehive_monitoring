#!/bin/bash

source /home/pi/scripts/config.sh

# trash videos that are 2 days old
TRASHNDAYS=2

# make trash directory (if it doesn't exist)
mkdir -p $VIDEO_DIR/.trash

# delete all videos in trash
#rm -rf $VIDEO_DIR/.trash/*

CUTOFF=`python3 -c "from datetime import *; print(datetime.strftime(datetime.now() - timedelta(days=$TRASHNDAYS), '%y%m%d'))"`


echo "Deleting videos as old as $CUTOFF"
# move all videos as old as CUTOFF to trash
for FN in `ls $VIDEO_DIR | grep -e '^.\{6\}$'`; do
    if [[ $FN -lt $CUTOFF ]]; then
        mv $VIDEO_DIR/$FN $VIDEO_DIR/.trash/
    fi
done
