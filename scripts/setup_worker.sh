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

# synchronize date
# requires passwordless sudo permission for the date command on the worker
# enable this by:
# - sshing into client
# - run: sudo visudo
# - add the following lines (without the # character)
#
# Cmnd_Alias DATE=/bin/date
# %pi ALL=(root) NOPASSWD: DATE
DATE=`date`
ssh sudo date --set="$DATE"