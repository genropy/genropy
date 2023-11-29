#!/usr/bin/env python
# encoding: utf-8
import sys, os

from gnr.core.cli import GnrCliArgParse
from gnr.web.gnrasync import GnrAsyncServer
from gnr.core.gnrsys import expandpath
from gnr.app.gnrconfig import gnrConfigPath,getSiteHandler,getGnrConfig

description = "will run a websocket server for <site_name> using tornado."

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('-p', '--port',
                  dest='port',
                  help="Listen port")     
    parser.add_argument('-c', '--crt',
                  dest='ssl_crt',
                  help="SSL Certificate path")        
    parser.add_argument('-k', '--key',
                  dest='ssl_key',
                  help="SSL key path")    
    parser.add_argument("instance_name", nargs=1)


    options = parser.parse_args()
    instance_name = options.instance_name[0]
    
    server=GnrAsyncServer(port=options.port,
                          instance=instance_name,
                          ssl_crt=options.ssl_crt,
                          ssl_key=options.ssl_key)
    server.start()

if __name__ == '__main__':
    main()
        
