#!/bin/bash

set -e

source /home/pi/scripts/config.sh

# don't allow drive to get > N percent full
FULLPERC=90

# to speed up space freeing, delete up to N files per delete
NFILESPERDELETE=30

# get space left on disk (as percent)
function get_used_space() {
    USEDSPACE=`df -h $VIDEO_DIR | tail -n 1 | awk '{print $5}'`
    USEDSPACE=${USEDSPACE::-1}
}

get_used_space

cd $VIDEO_DIR
if [[ $USEDSPACE -gt $FULLPERC ]]; then
    echo "Drive is too full"
    # delete old videos
    for SD in `ls $VIDEO_DIR`;
    do
        # navigate into subdirectory
        cd $VIDEO_DIR/$SD
        if ls -1qA $VIDEO_DIR/$SD | grep -q .; then
            # SD is not empty
            # delete some files until space is ok or no files are left
            # try to delete NFILESPERDELETE files
            while rm `ls | head -n $NFILESPERDELETE`; do
                get_used_space
                if [[ $USEDSPACE -lt $FULLPERC ]]; then
                    # have enough space, stop deleting
                    exit 0
                fi
            done
	    # deleted all files in directory and still not enough space
	    # keep deleting in other directories
        else
            # SD is empty, delete it
            cd $VIDEO_DIR
            rmdir $SD
        fi
    done
else
    echo "Drive is ok"
fi
