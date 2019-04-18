#!/usr/bin/env python

import fcntl
import json
import os
import socket
import struct
import subprocess
import sys
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
            return
        # make subprocess that sshes into pi and runs /home/pi/scripts/stream.sh
        cmd = "ssh pi@%s bash /home/pi/scripts/stream.sh" % (self.ip, )
        self.stream = subprocess.Popen(cmd.split())
        # receive and display stream
        time.sleep(1.0)  # give time to start stream
        vlc_cmd = 'vlc tcp/h264://%s:2222' % (self.ip, )
        subprocess.check_call(vlc_cmd.split())
    
    def stop_streaming(self):
        if self.stream is not None:
            self.stream.terminate()

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
                print("Updated worker state: %s" % (w, ))
                return w
        print("Adding new worker %s:%s" % (ip, port))
        self.workers.append(Worker(conn, ip, port))
        conn.close()
        print("New worker state: %s" % (self.workers[-1].state, ))

        print("Copying scripts to worker...")
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
        for w in self.workers:
            w.fetch_videos(to_dir, autoremove)


if __name__ == '__main__':
    queen = Queen()
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
