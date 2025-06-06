#!/usr/bin/env python
# encoding: utf-8
# 
from gnr.web import gnrtask
from gnr.core.cli import GnrCliArgParse

description = "Start the task worker service"

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('sitename')
    parser.add_argument('--host',
                        dest='host')
    parser.add_argument('--port',
                        dest='port')

    options = parser.parse_args()
    w = gnrtask.GnrTaskWorker(options.sitename,
                              options.host,
                              options.port)
    w.start()

if __name__=="__main__":
    main()
