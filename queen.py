#!/usr/bin/env python

import fcntl
import json
import os
import socket
import struct
import subprocess
import sys
import threading
import time


def get_ip_address(ifname='eth0'):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(), 0x8915,
        struct.pack('256s', bytes(ifname[:15], 'utf-8')))[20:24])


# setup stream command with this ip
queen_port = 5005
if len(sys.argv) == 1:
    queen_ip = get_ip_address()
else:
    queen_ip = sys.argv[1]

scripts_directory = '/home/pi/scripts'


class Worker:
    def __init__(self, conn, ip, port):
        self.ip = ip
        
        self.port = port
        # set initial state to unknown
        self.state = None
        self.state_timestamp = None
        self.hostname = None
        self.number = None
        # read state
        self.receive_state(conn)
        self.stream = None

    def __repr__(self):
        return "%s(%s[%s], %s, %s)" % (
            self.__class__, self.ip, self.hostname, self.port, self.state)
    
    def receive_state(self, conn):
        """ at the moment this is only 1 character
        this should probably contain the hostname"""
        try:
            data = conn.recv(2048)
            if not data: return -1
            msg = json.loads(data.decode('utf-8'))
            self.hostname = msg['hostname']
            self.state = msg['state']
            self.state_timestamp = time.time()
        except socket.timeout:
            return
        except:
            raise
        # parse number from hostname
        self.number = int(self.hostname.strip('worker').strip('.local'))
        return self.state

    def setup(self):
        # run setup_worker.sh script on queen
        cmd = 'bash %s %s' % (
            os.path.join(scripts_directory, 'setup_worker.sh'), self.number)
        subprocess.check_call(cmd.split())
    
    def start_streaming(self):
        if self.stream is not None:
            self.stream.terminate()
        # make subprocess that sshes into pi and runs /home/pi/scripts/stream.sh
        cmd = "ssh pi@%s bash /home/pi/scripts/stream.sh" % (self.ip, )
        self.stream = subprocess.Popen(cmd.split())
        # receive and display stream
        time.sleep(1.0)  # give time to start stream
        vlc_cmd = 'vlc tcp/h264://%s:2222' % (self.ip, )
        subprocess.check_call(vlc_cmd.split())

    def run_script(self, name):
        cmd = "ssh pi@%s bash /home/pi/scripts/%s.sh" % (self.ip, name)
        return subprocess.check_call(cmd.split())

    def start_recording(self):
        self.run_script("start_recording")
    
    def stop_recording(self):
        self.run_script("stop_recording")

    def fetch_videos(self, to_dir, autoremove=False):
        # rsync videos from worker to queen directory to_dir
        # delete from worker after transfer
        cmd = 'rsync '
        if autoremove:
            cmd += '--remove-source-files '
        cmd += '-rtuv %s:/home/pi/videos/ %s' % (self.ip, to_dir.rstrip('/'))
        return subprocess.check_call(cmd.split())


class Queen:
    def __init__(self, ip=queen_ip, port=queen_port):
        self.workers = []
        self.ip = ip
        self.port = port
        self.connect()
    
    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.ip, self.port))
        self.wait_for_worker()
    
    def add_worker(self, conn, ip, port):
        for w in self.workers:
            if w.ip == ip:
                w.receive_state(conn)
                conn.close()
                #print("Updated worker state: %s" % (w, ))
                return w
        print("Adding new worker %s:%s" % (ip, port))
        self.workers.append(Worker(conn, ip, port))
        conn.close()
        #print("New worker state: %s" % (self.workers[-1].state, ))

        #print("Copying scripts to worker...")
        # setup worker again (to copy over scripts)
        self.workers[-1].setup()
        return self.workers[-1]
    
    def wait_for_worker(self):
        try:
            self.sock.settimeout(0.1)
            self.sock.listen()
            (conn, (ip, port)) = self.sock.accept()
        except socket.timeout:
            return
        except:
            raise
        else:
            return self.add_worker(conn, ip, port)
    
    def update(self):
        w = 1
        while w is not None:
            w = self.wait_for_worker()
        return

    def fetch_worker_videos(self, to_dir, autoremove=False):
        if not os.path.exists(to_dir):
            os.makedirs(to_dir)
        for w in self.workers:
            d = os.path.join(to_dir, '%i' % w.number)
            w.fetch_videos(d, autoremove)


