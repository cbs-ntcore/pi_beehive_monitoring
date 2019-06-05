#!/bin/bash

set -e

source /home/pi/scripts/config.sh

if [ `hostname` == 'queen' ]; then
    echo "$0 cannot be run on the queen"
    exit 1
fi

if [[ `hostname` =~ ^worker ]]; then
    echo "This is a worker"
else
    echo "$0 must be run on a worker"
    exit 2
fi

if [ -z "$VIDEO_DIR" ]; then
    echo "Missing video directory: $VIDEO_DIR"
    exit 3
fi

read -p "Are you sure you want to run: rm -rf $VIDEO_DIR/*" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "removing all videos in $VIDEO_DIR"
    rm -rf $VIDEO_DIR/*
else
    echo "skipping removal of videos"
fi
