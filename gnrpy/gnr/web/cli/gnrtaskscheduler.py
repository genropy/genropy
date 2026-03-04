#!/usr/bin/env python
# encoding: utf-8
#
import sys
import os.path
import asyncio
from watchgod import awatch
from multiprocessing import Process
import importlib

from gnr.core.cli import GnrCliArgParse
from gnr.web import gnrtask 
from gnr.web import logger

description = "Start the task scheduler service"

CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "/".join([".."]*3)))

def run_service(options):
    from gnr.web import gnrtask_new
    importlib.reload(gnrtask_new)
    w = gnrtask_new.GnrTaskScheduler(options.sitename, host=options.host, port=options.port)
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

def start_old(options):
    """
    start the old database-polling task scheduler
    """
    w = gnrtask.GnrTaskScheduler(options.sitename, interval=None)
    logger.info("Starting Database-polling task scheduler for site: %s", options.sitename)
    w.start()

def start_new(options):
    """
    start the new asyncio based task scheduler
    """
    if options.autoreload:
        asyncio.run(autoreload(options))
    else:
        run_service(options)
        
def main():
    parser = GnrCliArgParse(description=description)
    
    parser.add_argument('sitename')

    if gnrtask.USE_ASYNC_TASKS:
        parser.add_argument('--host',
                            dest='host')
        parser.add_argument('--port',
                            dest='port')
        parser.add_argument('--autoreload',
                            action='store_true',
                            dest='autoreload')
        
    options = parser.parse_args()
    if gnrtask.USE_ASYNC_TASKS:
        start_new(options)
    else:
        print("This tool is currently disabled")
        sys.exit(1)
        
if __name__=="__main__":
    main()
