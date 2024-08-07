#!/usr/bin/env python
# encoding: utf-8

from gnr.core.cli import GnrCliArgParse
from gnr.core.gnrremotebag import RemoteBagServer
from gnr.core.gnrbag import Bag
from gnr.core.gnrsys import expandpath

description = ""

def getOptions():
    parser = GnrCliArgParse(description=description)
    
    parser.add_argument('-n', '--name',
                      help="The name of the configured server")

                          
    parser.add_argument('-H', '--host',
                      help="The binded host")
                      
    parser.add_argument('-P', '--port',
                      help="The binded port" ,type=int)
                      
    parser.add_argument('-K', '--hmac_key',
                      help="The secret key")
                      
    parser.add_argument('-t', '--timeout',type=float,
                      help="Timeout")

    parser.add_argument('-m', '--multiplex',action='store_false',
                      help="Use multiplexed server")
                      
    parser.add_argument('--polltimeout',type=float,
                      help="Use multiplexed server poll timeout")

    parser.add_argument('-d', '--debug',
                      action='store_false',
                      help="Debug mode")
                      
    parser.add_argument('-c', '--compression',
                      action='store_false',
                      help="Enable compression")

    arguments= parser.parse_args()
    return arguments.__dict__
    
    
def main():
    options=getOptions()
    name=options.pop('name',None)
    if name:
        sharedstores = Bag(expandpath('~/.gnr/environment.xml'))['sharedstores']
        assert sharedstores, 'Missing sharedstores configuration.'
        sharedstoreconfig=sharedstores.getNode(name)
        assert sharedstoreconfig,"Miissing sharedstore '%s' configuration."% name
        curropt=options
        print('curopt',curropt)
        options=sharedstoreconfig.attr
        print('conf options',options)
        options.update(curropt)
        print('final options',options)
    server =RemoteBagServer()
    server.start(**options)
    
if __name__=="__main__":
    main()
