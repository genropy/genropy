#!/usr/bin/env python
# encoding: utf-8
# 
from gnr.core.cli import GnrCliArgParse
from gnr.web.gnrtask import GnrTaskScheduler
from gnr.web import logger

description = "Start the task scheduler service"

def getOptions():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('sitename')
    arguments= parser.parse_args()
    return arguments.__dict__

def main():
    options = getOptions()
    sitename = options.pop('sitename')
    interval = options.pop('interval',None)
    w = GnrTaskScheduler(sitename,interval=interval)
    logger.info("Starting Task Scheduler for site: %s", sitename)
    w.start()    

if __name__=="__main__":
    main()
