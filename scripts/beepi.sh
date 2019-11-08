#!/bin/bash

set -e

source /home/pi/scripts/config.sh

function queen_help {
    cat <<EOF
Usage: beepi COMMAND

Inspect and control the queen.py python process on the queen computer

Commands:

  status
    get status of queen.py process

  kill
    kill any currently running queen.py process

  run
    start a new queen.py process
EOF
}

function queen {
    if [[ $# -lt 1 ]]; then
        echo "No command provided"
        queen_help
        exit 1
    fi

    # get queen pid (-1 if not running)
    QUEEN_PID=`ps aux | grep queen.py | grep python | awk '{print $2}'`
    if [ -z $QUEEN_PID ]; then
        QUEEN_PID=-1
    fi

    case "$1" in
        status)
            if [[ $QUEEN_PID -eq -1 ]]; then
                echo "queen.py is NOT running"
            else
                echo "queen.py running in process: $QUEEN_PID"
            fi
            exit 0
            ;;
        kill)
            if [[ $QUEEN_PID -eq -1 ]]; then
                echo "queen.py is NOT running"
                exit 0
            fi
            echo "killing process: $QUEEN_PID"
            kill $QUEEN_PID
            exit 0
            ;;
        run)
            if [[ $QUEEN_PID -ne -1 ]]; then
                echo "queen.py is already running in process $QUEEN_PID"
                echo "please kill the queen before starting"
                exit 0
            fi
            bash run_queen.sh
            ;;
        -h|--help|help|*)
            queen_help
            exit 1
            ;;
    esac
}

function worker_help {
    cat <<EOF
Usage: beepi COMMAND

Inspect and control the worker computer

Commands:
  state [new state]
  display
EOF
}

function worker {
    if [[ $# -lt 1 ]]; then
        echo "No command provided"
        worker_help
        exit 1
    fi
    STATE=`cat $STATE_FILE`
    case "$1" in
        state)
            if [[ $# -gt 1 ]]; then
                NEW_STATE=$2
                case "$NEW_STATE" in
                    idle)
                        echo "Setting worker state to $NEW_STATE"
                        echo "$NEW_STATE" > $STATE_FILE
                        ;;
                    recording)
                        echo "Setting worker state to $NEW_STATE"
                        echo "$NEW_STATE" > $STATE_FILE
                        ;;
                    *)
                        echo "Invalid state $NEW_STATE not idle or recording"
                        exit 1
                        ;;
                esac
                exit 0
            else
                # report state
                echo "Current state is: $STATE"
            fi
            exit 0
            ;;
        display)
            # make sure state is idle
            if [ "$STATE" != "idle" ]; then
                echo "Worker[$STATE] must be idle to display video"
                exit 1
            fi
            # start raspivid process
            raspivid $RASPIVID_DISPLAY_OPTS
            exit 0
            ;;
        -h|--help|help|*)
            worker_help
            ;;
    esac
}

# check if worker or queen
if [ `hostname` == 'queen' ]; then
    queen $@
else
    worker $@
fi
