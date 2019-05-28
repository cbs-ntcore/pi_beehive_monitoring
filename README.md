# Running/start-up

To check if the queen is running use 
[ps](http://linuxcommand.org/lc3_man_pages/ps1.html):

```bash
ps aux | grep queen.py
```

While the queen is running, it will output stderr and stdout messages to 
/home/pi/logs/ in a filename containing the date and time the queen started.

To start the queen if it's not running:

```bash
cd /home/pi/Repositories/cbs-ntcore/pi_beehive_monitoring/scripts/
./run_queen.sh
```

This will start the queen and setup a crontab entry to automatically restart 
the queen on reboot.

# Overview of system

The purpose of this system is to capture short videos (and save them for 
offline analysis) of many bee hive colonies as they develop. A single control 
computer (queen) is used to configure one or more (in this case 15) 
raspberry pi systems (workers).

![Image of system](docs/pi_beehive_monitoring.jpg)

## Queen - control computer

The queen runs a python script [queen.py](queen.py) (tested in python 3.X) that:

- runs a web server used for interacting with the queen and commanding workers
- receives worker state updates (via http)
- copies videos from each worker to the queen
- extracts a thumbnail from the early portion of each worker video
- reports the system status to the lab monitoring service

When the queen receives the first state message for a given worker, the queen 
will run [scripts/setup_worker.sh](scripts/setup_worker.sh). To configure the 
worker. This script will do the following:

- rsync ssh keys
- rsync (scripts)[scripts]
- call (scripts/setup.sh)[scripts/setup.sh] on the worker
- synchronize the worker time with the queen time

The [setup worker](scripts/setup_worker.sh) script is also used for the first 
configuration of a new worker computer after it has an appropriate hostname. 
Workers must have a hostname of the form workerN where N is some number 
(for example: worker10).

## Worker - video recording computer

Worker actions are in part controlled by 
[cron](https://en.wikipedia.org/wiki/Cron). A cron job setup to run on the 
worker every minute executes [scripts/send_state.sh](scripts/send_state.sh) 
to transfer of a state message from the worker to the queen. This state 
message contains:

- current state of the worker (see below)
- disk space left on worker
- current date and time on the worker

The worker can be in one of several states:

- idle
- recording: worker will call [scripts/record.sh](scripts/record.sh) every minute
- streaming: streaming video (see [scripts/stream.sh](scripts/stream.sh))

Workers can only enter recording or streaming states from the idle state. The 
state of the worker is saved in a state file (/home/pi/state). The worker also 
contains a setup file (/home/pi/setup) that is created during the first setup 
of the worker (see (scripts/setup.sh)[scripts/setup.sh]). 

Note that no more than 1 worker should be streaming at any time as streaming 
requires the queen to be actively receiving the video. Starting several streams 
might cause a worker to get stuck in a streaming state. This can be fixed by 
sshing into the worker, killing the raspivid process (used for streaming), then 
manually updating the state file or by rebooting the worker, removing the state 
file and re-setting up the worker.

# Videos

Videos are first saved on the workers (in /home/pi/videos). If a worker drive 
is more than 90% full prior to recording, the worker will delete the old videos 
in 30 file chunks until there is enough space (see 
[scripts/purge_videos.sh](scripts/purge_videos.sh)). Videos are separated into 
sub-directories by day and have a filename containing the worker hostname, date 
and time (for example: /home/pi/videos/190528/190528_153001_worker10.h264). 
Dates take the form of year, month, day (190528 = 28th of May, 2019). Times 
take the form of hour, minute, second (153001 = 1 second past 2:30 PM). Videos 
are saved as raw h264 streams and may need to be containerized before loading 
into some programs.

Once a minute (if the queen python script is running) the queen will transfer 
videos from all workers (using rsync) and store them in sub-directories in 
/home/pi/videos on the queen. Each worker will have it's own sub directory 
determined by it's worker number (so videos from worker 10 will be in 
/home/pi/videos/10).

See (scripts/record.sh)[scripts/record.sh] to change any raspivid settings for 
the recordings.