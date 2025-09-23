#!/usr/bin/env python
# encoding: utf-8
#
import os
import asyncio

from gnr.core.cli import GnrCliArgParse
from gnr.web import gnrtask

GRACE_SECONDS = 8
ESCALATE_SECONDS = 3

description = "Start the task worker service"

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument("sitename")
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
    options = parser.parse_args()
    async def r():
        worker = gnrtask.GnrTaskWorker(
            options.sitename,
            queue_name=options.queue_name,
            processes=options.processes
        )
        await worker.start()

    asyncio.run(r())

    

if __name__ == "__main__":
    main()
