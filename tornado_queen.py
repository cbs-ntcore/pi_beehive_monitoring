#!/usr/bin/env python3

import fcntl
import json
import os
import socket
import struct
import subprocess
import sys
import threading
import time


import tornado
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket


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
    def __init__(self, hostname, state, ip):
        self.state_timestamp = time.time()
        self.hostname = hostname
        self.state = state
        self.ip = ip
        self.number = int(self.hostname.strip('worker').strip('.local'))
        self.stream = None

    def __repr__(self):
        return "%s(%s[%s]: %s)" % (
            self.__class__, self.ip, self.hostname, self.state)

    def update_state(self, state):
        # TODO encapsulate this in a dictionary?
        self.state = state
        self.state_timestamp = time.time()
    
    def setup(self):
        # run setup_worker.sh script on queen
        cmd = 'bash %s %s' % (
            os.path.join(scripts_directory, 'setup_worker.sh'), self.number)
        # TODO use tornado
        subprocess.check_call(cmd.split())
    
    def start_streaming(self):
        if self.stream is not None:
            self.stream.terminate()
        # make subprocess that sshes into pi and runs /home/pi/scripts/stream.sh
        cmd = "ssh pi@%s bash /home/pi/scripts/stream.sh" % (self.ip, )
        # TODO use tornado
        self.stream = subprocess.Popen(cmd.split())
        # receive and display stream
        time.sleep(1.0)  # give time to start stream
        vlc_cmd = 'vlc tcp/h264://%s:2222' % (self.ip, )
        # TODO use tornado
        subprocess.check_call(vlc_cmd.split())

    def run_script(self, name):
        cmd = "ssh pi@%s bash /home/pi/scripts/%s.sh" % (self.ip, name)
        # TODO use tornado
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
        # TODO use tornado
        return subprocess.check_call(cmd.split())


class Queen(object):
    def __init__(self):
        self.workers = {}
        self.last_worker_transfer_time = None
        self.last_worker_transfer_duration = None

    def update_worker_state(self, hostname, state, ip):
        # lookup worker
        if hostname in self.workers:
            worker = self.workers[hostname]
            # update state
            worker.update_state(state)
        else:
            # if not make new one
            worker = Worker(hostname, state, ip)
            worker.setup()
            self.workers[hostname] = worker

    def fetch_worker_videos(self, to_dir, autoremove=False):
        self.last_worker_transfer_time = time.time()
        if not os.path.exists(to_dir):
            os.makedirs(to_dir)
        for w in self.workers:
            d = os.path.join(to_dir, '%i' % w.number)
            w.fetch_videos(d, autoremove)
        self.last_worker_transfer_duration = (
            time.time() - self.last_worker_transfer_time)

    def get_space_in_directory(self, directory):
        # df -h directory | tail -n 1 | awk '{print $2,$3,$5}
        pass



class QueenSite(tornado.web.RequestHandler):
    def get(self):
        # self.application.queen
        # return list of workers and states
        print(self.request.uri)
        s = "Workers:\n"
        s += "\n".join([str(w) for w in self.application.queen.workers])
        s += "\n"
        self.write(s)

    def post(self):
        # TODO state update:  TODO add df
        # curl
        #  -d "hostname=`hostname`&state=`cat /home/pi/state`"
        #  -X POST http://queen.local:8888/
        # TODO state change
        # TODO configure
        hostname = self.get_argument('hostname')
        state = self.get_argument('state')
        #df = self.get_argument('df')
        # other?
        # register new worker
        self.application.queen.update_worker_state(
            hostname, state, self.request.remote_ip)


class QueenWebSocket(tornado.websocket.WebSocketHandler):
    def on_message(self, message):
        # self.application.queen
        return


class QueenApplication(tornado.web.Application):
    def __init__(self, **kwargs):
        self.queen = Queen()
        handlers = [
            (r"/", QueenSite),
            (r"/ws", QueenWebSocket),
        ]
        settings = kwargs.copy()
        super().__init__(handlers, **settings)


if __name__ == '__main__':
    server = tornado.httpserver.HTTPServer(QueenApplication())
    # listen on local IP
    server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
