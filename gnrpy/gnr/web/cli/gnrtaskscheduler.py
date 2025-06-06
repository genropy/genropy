#!/usr/bin/env python
# encoding: utf-8
#

from gnr.core.cli import GnrCliArgParse
from gnr.web import gnrtask 

description = "Start the task scheduler service"

def main():
    parser = GnrCliArgParse(description=description)
    
    parser.add_argument('sitename')
    parser.add_argument('--host',
                        dest='host')
    parser.add_argument('--port',
                        dest='port')

    options = parser.parse_args()
    w = gnrtask.GnrTaskScheduler(options.sitename, host=options.host, port=options.port)
    w.start()    

if __name__=="__main__":
    main()
