#!/usr/bin/env python
# encoding: utf-8
#

import os.path
from multiprocessing import Process
import importlib

from gnr.core.cli import GnrCliArgParse
from gnr.web import gnrtask
from gnr.web import logger

description = "Start the task worker service"

def run_service(options):
    w = gnrtask.GnrTaskWorker(options.sitename,
                              host=options.host,
                              port=options.port)
    w.start()    

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('sitename')
    parser.add_argument('--host',
                        dest='host')
    parser.add_argument('--port',
                        dest='port')
    parser.add_argument('--processes',
                        type=int,
                        default=1,
                        dest='processes')

    processes = []
    options = parser.parse_args()

    for _ in range(options.processes):
        p = Process(target=run_service, args=(options,))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()

if __name__=="__main__":
    main()
