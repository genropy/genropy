#!/usr/bin/env python
# encoding: utf-8
#

from datetime import datetime
import logging
from multiprocessing import Process, log_to_stderr, get_logger, Manager
import ipaddress
import atexit
import os
import time
from Pyro5.compatibility import Pyro4
from Pyro5.server import expose

from gnr.web.gnrwsgisite_proxy.gnrsiteregister import GnrSiteRegisterServer
from gnr.core.gnrlang import gnrImport
from gnr.core.gnrbag import Bag,NetBag
from gnr.core.gnrsys import expandpath
from gnr.app.gnrconfig import gnrConfigPath
from gnr.app.gnrdeploy import PathResolver
from gnr.core.gnrstring import boolean
from gnr.core.gnrlog import log_styles
from gnr.web.gnrdaemonprocesses import GnrCronHandler, GnrDaemonServiceManager
from gnr.web.gnrtask import GnrTaskScheduler

if hasattr(Pyro4.config, 'METADATA'):
    Pyro4.config.METADATA = False
    
PYRO_HOST = 'localhost'
PYRO_PORT = 40004

def createSiteRegister(sitename=None,daemon_uri=None,host=None, socket=None,
                         storage_path=None,debug=None,autorestore=False,
                         port=None):
    server = GnrSiteRegisterServer(sitename=sitename,daemon_uri=daemon_uri,
        storage_path=storage_path,debug=debug)
    server.start(host=host,socket=socket,port=port or '*',autorestore=autorestore)

def createHeartBeat(site_url=None,interval=None,**kwargs):
    server = GnrHeartBeat(site_url=site_url,interval=interval,**kwargs)
    time.sleep(interval)
    server.start()

def createTaskScheduler(sitename,interval=None):
    scheduler = GnrTaskScheduler(sitename,interval=interval)
    scheduler.start()

def getFullOptions(options=None):
    gnr_path = gnrConfigPath()
    enviroment_path = os.path.join(gnr_path,'environment.xml')
    env_options = Bag(expandpath(enviroment_path)).getAttr('gnrdaemon')
    if env_options.get('sockets'):
        if env_options['sockets'].lower() in ('t','true','y') :
            env_options['sockets']=os.path.join(gnr_path,'sockets')
        if not os.path.isdir(env_options['sockets']):
            os.makedirs(env_options['sockets'])
        env_options['socket']=env_options.get('socket') or os.path.join(env_options['sockets'],'gnrdaemon.sock')
    assert env_options,"Missing gnrdaemon configuration."
    for k,v in list(options.items()):
        if v:
            env_options[k] = v
    return env_options

class GnrHeartBeat(object):
    def __init__(self,site_url=None,interval=None,loglevel=None,**kwargs):
        self.interval = interval
        self.site_url = site_url
        self.url = "%s/sys/heartbeat"%self.site_url
        self.logger = get_logger()
        
    def start(self):
        os.environ['no_proxy'] = '*'
        import urllib.request, urllib.parse, urllib.error
        while True:
            try:
                self.logger.info("Calling {}".format(self.url))
                response = urllib.request.urlopen(self.url)
                response_code = response.getcode()

                if response_code!=200:
                    self.retry('WRONG CODE %i' %response_code)
                else:
                    time.sleep(self.interval)
            except IOError:
                self.retry('IOError')
            except Exception as e:
                self.logger.error(str(e))


    def retry(self,reason):
        self.logger.warn('%s -> will retry in %i seconds' %(reason,3*self.interval))
        time.sleep(3*self.interval)

def ip_is_loopback(host):
    if host == 'localhost':
        return True
    try:
        return ipaddress.IPv4Address(host).is_loopback
    except:
        return ipaddress.IPv6Address(host).is_loopback

        
class GnrDaemonProxy(object):
    def __init__(self,host=None,port=None, socket=None,compression=True,use_environment=False,serializer='pickle'):
        options=dict(host=host, socket=socket, port=port,compression=compression)
        if use_environment:
            options = getFullOptions(options=options)
        Pyro4.config.SERIALIZER = options.get('serializer','pickle')
        Pyro4.config.COMPRESSION = options.get('compression',True)

        if options.get('socket'):
            self.uri='PYRO:GnrDaemon@./u:%s' % options.get('socket')
        else:
            self.uri = 'PYRO:GnrDaemon@%s:%s' %(options.get('host') or PYRO_HOST,options.get('port') or PYRO_PORT)


    def proxy(self):
        proxy = Pyro4.Proxy(self.uri)
        return proxy

