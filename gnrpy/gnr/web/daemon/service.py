import os
from gnr.core.gnrbag import Bag
from gnr.app.gnrdeploy import PathResolver
from gnr.web.daemon.handler import GnrDaemon, GnrDaemonProxy
from gnr.web.gnrwsgisite_proxy.gnrsiteregister import GnrSiteRegisterServer


class DaemonService(object):
    """ Commodity class to control the service """
    
    def __init__(self, options, command=None, sitename=None):
        self.options = options
        self.command = command
        self.sitename = sitename
        
    def run(self):
        if self.command == 'start' or not self.command:
            if self.sitename:
                path_resolver = PathResolver()
                siteconfig = path_resolver.get_siteconfig(self.sitename)
                daemonconfig = siteconfig.getAttr('gnrdaemon')
                sitedaemonconfig = siteconfig.getAttr('sitedaemon') or {}
                sitepath = path_resolver.site_name_to_path(self.sitename)
                debug = sitedaemonconfig.get('debug',None)
                host = self.options.get('host', sitedaemonconfig.get('host','localhost'))
                socket = sitedaemonconfig.get('socket',None)
                port = self.options.get('port', sitedaemonconfig.get('port','*'))
                hmac_key = sitedaemonconfig.get('hmac_key') or daemonconfig['hmac_key']
                storage_path = os.path.join(sitepath, 'siteregister_data.pik')
                sitedaemon = GnrSiteRegisterServer(sitename=self.sitename, debug=debug,
                                                   storage_path=storage_path)
                sitedaemon.start(host=host, socket=socket, hmac_key=hmac_key, port=port, run_now=False)
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
                server.start(use_environment=True,**self.options)
        else:
            p = GnrDaemonProxy(use_environment=True, host=self.options.get('host'),
                               port=self.options.get('port'), socket=self.options.get('socket'),
                               hmac_key=self.options.get('hmac_key'),
                               compression=self.options.get('compression'))
            proxy = p.proxy()
            if self.command=='stop':
                print('savestatus',self.options.get('savestatus'))
                result = proxy.stop(saveStatus=self.options.get('savestatus'))
                print(result)
            elif self.command =='restart':
                result = proxy.restart(sitename='*')
            elif self.command in ('stopping','starting'):
                result = getattr(proxy, self.command)()
                print(result)
            else:
                h = getattr(proxy, self.command, None)
                if h:
                    print(h(**self.options))
                else:
                    print(f'unknown command: {self.command}')

        
