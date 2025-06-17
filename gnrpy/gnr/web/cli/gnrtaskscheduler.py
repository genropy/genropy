#!/usr/bin/env python
# encoding: utf-8
#

import os.path
import asyncio
from watchfiles import awatch
from multiprocessing import Process
import importlib

from gnr.core.cli import GnrCliArgParse
from gnr.web import gnrtask 
from gnr.web import logger

description = "Start the task scheduler service"

CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "/".join([".."]*3)))

def run_service(options):
    importlib.reload(gnrtask)
    w = gnrtask.GnrTaskScheduler(options.sitename, host=options.host, port=options.port)
    w.start()    

async def autoreload(options):
    process = Process(target=run_service, args=(options,))
    process.start()
    async for changes in awatch(CODE_DIR):
        logger.info("Detected code changes, restarting...")
        process.terminate()
        process.join()
        process = Process(target=run_service, args=(options,))
        process.start()

def main():
    parser = GnrCliArgParse(description=description)
    
    parser.add_argument('sitename')
    parser.add_argument('--host',
                        dest='host')
    parser.add_argument('--port',
                        dest='port')
    parser.add_argument('--autoreload',
                        action='store_true',
                        dest='autoreload')
    
    options = parser.parse_args()
    if options.autoreload:
        asyncio.run(autoreload(options))
    else:
        run_service(options)

if __name__=="__main__":
    main()
