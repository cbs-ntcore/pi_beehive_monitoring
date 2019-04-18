
#!/bin/bash

# source configuration
source /home/pi/scripts/config.sh

# setup send state to run in crontab
if ! crontab -l | grep /home/pi/scripts/send_state.sh; then
    # add to crontab
    LINE="* * * * * /home/pi/scripts/send_state.sh"
    echo "Adding line to crontab: $LINE"
    (crontab -l; echo "$LINE") | crontab -
fi

mkdir -p $VIDEO_DIR