class GnrDaemon(object):
    def __init__(self):
        self.running = False
        self.siteregisters= dict()
        self.siteregisters_process = dict()
        self.sshtunnel_index = dict()
        self.multiprocessing_manager =  Manager()
        self.batch_processes = dict()
        self.cron_processes = dict()
        self.task_locks = dict()
        self.task_execution_dicts = dict()
        self.logger = log_to_stderr()

    def start(self,use_environment=False,**kwargs):
        if use_environment:
            options =  getFullOptions(options=kwargs)
        self.do_start(**options)

    def do_start(self, host=None, port=None, socket=None,
                      debug=False,compression=False,timeout=None,
                      multiplex=False,polltimeout=None,use_environment=False, size_limit=None,
                      sockets=None, loglevel=None, **kwargs):
        self.loglevel = loglevel or logging.ERROR
        self.logger.setLevel(self.loglevel)
        
        self.pyroConfig(host=host,port=port, socket=socket,debug=debug,
                        compression=compression,timeout=timeout,
                        multiplex=multiplex,polltimeout=polltimeout, size_limit=size_limit,
                        sockets=sockets)
        if self.socket:
            self.logger.info('Start daemon new socket {}'.format(self.socket))
            self.daemon = Pyro4.Daemon(unixsocket=self.socket)
        else:
            # FIXME: since Pyro5 can use only SSL with 2-way certificate for security
            # we've disabled listening of the daemon outside of loopback
            if not ip_is_loopback(self.host):
                raise NotImplementedError("Can't listen outside of loopback, please enquiry with Genropy team")
            
            self.logger.info(f"Starting daemon on {self.host}:{self.port}")
            self.daemon = Pyro4.Daemon(host=self.host,port=int(self.port))
            
        self.main_uri = self.daemon.register(self,'GnrDaemon')
        self.logger.info("uri={}".format(self.main_uri))
        print('{color_blue}Daemon is running{nostyle}'.format(**log_styles()))
        self.running = True
        atexit.register(self.stop)
        self.daemon.requestLoop(lambda : self.running)

    def pyroConfig(self,host=None,port=None, socket=None,
                   debug=False,compression=False,timeout=None,
                   multiplex=False,polltimeout=None, size_limit=None,sockets=None):
        #Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
        self.port=port or PYRO_PORT
        self.host = host or PYRO_HOST
        self.socket = socket
        self.sockets = sockets
        if compression:
            Pyro4.config.COMPRESSION = True
        if multiplex:
            Pyro4.config.SERVERTYPE = "multiplex"
        if timeout:
            Pyro4.config.TIMEOUT = timeout
        if polltimeout:
            Pyro4.config.POLLTIMEOUT = timeout
        if size_limit:
            Pyro4.config.SIZE_LIMIT = size_limit

    @expose
    def onRegisterStart(self,sitename,server_uri=None,register_uri=None):
        self.siteregisters[sitename]['server_uri'] = server_uri
        self.siteregisters[sitename]['register_uri'] = register_uri
        self.siteregisters[sitename]['register_port'] = int(register_uri.split(':')[-1])
        print('registered ',sitename,server_uri)

    @expose
    def onRegisterStop(self,sitename=None):
        print('onRegisterStop',sitename)
        self.siteregisters.pop(sitename,None)
        process_dict = self.siteregisters_process.pop(sitename,None) or {}
        for name, process in list(process_dict.items()):
            if name!='register' and process and process.is_alive():
                process.terminate()

    @expose
    def ping(self,**kwargs):
        return 'ping'

    @expose
    def getSite(self,sitename=None,create=False,storage_path=None,autorestore=None,**kwargs):
        if sitename in self.siteregisters and self.siteregisters[sitename]['server_uri']:
            return self.siteregisters[sitename]
        elif create:
            self.addSiteRegister(sitename,storage_path=storage_path,autorestore=autorestore)
            return dict()

    @expose
    def stop(self,saveStatus=False,**kwargs):
        self.daemon.close()
        self.siteregister_stop('*',saveStatus=saveStatus)
        for t in list(self.sshtunnel_index.values()):
            t.stop()
        self.running = False

    @expose
    def restart(self, sitename=None, **kwargs):
        self.stop(saveStatus=True)

    @expose
    def restartServiceDaemon(self,sitename=None,service_name=None):
        sitedict = self.siteregisters_process[sitename]
        if service_name in sitedict:
            proc = sitedict[service_name]
            proc.terminate()
            sitedict[service_name] = self.startServiceDaemon(sitename, service_name=service_name)

    def on_reloader_restart(self, sitename=None):
        pass

    @expose
    def startCronProcess(self, sitename=None, batch_pars=None, batch_queue=None):
        siteregister_processes_dict = self.siteregisters_process[sitename]
        cron_handler = GnrCronHandler(self, sitename=sitename, batch_queue=batch_queue,
            batch_pars=batch_pars)
        cron_handler.start()
        siteregister_processes_dict['cron'] = cron_handler


    def startGnrDaemonServiceManager(self, sitename, sitedict=None):
        siteregister_processes_dict = self.siteregisters_process[sitename]
        daemonServiceHandler = GnrDaemonServiceManager(self, sitename=sitename)
        daemonServiceHandler.start()
        siteregister_processes_dict['services'] = daemonServiceHandler
        

    def startServiceProcesses(self, sitename, sitedict=None):
        siteregister_processes_dict = self.siteregisters_process[sitename]
        p = PathResolver()
        siteconfig = p.get_siteconfig(sitename)
        services = siteconfig['services']
        if not services:
            return
        for serv in services:
            if serv.attr.get('daemon'):
                service_process = self.startServiceDaemon(sitename,serv.label)
                siteregister_processes_dict[serv.label] = service_process

    def startServiceDaemon(self,sitename, service_name=None):
        p = PathResolver()
        siteconfig = p.get_siteconfig(sitename)
        services = siteconfig['services']
        service_attr = services.getAttr(service_name)
        pkg, pathlib = service_attr['daemon'].split(':')
        p = os.path.join(p.package_name_to_path(pkg), 'lib', '%s.py' % pathlib)
        m = gnrImport(p)
        service_attr.update({'sitename': sitename})
        proc = Process(name='service_daemon_%s_%s' %(sitename, service_name),
                        target=getattr(m, 'run'), kwargs=service_attr)
        proc.daemon = True
        proc.start()
        return proc
    
    def hasSysPackageAndIsPrimary(self,sitename):
        instanceconfig = PathResolver().get_instanceconfig(sitename)
        if instanceconfig:
            has_sys = 'gnrcore:sys' in instanceconfig['packages']
            secondary = has_sys and instanceconfig['packages'].getAttr('gnrcore:sys').get('secondary')
            return has_sys and not secondary
        return False

    @expose
    def addSiteRegister(self,sitename,storage_path=None,autorestore=False,port=None):
        if not sitename in self.siteregisters:
            siteregister_processes_dict = dict()
            self.siteregisters_process[sitename] = siteregister_processes_dict
            siteregister_dict = dict()
            self.siteregisters[sitename] = siteregister_dict
            socket = os.path.join(self.sockets,'%s_daemon.sock' %sitename) if self.sockets else None
            process_kwargs = dict(sitename=sitename,daemon_uri=self.main_uri,host=self.host,socket=socket,
                                  storage_path=storage_path,autorestore=autorestore,
                                  port=port)
            childprocess = Process(name='sr_%s' %sitename, target=createSiteRegister,kwargs=process_kwargs)
            siteregister_dict.update(sitename=sitename,server_uri=False,
                                     register_uri=False,start_ts=datetime.now(),
                                     storage_path=storage_path,
                                     autorestore=autorestore)
            childprocess.daemon = True
            childprocess.start()
            siteregister_processes_dict['register'] = childprocess

            if self.hasSysPackageAndIsPrimary(sitename):
                taskScheduler = Process(name='ts_%s' %sitename, target=createTaskScheduler,kwargs=dict(sitename=sitename))
                taskScheduler.daemon = True
                taskScheduler.start()
                siteregister_processes_dict['task_scheduler'] = taskScheduler 
            sitedict = siteregister_processes_dict
            self.startServiceProcesses(sitename,sitedict=sitedict)
            #self.startGnrDaemonServiceManager(sitename)
            #self.siteregisters_process[sitename] = sitedict
        else:
            print('ALREADY EXISTING ',sitename)

    def pyroProxy(self,url):
        proxy = Pyro4.Proxy(url)
        return proxy

    def siteRegisters(self,**kwargs):
        sr = dict(self.siteregisters)
        for k,v in list(sr.items()):
            register_process = self.siteregisters_process[k]['register']
            v['pid'] = register_process.pid
            v['is_alive'] = register_process.is_alive()
        return list(sr.items())

    def siteRegisterProxy(self,sitename):
        return self.pyroProxy(self.siteregisters[sitename]['register_uri'])

    def siteregister_dump(self,sitename=None,**kwargs):
        uri = self.siteregisters[sitename]['register_uri']
        with self.pyroProxy(uri) as proxy:
            return proxy.dump()

    @expose
    def setSiteInMaintenance(self,sitename,status=None,allowed_users=None):
        uri = self.siteregisters[sitename]['register_uri']
        with self.pyroProxy(uri) as proxy:
            return proxy.setMaintenance(status,allowed_users=allowed_users)

    def siteregister_stop(self,sitename=None,saveStatus=False,**kwargs):
        if sitename == '*':
            sitelist = list(self.siteregisters.keys())
        elif isinstance(sitename, str):
            sitelist = sitename.split(',')
        else:
            sitelist = sitename
        result = {}
        for k in sitelist:
            if not k in self.siteregisters:
                continue
            sitepars = self.siteregisters[k]
            try:
                with self.pyroProxy(sitepars['server_uri']) as proxy:
                    proxy.stop(saveStatus=saveStatus)
            except Exception as e:
                print(str(e))
            self.onRegisterStop(k)
            result[k] = sitepars
        return result

    def siteregister_start(self,stopStatus):
        for sitename,pars in list(stopStatus.items()):
            self.addSiteRegister(sitename,storage_path=pars['storage_path'],
                        autorestore=pars['autorestore'],
                        port=pars['register_port'])

    def siteregister_restartServiceDaemon(self,sitename=None,service_name=None):
        self.restartServiceDaemon(sitename=sitename, service_name=service_name)

    def siteregister_restart(self,sitename=None,**kwargs):
        self.siteregister_start(self.siteregister_stop(sitename,True))



    def sshtunnel_port(self,ssh_host=None,ssh_port=None, ssh_user=None, ssh_password=None, forwarded_port=None,forwarded_host=None,**kwargs):
        return self.sshtunnel_get(ssh_host=ssh_host,ssh_port=ssh_port,ssh_password=ssh_password,forwarded_port=forwarded_port,forwarded_host=forwarded_host).local_port

    def sshtunnel_get(self,ssh_host=None,ssh_port=None, ssh_user=None, ssh_password=None,
                     forwarded_port=None,forwarded_host=None,**kwargs):
        from gnr.core.gnrssh import normalized_sshtunnel_parameters
        ssh_parameters = normalized_sshtunnel_parameters(ssh_host=ssh_host,ssh_port=ssh_port,ssh_user=ssh_user,ssh_password=ssh_password,
                                        forwarded_port=forwarded_port,forwarded_host=forwarded_host)
        tunnelKey = '%(ssh_host)s:%(ssh_port)s - %(forwarded_host)s:%(forwarded_port)s' %ssh_parameters
        if not tunnelKey in self.sshtunnel_index:
            self.sshtunnel_index[tunnelKey] = self.sshtunnel_create(**ssh_parameters)
        return self.sshtunnel_index[tunnelKey]

    def sshtunnel_create(self,ssh_host=None,ssh_port=None, ssh_user=None, ssh_password=None,
                     forwarded_port=None,forwarded_host=None,**kwargs):
        from gnr.core.gnrssh import SshTunnel
        tunnel = SshTunnel(forwarded_port=int(forwarded_port), forwarded_host=forwarded_host,
                ssh_host=ssh_host, ssh_port=int(ssh_port),
                username=ssh_user, password=ssh_password)
        tunnel.prepare_tunnel()
        tunnel.serve_tunnel()
        return tunnel

    def sshtunnel_stop(self,**tunnel_kwargs):
        self.sshtunnel_get(**tunnel_kwargs).stop()
