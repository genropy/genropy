#!/usr/bin/env python
# encoding: utf-8

import os

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrtransactiond import GnrAppTransactionAgent

description = "used to apply synced 4d transaction pending"

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('-v', '--verbose',
                        dest='verbose',
                        action='store_true',
                        help="Verbose mode")
    parser.add_argument('-i', '--instance',
                        dest='instance',
                        help="Use command on instance identified by supplied name")
    parser.add_argument('-D', '--directory',
                        dest='directory',
                        help="Use command on instance identified by supplied directory (overrides -i)")
    parser.add_argument('-r', '--rebuild',
                        dest='rebuild',
                        action='store_true',
                        help="Rebuild config_db.xml")
    parser.add_argument('-4', '--4dir',
                        dest='sync4d_name',
                        help="specifies a sync4d folder name")
    parser.add_argument("instance_path", nargs="?",
                        default=os.getcwd(),
                        help="the instance path")
    
    options = parser.parse_args()
    debug = options.debug==True
    app_kwargs=dict(debug=debug)
    app = GnrAppTransactionAgent(options.instance_path)
    app.loop()

if __name__=='__main__':
    main()