class QueenThread(threading.Thread):
    def __init__(self, queen, update_delay=1.0, fetch_delay=30.0):
        super(QueenThread, self).__init__()
        self.daemon = True
        self.queen = queen
        self.lock = threading.Lock()
        self._stop_update = False
        self._update_delay = update_delay
        self._fetch_delay = fetch_delay
        self._last_fetch = time.time() - self._fetch_delay
    
    def stop(self):
        with self.lock:
            self._stop_update = True
        self.join()
    
    def run(self):
        while True:
            time.sleep(self._update_delay)
            with self.lock:
                if self._stop_update:
                    break
                self.queen.update()
                # fetch videos every N seconds
                if (time.time() - self._last_fetch) >= self._fetch_delay:
                    self.queen.fetch_worker_videos('/home/pi/videos/')
                    self._last_fetch = time.time()


def worker_from_line(l, queen):
    ts = l.split()
    if len(ts) < 2:
        return None
    t = ts[1]
    try:
        i = int(t)
    except ValueError:
        return None
    for w in queen.workers:
        if i == w.number:
            return w
    return None

    
def print_cmd_line_help():
    print("Available commands...")
    print("  for any command with a [N] replace with the worker number")
    print("c [N]: configure/setup worker number N (example: c 3)")
    print("h: help")
    print("q: quit, destroy queen, shut down program")
    print("r [N]: toggle recording (start if idle, stop if recording)")
    print("s: get status of all workers")
    print("S [N]: start streaming from worker, display in vlc")


def run_cmd_line(queen):
    # start queen thread: runs update in background, use lock for sync
    queen_thread = QueenThread(queen)
    queen_thread.start()
    while True:
        # look for user input
        i = input(">>> ").strip()
        # if user input requires queen, sync and use
        if len(i) == 0:
            continue
        elif i[0] == 'c':  # configure
            w = worker_from_line(i, queen)
            if w is None:
                print("Invalid worker number: %s" % (i.strip()))
                continue
            with queen_thread.lock:
                w.setup()
        elif i[0] in 'h?H':  # help
            print_cmd_line_help()
        elif i[0] == 'q':  # quit
            queen_thread.stop()
            break
        elif i[0] == 'r':  # toggle recording
            w = worker_from_line(i, queen)
            if w is None:
                print("Invalid worker number: %s" % (i.strip()))
                continue
            # if worker is idle start recording
            with queen_thread.lock:
                if w.state == 'idle':
                    print("Worker %s start_recording" % (w, ))
                    w.start_recording()
                elif w.state == 'recording':
                    print("Worker %s stop_recording" % (w, ))
                    w.stop_recording()
        elif i[0] == 's':  # status
            # print worker states
            workers = sorted(queen.workers, key=lambda w: w.number)
            for w in workers:
                ts = time.strftime(
                    '%Y-%m-%d %H:%M:%S', time.localtime(w.state_timestamp))
                print("Worker %i [%s @ %s]" % (w.number, w.state, ts))
        elif i[0] == 'S':  # stream
            w = worker_from_line(i, queen)
            if w is None:
                print("Invalid worker number: %s" % (i.strip()))
                continue
            with queen_thread.lock:
                if w.state != 'idle':
                    print(
                        "Worker %s is not idle, cannot start streaming" % (w, ))
                    continue
                w.start_streaming()


if __name__ == '__main__':
    queen = Queen()
    run_cmd_line(queen)
    print("Waiting for workers")
    print("Listening on: %s:%s" % (queen.ip, queen.port))
    t0 = time.time()
    while True:
        try:
            w = queen.wait_for_worker()
            if w is not None:
                print("N workers: %i" % (len(queen.workers), ))
            if (time.time() - t0) > 30:
                print("Fetching worker videos")
                t0 = time.time()
                queen.fetch_worker_videos('/home/pi/videos/')
            # TODO look for input to command workers to record etc
        except KeyboardInterrupt:
            break
