#!/usr/bin/env python

import subprocess

import tornado.ioloop
import tornado.process


def call_subprocess():
    cmd = "df -h"
    sp = tornado.process.Subprocess(
        cmd.split(),
        stdout=subprocess.PIPE)
    f = sp.wait_for_exit()
    loop = tornado.ioloop.IOLoop.current()

    def command_done(f, p=sp):
        print("Command finished: %s" % f)
        print(p.stdout.read().decode('latin8'))
        loop = tornado.ioloop.IOLoop.current()
        loop.stop()

    loop.add_future(f, command_done)


if __name__ == '__main__':
    loop = tornado.ioloop.IOLoop.current()
    loop.add_callback(call_subprocess)
    loop.start()
