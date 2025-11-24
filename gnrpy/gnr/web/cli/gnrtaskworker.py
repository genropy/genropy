#!/usr/bin/env python
# encoding: utf-8
#
import os
import asyncio

from gnr.core.cli import GnrCliArgParse
from gnr.web import gnrtask
from gnr.web import logger

GRACE_SECONDS = 8
ESCALATE_SECONDS = 3

description = "Start the task worker service"

def start_old(options):
    w = gnrtask.GnrTaskWorker(sitename=options.sitename, interval=options.interval)
    logger.info("Starting Task Worker for site: %s", options.sitename)
    w.start()

def start_new(options):
    from gnr.web import gnrtask_new
    async def r():
        worker = gnrtask_new.GnrTaskWorker(
            options.sitename,
            queue_name=options.queue_name,
            processes=options.processes
        )
        await worker.start()

    asyncio.run(r())


def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument("sitename")
    if gnrtask.USE_ASYNC_TASKS:
        parser.add_argument(
            "-p",
            "--processes",
            type=int,
            default=int(os.environ.get("GNR_WORKER_PROCESSES", 1)),
            dest="processes",
        )
        parser.add_argument(
            "-q",
            "--queue-name",
            nargs="?",
            default=None,
            dest="queue_name",
        )
    else:
        parser.add_argument('-I', '--interval', type=int,
                            help="Interval")
        parser.add_argument('-C', '--code', help="Code")
        
    options = parser.parse_args()

    if gnrtask.USE_ASYNC_TASKS:
        start_new(options)
    else:
        start_old(options)
        

if __name__ == "__main__":
    main()
