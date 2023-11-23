#!/usr/bin/env python
# encoding: utf-8
# 
from gnr.web.gnrtask import GnrTaskWorker

import argparse

usage = """
gnrtaskworker sitename """

def getOptions():
    parser = argparse.ArgumentParser(usage)
    parser.add_argument('sitename')
    parser.add_argument('-L', '--loglevel', type=int,
                       help="Log level")
    parser.add_argument('-I', '--interval', type=int,
                       help="Interval")
    parser.add_argument('-C', '--code', help="Code")
    arguments= parser.parse_args()
    return arguments.__dict__

def main():
    options = getOptions()
    sitename = options.pop('sitename')
    code = options.pop('code',None)
    interval = options.pop('interval',None)

    w = GnrTaskWorker(sitename,code=code,interval=interval)
    w.start()
    

if __name__=="__main__":
    main()
