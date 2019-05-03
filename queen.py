#!/usr/bin/env python3
"""
TODO
- auto-discover and force state updates for workers on startup?
- setup queen to automatically run on reboot
- query worker date and resync
- extract first frame from video and show in ui
- give download link for newest video
"""

import datetime
import fcntl
import json
import os
import socket
import struct
import subprocess
import sys
import threading
import time
import urllib.request


import tornado
import tornado.httpserver
import tornado.ioloop
import tornado.process
import tornado.web


def get_ip_address(ifname='eth0'):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(), 0x8915,
        struct.pack('256s', bytes(ifname[:15], 'utf-8')))[20:24])


# setup stream command with this ip
#queen_port = 5005
#if len(sys.argv) == 1:
#    queen_ip = get_ip_address()
#else:
#    queen_ip = sys.argv[1]

# if worker and queen times differ by more than N seconds re-setup the worker
RESYNC_THRESHOLD_SECONDS = 300
monitor_device_id = 'jdrcLaptop'
monitor_url_template = 'http://lab.debivort.org/mu.php?id={device_id}&st={status}'
scripts_directory = '/home/pi/scripts'
videos_directory = '/home/pi/videos'
this_directory = os.path.dirname(os.path.realpath(__file__))
static_path = os.path.join(this_directory, 'static')


def update_monitor(device_id, status=10005):
    try:
        urllib.request.urlopen(
            monitor_url_template.format(
                device_id=device_id,
                status=status))
    except Exception as e:
        print("Failed to update monitor[%s]: %s" % (device_id, e))


