![Image of system](docs/pi_beehive_monitoring.jpg)

To check if the queen is running use [ps](http://linuxcommand.org/lc3_man_pages/ps1.html):

```bash
ps aux | grep queen.py
```

While the queen is running, it will output stderr and stdout messages to /home/pi/logs/ in a filename containing the date and time the queen started.

To start the queen if it's not running:

```bash
cd /home/pi/Repositories/cbs-ntcore/pi_beehive_monitoring/scripts/
./run_queen.sh
```
