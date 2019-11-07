#!/bin/bash

echo "idle" > /home/pi/state

bash /home/pi/scripts/send_state.sh noblock
