
#!/bin/bash

# where videos will be saved
export VIDEO_DIR='/home/pi/videos'
export RASPIVID_BASE_OPTS="-md 2"
export RASPIVID_SAVE_OPTS="$RASPIVID_BASE_OPTS -t 20000 -n -fps 3"
export RASPIVID_DISPLAY_OPTS="$RASPIVID_BASE_OPTS"

# setup default editor
export EDITOR=`which nano`

# location of pi state file
export STATE_FILE="/home/pi/state"

# location of one-time setup file
export SETUP_FILE="/home/pi/setup"

# check if state file exists
if [ ! -f $STATE_FILE ]; then
    # if not, set it to idle
    echo "idle" > $STATE_FILE
fi

export QUEEN="queen.local"

# ip/name of queen
if [ `hostname` == 'queen' ]; then
    export QUEENIP=`/sbin/ifconfig eth0 | grep netmask | awk '{print $2}'`
else
    export QUEENIP=`python -c "import socket; print(socket.gethostbyname('$QUEEN'))"`
    export WORKER="`hostname`.local"
    export WORKERIP=`/sbin/ifconfig eth0 | grep netmask | awk '{print $2}'`
fi
