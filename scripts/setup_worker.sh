#!/bin/bash

# stop on error
set -e

# read in worker number from first argument
WORKER_NUMBER="$1"

NUMBER_RE='^[0-9]+$'
if ! [[ $WORKER_NUMBER =~ $NUMBER_RE ]]; then
    echo "Error worker is not a number" >&2; exit 1
fi

WORKER="worker$WORKER_NUMBER.local"

# copy over ssh keys (will learn ssh fingerprint)
rsync -rtuv /home/pi/.ssh/id_rsa.pub /home/pi/.ssh/authorized_keys $WORKER:/home/pi/.ssh

# copy over scripts
rsync -rtuv /home/pi/scripts/* $WORKER:/home/pi/scripts

# start ping
ssh $WORKER /home/pi/scripts/setup.sh

# copy over scripts
rsync -rtuv /home/pi/scripts/* $WORKER:/home/pi/scripts

# start ping
ssh $WORKER /home/pi/scripts/setup.sh

# synchronize date
DATE=`date -I"seconds"`
echo "Setting worker date: $DATE"
ssh $WORKER sudo date --set="$DATE"
