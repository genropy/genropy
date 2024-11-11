#!/usr/bin/env python
# encoding: utf-8

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapp import GnrApp

description = "will run a websocket server for <site_name> using tornado."

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument("instance_name", nargs=1)
    parser.add_argument("restorepath", nargs=1)


    options = parser.parse_args()
    instance_name = options.instance_name[0]
    restorepath = options.restorepath[0]
    server=GnrApp(instance_name, restorepath=restorepath)
    
if __name__ == '__main__':
    main()
        
