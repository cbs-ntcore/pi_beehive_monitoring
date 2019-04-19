
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

# check if setup file exists
if [ ! -f $SETUP_FILE ]; then
    # if not, do all the one time setup
    echo "setup! `date`" > $SETUP_FILE
    
    # allow date to be run without sudo
    echo 'Cmnd_Alias DATE=/bin/date \n%pi ALL=(root) NOPASSWD: DATE' | sudo EDITOR='tee -a' visudo
    
    # change timezone to US eastern
    mv /usr/share/zoneinfo/US/Eastern /etc/localtime
fi