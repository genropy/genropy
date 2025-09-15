#!/usr/bin/env python
# encoding: utf-8
#
import os
from multiprocessing import Process

from gnr.core.cli import GnrCliArgParse
from gnr.web import gnrtask

description = "Start the task worker service"

def run_service(options):
    w = gnrtask.GnrTaskWorker(options.sitename,
                              host=options.host,
                              port=options.port,
                              queue_name=options.queue_name)
    w.start()    

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('sitename')
    parser.add_argument('--host',
                        dest='host')
    parser.add_argument('--port',
                        dest='port')
    parser.add_argument('-p', '--processes',
                        type=int,
                        default=int(os.environ.get("GNR_WORKER_PROCESSES", 1)),
                        dest='processes')
    parser.add_argument('-q', '--queue-name',
                        default=None,
                        dest='queue_name')

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