def extract_image(vfn, ifn, frame_number=3):
    # start subprocess to extract frame from video
    cmd = [
        "ffmpeg", "-i", str(vfn),
        "-vf", 'select=eq(n\,%s), scale=320:-2' % frame_number,
        "-vframes", "1", "-q:v", "3", str(ifn), "-y"
    ]
    st = time.time()
    p = tornado.process.Subprocess(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    f = p.wait_for_exit()

    def extraction_done(f, fn=vfn, t0=st):
        #print("extraction from %s done[%s]" % (fn, time.time() - t0))
        pass

    tornado.ioloop.IOLoop.current().add_future(f, extraction_done)


def link_newest_worker_video(hostname, directory):
    # find newest worker video
    sds = sorted(os.listdir(directory))
    if len(sds) == 0:
        return
    sd = sds[-1]
    fns = sorted(os.listdir(os.path.join(directory, sd)))
    if len(fns) == 0:
        return
    fn = os.path.join(directory, sd, fns[-1])
    #print("most recent file: %s" % fn)

    # link to /static/{hostname}.h264
    sfn = os.path.join(static_path, hostname) + '.h264'
    if os.path.islink(sfn):  # a broken link will return Fales for exists
        #print("unlinking file: %s" % sfn)
        os.unlink(sfn)
    #print("linking: %s, %s" % (fn, sfn))
    os.symlink(fn, sfn)

    # extract jpg
    ifn = os.path.join(static_path, hostname) + '.jpg'
    extract_image(sfn, ifn)


class Worker:
    def __init__(self, hostname, state, ip):
        self.state_timestamp = time.time()
        self.hostname = hostname
        self.state = state
        self.ip = ip
        self.number = int(self.hostname.strip('worker').strip('.local'))
        self.stream = None
        self.fetch_process = None
        self.last_transfer = {}
        self.last_transfer_duration = -1
        self.failed_transfer = None

    def __repr__(self):
        return "%s(%s[%s]: %s)" % (
            self.__class__, self.ip, self.hostname, self.state)

    def change_state(self, new_state):
        if new_state == 'setup':
            return self.setup()
        if new_state == self.state['state']:
            return
        if new_state == 'recording':
            if self.state['state'] != 'idle':
                raise Exception("Can only start recording from idle")
            self.start_recording()
            return
        elif new_state == 'streaming':
            if self.state['state'] != 'idle':
                raise Exception("Can only start streaming from idle")
            self.start_streaming()
            return
        elif new_state == 'idle':
            if self.state['state'] == 'recording':
                self.stop_recording()
            elif self.state['state'] == 'streaming':
                self.stop_streaming()
            return
        else:
            raise Exception("Unknown state: %s" % (new_state, ))

    def update_state(self, state):
        self.state = state
    
    def setup(self):
        # run setup_worker.sh script on queen
        cmd = 'bash %s %s' % (
            os.path.join(scripts_directory, 'setup_worker.sh'), self.number)
        subprocess.check_call(cmd.split())
    
    def start_streaming(self):
        if self.stream is not None:
            self.stream.terminate()
        # make subprocess that sshes into pi and
        # runs /home/pi/scripts/stream.sh
        cmd = "ssh pi@%s bash /home/pi/scripts/stream.sh" % (self.ip, )
        self.stream = subprocess.Popen(cmd.split())
        # receive and display stream
        time.sleep(1.0)  # give time to start stream
        vlc_cmd = 'vlc tcp/h264://%s:2222' % (self.ip, )
        # run vlc using queen display
        subprocess.check_call(
            vlc_cmd.split(), env={'DISPLAY': ':0'})

    def stop_streaming(self):
        pass

    def run_script(self, name):
        cmd = "ssh pi@%s bash /home/pi/scripts/%s.sh" % (self.ip, name)
        return subprocess.check_call(cmd.split())

    def start_recording(self):
        self.run_script("start_recording")
    
    def stop_recording(self):
        self.run_script("stop_recording")

    def is_fetching(self):
        return self.fetch_process is not None

    def fetch_videos(self, to_dir, autoremove=False, in_loop=False):
        # rsync videos from worker to queen directory to_dir
        # delete from worker after transfer
        cmd = 'rsync '
        if autoremove:
            cmd += '--remove-source-files '
        cmd += (
            '-rtuvW --exclude=".*" --size-only %s:/home/pi/videos/ %s' %
            (self.ip, to_dir.rstrip('/')))
        st = time.time()
        if not in_loop:
            r = subprocess.check_call(
                cmd.split(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            link_newest_worker_video(self.hostname, to_dir)
            self.last_transfer = {'start': st, 'end': time.time()}
            self.last_transfer_duration = (
                self.last_transfer['end'] - self.last_transfer['start'])
            return r

        # otherwise run in tornado ioloop
        if self.fetch_process is not None:
            return False

        self.last_transfer = {'start': st}
        self.fetch_process = tornado.process.Subprocess(
            cmd.split(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        loop = tornado.ioloop.IOLoop.current()

        def transfer_done(future, worker=self):
            worker.fetch_process = None
            worker.last_transfer['end'] = time.time()
            worker.last_transfer['result'] = future.result()
            worker.last_transfer_duration = (
                worker.last_transfer['end'] - worker.last_transfer['start'])
            print(
                "Worker[%s] transfer finished: %s[%s]" % (
                    worker.hostname,
                    worker.last_transfer_duration,
                    worker.last_transfer['result']))
            if worker.last_transfer['result'] == 0:
                link_newest_worker_video(self.hostname, to_dir)
                update_monitor(worker.hostname)
            else:
                self.failed_transfer = self.last_transfer.copy()

        f = self.fetch_process.wait_for_exit(raise_error=False)
        loop.add_future(f, transfer_done)
        return True



class Queen(object):
    def __init__(self):
        self.workers = {}
        self.errors = []  # TODO expose these to the UI
        self.last_worker_transfer_time = None
        self.last_worker_transfer_duration = None

    def update_worker_state(self, hostname, state, ip):
        # lookup worker
        if hostname in self.workers:
            worker = self.workers[hostname]
            # update state
            worker.update_state(state)
            # check if time is correct
            dt = datetime.datetime.now()
            wdt = datetime.datetime.strptime(
                state['datetime'][:-6],
                "%Y-%m-%dT%H:%M:%S")
            ddt = abs((dt - wdt).total_seconds())
            if (ddt > RESYNC_THRESHOLD_SECONDS):
                self.errors.append({
                    "time": time.time(),
                    "worker": hostname,
                    "operation": 'resync',
                    "exception": "worker %s: queen %s" % (wdt, dt),
                })
                worker.setup()
        else:
            # if not make new one
            worker = Worker(hostname, state, ip)
            worker.setup()
            self.workers[hostname] = worker

    def fetch_worker_videos(self, to_dir=None, autoremove=False):
        # send monitor update
        update_monitor(monitor_device_id)
        if to_dir is None:
            to_dir = videos_directory
        self.last_worker_transfer_time = time.time()
        if not os.path.exists(to_dir):
            os.makedirs(to_dir)
        for hostname in list(self.workers.keys()):
            w = self.workers[hostname]
            if w.failed_transfer is not None:  # last transfer failed
                # worker transfer failed, remove worker
                self.errors.append({
                    "time": time.time(),
                    "worker": hostname,
                    "operation": "fetch",
                    "exception": repr(e),
                })
                del self.workers[hostname]
                continue
            d = os.path.join(to_dir, '%i' % w.number)
            try:
                w.fetch_videos(d, autoremove, in_loop=True)
                #link_newest_worker_video(hostname, d)
            except Exception as e:
                # worker transfer failed, remove worker
                self.errors.append({
                    "time": time.time(),
                    "worker": hostname,
                    "operation": "fetch",
                    "exception": repr(e),
                })
                del self.workers[hostname]
        self.last_worker_transfer_duration = (
            time.time() - self.last_worker_transfer_time)

    def get_space_in_directory(self, directory):
        # df -h directory | tail -n 1 | awk '{print $2,$3,$5}
        cmd = "df -h %s" % directory
        output = subprocess.check_output(cmd, shell=True).decode('latin8')
        # parse output
        lines = output.strip().split(os.linesep)
        l = lines[-1]
        ts = l.split()
        space, used, perc = ts[1], ts[2], ts[4]
        return space, used, perc

    def get_transfer_info(self, to_dir=None):
        if to_dir is None:
            to_dir = videos_directory
        space, used, perc = self.get_space_in_directory(to_dir)
        return {
            'last_transfer': {
                'time': self.last_worker_transfer_time,
                'duration': self.last_worker_transfer_duration,
            },
            'space': {
                'total': space,
                'used': used,
                'percent_used': perc,
            },
        }


def setup_periodic_video_transfer(queen, interval=60):
    if (interval < 60) or (interval > 86401):
        raise ValueError("Out of range")
    if hasattr(queen, '_transfer_pcb'):
        queen._transfer_pcb.stop()
    cb = tornado.ioloop.PeriodicCallback(
        queen.fetch_worker_videos, interval * 1000)
    cb.start()
    queen._transfer_pcb = cb


class QueenSite(tornado.web.RequestHandler):
    def get(self):
        # self.application.queen
        # return list of workers and states
        #s = "Workers:\n"
        #s += "\n".join([str(w) for w in self.application.queen.workers])
        #s += "\n"
        #self.write(s)
        template = os.path.join(this_directory, 'index.html')
        self.render(template)


class QueenQuery(tornado.web.RequestHandler):
    def post(self):
        args = list(self.request.arguments.keys())
        kwargs = {k: self.get_argument(k) for k in args}
        if 'transfer_info' in kwargs:
            self.write(json.dumps(self.application.queen.get_transfer_info()))
        elif 'errors' in kwargs:
            self.write(json.dumps(self.application.queen.errors))
        elif 'transfer' in kwargs:
            # transfer worker videos (periodically in tornado loop?)
            if 'interval' in kwargs:
                try:
                    setup_periodic_video_transfer(
                        self.application.queen, int(kwargs['interval']))
                except Exception as e:
                    self.clear()
                    self.set_status(400)
                    self.write("failed to setup periodic transfer: %s" % (e, ))
                return
            else:
                # transfer worker videos
                try:
                    self.application.queen.fetch_worker_videos()
                except Exception as e:
                    self.clear()
                    self.set_status(500)
                    self.write("failed to transfer worker videos: %s" % (e, ))
        # -- control all workers --
        return

    get = post


class WorkerQuery(tornado.web.RequestHandler):
    def post(self):
        ip = self.request.remote_ip
        args = list(self.request.arguments.keys())
        kwargs = {k: self.get_argument(k) for k in args}
        if (
                'df' in kwargs and
                'state' in kwargs and
                'hostname' in kwargs and
                'datetime' in kwargs):
            # update state of worker
            print("Updating worker state: %s" % (kwargs, ))
            state = {
                'timestamp': time.time(),
                'state': kwargs['state'],
                'df': kwargs['df'],
                'datetime': kwargs['datetime'],
            }
            self.application.queen.update_worker_state(
                kwargs['hostname'], state, ip)
            return
        elif 'new_state' in kwargs and 'hostname' in kwargs:
            print("Changing worker state: %s" % (kwargs, ))
            if kwargs['hostname'] not in self.application.queen.workers:
                self.clear()
                self.set_status(400)
                self.write("unknown hostname: %s" % (kwargs['hostname'], ))
                return
            w = self.application.queen.workers[kwargs['hostname']]
            try:
                w.change_state(kwargs['new_state'])
            except Exception as e:
                self.clear()
                self.set_status(500)
                self.write("failed to change state: %s" % (e, ))
            return
        elif 'hostname' in kwargs and 'transfer_info' in kwargs:
            print("Getting worker transfer_info: %s" % (kwargs, ))
            # get worker state
            if kwargs['hostname'] not in self.application.queen.workers:
                self.clear()
                self.set_status(400)
                self.write("unknown hostname: %s" % (kwargs['hostname'], ))
                return
            w = self.application.queen.workers[kwargs['hostname']]
            d = {
                'transfer_info': w.last_transfer,
                'transfer_duration': w.last_transfer_duration}
            self.write(json.dumps(d))
            return
        elif 'hostname' in kwargs:
            print("Getting worker state: %s" % (kwargs, ))
            # get worker state
            if kwargs['hostname'] not in self.application.queen.workers:
                self.clear()
                self.set_status(400)
                self.write("unknown hostname: %s" % (kwargs['hostname'], ))
                return
            w = self.application.queen.workers[kwargs['hostname']]
            d = {
                'transfer_info': w.last_transfer,
                'transfer_duration': w.last_transfer_duration,
                'state': w.state}
            self.write(json.dumps(d))
            return
        # return dict of all workers and state
        r = {}
        for h in self.application.queen.workers:
            w = self.application.queen.workers[h]
            r[h] = {
                'transfer_info': w.last_transfer,
                'transfer_duration': w.last_transfer_duration,
                'state': w.state}
        self.write(json.dumps(r))
        return
    
    get = post


class QueenApplication(tornado.web.Application):
    def __init__(self, **kwargs):
        self.queen = Queen()
        handlers = [
            (r"/", QueenSite),
            (r"/queen", QueenQuery),
            (r"/worker", WorkerQuery),
            (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": static_path}),
        ]
        settings = kwargs.copy()
        setup_periodic_video_transfer(self.queen)
        super().__init__(handlers, **settings)


if __name__ == '__main__':
    server = tornado.httpserver.HTTPServer(QueenApplication())
    # TODO listen on local IP (and remote?)
    server.listen(8888)
    tornado.ioloop.IOLoop.current().start()
