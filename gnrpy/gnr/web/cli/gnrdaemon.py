#!/usr/bin/env python
# encoding: utf-8
import sys
import logging
from gnr.core.cli import GnrCliArgParse

from gnr.web.gnrdaemonhandler import GnrDaemon,GnrDaemonProxy

description = "Main Genropy Daemon for request handling"
def getOptions():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('sitename',nargs='?')
    parser.add_argument('-C', '--command',
                    help="Command")
    parser.add_argument('-H', '--host',
                    help="The binded host")

    parser.add_argument('-P', '--port',
                    help="The binded port" ,type=int)

    parser.add_argument('-S', '--socket',
                    help="socket to use")

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

    parser.add_argument('-s', '--savestatus',
                    action='store_true',
                    help="Save status")

    parser.add_argument('-n', '--sitename',
                    help="Sitename")

    parser.add_argument('-l', '--size_limit', type=int,
                    help="Size limit")

    # set default to logging.FATAL
    parser.add_argument('-L', '--loglevel', type=int, default=logging.FATAL,
                    help="Log level")
    arguments= parser.parse_args()

    return arguments.__dict__

def main():
    options = getOptions()
    command = options.pop('command',None)
    sitename = options.pop('sitename',None)
    logging.basicConfig(level=options.get("loglevel"))
    logging.getLogger("Pyro5").setLevel(options.get("loglevel"))

    if command == 'start' or not command:
        if sitename:
            from gnr.web.gnrwsgisite_proxy.gnrsiteregister import GnrSiteRegisterServer
            from gnr.app.gnrdeploy import PathResolver
            import os
            from gnr.core.gnrbag import Bag
            path_resolver = PathResolver()
            siteconfig = path_resolver.get_siteconfig(sitename)
            daemonconfig = siteconfig.getAttr('gnrdaemon')
            sitedaemonconfig = siteconfig.getAttr('sitedaemon') or {}
            sitepath = path_resolver.site_name_to_path(sitename)
            debug = sitedaemonconfig.get('debug',None)
            host = sitedaemonconfig.get('host','localhost')
            socket = sitedaemonconfig.get('socket',None)
            port = sitedaemonconfig.get('port','*')
            storage_path = os.path.join(sitepath, 'siteregister_data.pik')
            sitedaemon = GnrSiteRegisterServer(sitename=sitename,debug=debug, storage_path=storage_path)
            sitedaemon.start(host=host,socket=socket,port=port, run_now=False)
            sitedaemon_xml_path = os.path.join(sitepath,'sitedaemon.xml')
            sitedaemon_bag = Bag()
            sitedaemon_bag.setItem('params',None,
                        register_uri=sitedaemon.register_uri,
                        main_uri = sitedaemon.main_uri,
                        pid=os.getpid()
                )
            sitedaemon_bag.toXml(sitedaemon_xml_path)
            sitedaemon.run()
        else:
            server = GnrDaemon()
            server.start(use_environment=True,**options)
    else:
        p = GnrDaemonProxy(use_environment=True, host=options.get('host'),port=options.get('port'),socket=options.get('socket'),compression=options.get('compression'))
        proxy = p.proxy()
        if command=='stop':
            print('savestatus',options.get('savestatus'))
            result = proxy.stop(saveStatus=options.get('savestatus'))
            print(result)
        elif command =='restart':
            result = proxy.restart(sitename='*')
        elif command in ('stopping','starting'):
            result = getattr(proxy,command)()
            print(result)
        else:
            h = getattr(proxy,command,None)
            if h:
                print(h(**options))
            else:
                print('unknown command:%s' %command)

if __name__=="__main__":
    main()
