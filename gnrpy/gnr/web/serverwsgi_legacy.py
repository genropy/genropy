import time
from datetime import datetime
import os
import sys
import re
import atexit

from gnr.core.cli import GnrCliArgParse
from gnr.core.gnrbag import Bag
from gnr.core.gnrdict import dictExtract
from gnr.web.gnrwsgisite import GnrWsgiSite
from gnr.web import logger
from gnr.core.gnrconfig import getGnrConfig, gnrConfigPath
from gnr.app.gnrdeploy import PathResolver

from werkzeug.serving import run_simple
from werkzeug.debug.tbtools import get_current_traceback, render_console_html
from werkzeug.debug import DebuggedApplication,_ConsoleFrame
from werkzeug.wrappers import Response, Request

CONN_STRING_RE=r"(?P<ssh_user>\w*)\:?(?P<ssh_password>\w*)\@(?P<ssh_host>(\w|\.)*)\:?(?P<ssh_port>\w*)(\/?(?P<db_user>\w*)\:?(?P<db_password>\w*)\@(?P<db_host>(\w|\.)*)\:?(?P<db_port>\w*))?"
CONN_STRING = re.compile(CONN_STRING_RE)


wsgi_options = dict(
        port=8080,
        host='0.0.0.0',
        reload=False,
        set_user=None,
        set_group=None,
        server_name='Genropy',
        debug=True,
        profile=False,
        noclean=False,
        restore=False,
        source_instance=None,
        remote_edit=None,
        remotesshdb=None,
        gzip=None,
        websocket=True,
        tornado=None
        )

DNS_SD_PID = None


def run_sitedaemon(sitename=None, sitepath=None, debug=None, storage_path=None, host=None, port=None, socket=None, hmac_key=None):
        from gnr.web.gnrwsgisite_proxy.gnrsiteregister import GnrSiteRegisterServer
        import os
        from gnr.core.gnrbag import Bag
        sitedaemon = GnrSiteRegisterServer(sitename=sitename,debug=debug, storage_path=storage_path)
        sitedaemon.start(host=host,socket=socket,hmac_key=hmac_key,port=port, run_now=False)
        sitedaemon_xml_path = os.path.join(sitepath,'sitedaemon.xml')
        sitedaemon_bag = Bag()
        sitedaemon_bag.setItem('params',None,
            register_uri=sitedaemon.register_uri,
            main_uri = sitedaemon.main_uri,
            pid=os.getpid()
            )
        sitedaemon_bag.toXml(sitedaemon_xml_path)
        sitedaemon.run()

class GnrDebuggedApplication(DebuggedApplication):

    def debug_application(self, environ, start_response):
        """Run the application and conserve the traceback frames."""
        app_iter = None
        try:
            app_iter = self.app(environ, start_response)
            for item in app_iter:
                yield item
            if hasattr(app_iter, 'close'):
                app_iter.close()
        except Exception:
            if hasattr(app_iter, 'close'):
                app_iter.close()
            traceback = get_current_traceback(
                skip=1, show_hidden_frames=self.show_hidden_frames,
                ignore_system_exceptions=True)
            for frame in traceback.frames:
                self.frames[frame.id] = frame
            self.tracebacks[traceback.id] = traceback
            request = Request(environ)
            debug_url = '%sconsole?error=%i'%(request.host_url, traceback.id)

            logger.error(f"Error occurred, debug on {debug_url}")

            try:
                start_response('500 INTERNAL SERVER ERROR', [
                    ('Content-Type', 'text/html; charset=utf-8'),
                    # Disable Chrome's XSS protection, the debug
                    # output can cause false-positives.
                    ('X-XSS-Protection', '0'),
                    ('X-Debug-Url', debug_url)
                ])
            except Exception:
                # if we end up here there has been output but an error
                # occurred.  in that situation we can do nothing fancy any
                # more, better log something into the error log and fall
                # back gracefully.
                environ['wsgi.errors'].write(
                    'Debugging middleware caught exception in streamed '
                    'response at a point where response headers were already '
                    'sent.\n')
            else:
                is_trusted = bool(self.check_pin_trust(environ))
                yield traceback.render_full(evalex=self.evalex,
                                            evalex_trusted=is_trusted,
                                            secret=self.secret) \
                    .encode('utf-8', 'replace')
            traceback.log(environ['wsgi.errors'])


    def display_console(self, request):
        """Display a standalone shell."""
        error = request.args.get('error', type=int)
        traceback = self.tracebacks.get(error)
        is_trusted = bool(self.check_pin_trust(request.environ))
        if traceback:
            return Response(traceback.render_full(evalex=self.evalex,
                                            evalex_trusted=is_trusted,
                                            secret=self.secret) \
                    .encode('utf-8', 'replace'),
                        mimetype='text/html')
        if 0 not in self.frames:
            if self.console_init_func is None:
                ns = {}
            else:
                ns = dict(self.console_init_func())
            ns.setdefault('app', self.app)
            self.frames[0] = _ConsoleFrame(ns)
        return Response(render_console_html(secret=self.secret,
                                            evalex_trusted=is_trusted),
                        mimetype='text/html')


class ServerException(Exception):
    pass

class DaemonizeException(Exception):
    pass

class Server(object):
    min_args = 0
    usage = '[start|stop|restart|status] [var=value]'
    summary = "Start this genropy application"
    description = """\
    This command serves a genropy web application.
    """


    parser = GnrCliArgParse(description=summary)
    parser.add_argument('--log-file',
                      dest='log_file',
                      metavar='LOG_FILE',
                      help="Save output to the given log file (redirects stdout)")
    parser.add_argument('--reload',
                      dest='reload',
                      action='store_true',
                      help="Use auto-restart file monitor")
    parser.add_argument('--noreload',
                      dest='reload',
                      action='store_false',
                      help="Do not use auto-restart file monitor")
    parser.add_argument('--profile',
                      dest='profile',
                      action='store_true',
                      help="Use profiler at /__profile__ url")
    parser.add_argument('--websocket',
                      dest='websocket',
                      action='store_true',
                      help="Use websocket")
    parser.add_argument('-t','--tornado',
                      dest='tornado',
                      action='store_true',
                      help="Serve using tornado")

    parser.add_argument('--reload-interval',
                      dest='reload_interval',
                      default=1,
                      help="Seconds between checking files (low number can cause significant CPU usage)")

    parser.add_argument('-c', '--config',
                      dest='config_path',
                      help="gnrserve directory path")

    parser.add_argument('-p', '--port',
                      dest='port',
                      help="Sets server listening port (Default: 8080)")

    parser.add_argument('-H', '--host',
                      dest='host',
                      help="Sets server listening address (Default: 0.0.0.0)")

    parser.add_argument('--restore',
                      dest='restore',
                      help="Restore from path")
    parser.add_argument('--source_instance',
                      dest='source_instance',
                      help="Import from instance")

    parser.add_argument('--remote_edit',
                      dest='remote_edit',
                      action='store_true',
                      help="Enable remote edit")
    parser.add_argument('-g','--gzip',
                      dest='gzip',
                      action='store_true',
                      help="Enable gzip compressions")

    parser.add_argument('--verbose',
                      dest='verbose',
                      action='store_true',
                      help='Verbose')
    
    parser.add_argument('-s', '--site',
                      dest='site_name_opt',
                      help="Use command on site identified by supplied name")
    parser.add_argument('site_name', nargs='?')
    
    parser.add_argument('-n', '--noclean',
                      dest='noclean',
                      help="Don't perform a clean (full reset) restart",
                      action='store_true')

    parser.add_argument('--counter',
                      dest='counter',
                      help="Startup counter")

    parser.add_argument('--ssl_cert',
                      dest='ssl_cert',
                      help="SSL cert")

    parser.add_argument('--ssl_key',
                      dest='ssl_key',
                      help="SSL key")

    parser.add_argument('--ssl',
                      dest='ssl',
                      action='store_true',
                      help="SSL")

    _scheme_re = re.compile(r'^[a-z][a-z]+:', re.I)

    default_verbosity = 1

    _reloader_environ_key = 'PYTHON_RELOADER_SHOULD_RUN'
    _monitor_environ_key = 'PASTE_MONITOR_SHOULD_RUN'

    possible_subcommands = ('start', 'stop', 'restart', 'status')

    def __init__(self, site_script=None, server_name='Genro Server', server_description='Development'):
        self.site_script = site_script
        self.server_description = server_description
        self.server_name = server_name

        # this is needed maintain compatibility with
        # legacy scripts.
        if sys.argv[0].startswith("gnr "):
                cmdline = sys.argv.pop(0).split()
                sys.argv.insert(0, cmdline)
                
        self.options = self.parser.parse_args()
        if hasattr(self.options, 'config_path') and self.options.config_path:
            self.config_path = self.options.config_path
        else:
            self.config_path = gnrConfigPath()
        self.gnr_config = getGnrConfig(config_path=self.config_path, set_environment=True)

        self.site_name = self.options.site_name_opt or self.options.site_name or os.getenv('GNR_CURRENT_SITE')
        if self.site_name is None:
                logger.error("site name is required")
                sys.exit(1)
        
        if not self.site_name:
            self.site_name = os.path.basename(os.path.dirname(site_script))
        self.remote_db = ''
        if self.site_name:
            if ':' in self.site_name:
                self.site_name,self.remote_db  = self.site_name.split(':',1)
            if not self.gnr_config:
                raise ServerException(
                        'Error: no ~/.gnr/ or /etc/gnr/ found')
            self.site_path = self.site_name_to_path(self.site_name)
            self.site_script = os.path.join(self.site_path, 'root.py')
            if not os.path.isfile(self.site_script):
                self.site_script = os.path.join(self.site_path, '..','root.py')
                if not os.path.exists(self.site_script):
                    raise ServerException(
                        'Error: no root.py in the site provided (%s)' % self.site_name)
        else:
            self.site_path = os.path.dirname(os.path.realpath(site_script))
        self.init_options()

    def isVerbose(self, level=0):
        return self.options.verbose and self.options.verbose>level

    def site_name_to_path(self, site_name):
        return PathResolver().site_name_to_path(site_name)


    def init_options(self):
        self.siteconfig = self.get_config()
        options = self.options.__dict__
        envopt = dictExtract(os.environ,'GNR_WSGI_OPT_')
        for option in list(options.keys()):
            if options.get(option, None) is None: # not specified on the command-line
                site_option = self.siteconfig['wsgi?%s' % option]
                self.options.__dict__[option] = site_option or wsgi_options.get(option) or envopt.get(option)

    def get_config(self):
        return PathResolver().get_siteconfig(self.site_name)

    @property
    def site_config(self):
        if not hasattr(self, '_site_config'):
            self._site_config = self.get_config()
        return self._site_config

    @property
    def instance_config(self):
        if not hasattr(self, '_instance_config'):
            self._instance_config = self.get_instance_config()
        return self._instance_config

    def get_instance_config(self):
        instance_path = os.path.join(self.site_path, 'instance')
        if not os.path.isdir(instance_path):
            instance_path = os.path.join(self.site_path, '..', '..', 'instances', self.site_name)
        if not os.path.isdir(instance_path):
            instance_path = self.site_config['instance?path'] or self.site_config['instances.#0?path']
        instance_config_path = os.path.join(instance_path, 'instanceconfig.xml')
        base_instance_config = Bag(instance_config_path)
        instance_config = self.gnr_config['gnr.instanceconfig.default_xml'] or Bag()
        template = instance_config['instance?template'] or getattr(self, 'instance_template', None)
        if template:
            instance_config.update(self.gnr_config['gnr.instanceconfig.%s_xml' % template] or Bag())
        if 'instances' in self.gnr_config['gnr.environment_xml']:
            for path, instance_template in self.gnr_config.digest('gnr.environment_xml.instances:#a.path,#a.instance_template'):
                if path == os.path.dirname(instance_path):
                    instance_config.update(self.gnr_config['gnr.instanceconfig.%s_xml' % instance_template] or Bag())
        instance_config.update(base_instance_config)
        return instance_config

    def run(self):
        self.reloader = not (self.options.reload == 'false' or self.options.reload == 'False' or self.options.reload == False or self.options.reload == None)
        self.debug = not (self.options.debug == 'false' or self.options.debug == 'False' or self.options.debug == False or self.options.debug == None)
        self.start_sitedaemon()
        self.serve()

    def start_sitedaemon(self):
        from gnr.app.gnrdeploy import PathResolver
        import os
        from multiprocessing import Process
        path_resolver = PathResolver()
        siteconfig = path_resolver.get_siteconfig(self.site_name)
        daemonconfig = siteconfig.getAttr('gnrdaemon')
        sitedaemonconfig = siteconfig.getAttr('sitedaemon') or {}
        if not sitedaemonconfig:
            return
        sitepath = path_resolver.site_name_to_path(self.site_name)
        sitedaemon_attr = dict(
            sitepath = sitepath,
            debug = sitedaemonconfig.get('debug',None),
            host = sitedaemonconfig.get('host','localhost'),
            socket = sitedaemonconfig.get('socket',None),
            port = sitedaemonconfig.get('port','*'),
            hmac_key = sitedaemonconfig.get('hmac_key') or daemonconfig['hmac_key'],
            storage_path = os.path.join(sitepath, 'siteregister_data.pik')
        )
        sitedaemon_process = Process(name='sitedaemon_%s' %(self.site_name),
                        target=run_sitedaemon, kwargs=sitedaemon_attr)
        sitedaemon_process.daemon = True
        sitedaemon_process.start()
        logger.info('sitedaemon started')
        time.sleep(1)

    def serve(self):
        port = int(self.options.port)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        host = self.options.host
        site_name='%s:%s' %(self.site_name,self.remote_db) if self.remote_db else self.site_name
        if self.options.tornado:
            host = '127.0.0.1' if self.options.host == '0.0.0.0' else self.options.host

            from gnr.web.gnrasync import GnrAsyncServer
            site_options= dict(_config=self.siteconfig,_gnrconfig=self.gnr_config,
                counter=getattr(self.options, 'counter', None),
                noclean=self.options.noclean, options=self.options)
            logger.info(f"Starting Tornado server - listening on {host}:{port}")
            server=GnrAsyncServer(port=port,instance=site_name,
                web=True, autoreload=self.options.reload, site_options=site_options)
            server.start()
        else:
            gnrServer = GnrWsgiSite(self.site_script, site_name=site_name, _config=self.siteconfig,
                                    _gnrconfig=self.gnr_config,
                                    counter=getattr(self.options, 'counter', None), noclean=self.options.noclean,
                                    options=self.options)
            atexit.register(gnrServer.on_site_stop)
            extra_info = []
            if self.debug:
                gnrServer = GnrDebuggedApplication(gnrServer, evalex=True, pin_security=False)
                extra_info.append('Debug mode: On')
            ssl_context = None
            localhost = 'http://127.0.0.1'
            if self.options.ssl:
                from gnr.app.gnrconfig import gnrConfigPath
                cert_path = os.path.join(gnrConfigPath(),'localhost.pem')
                key_path = os.path.join(gnrConfigPath(),'localhost-key.pem')
                if os.path.exists(cert_path) and os.path.exists(key_path):
                    ssl_context = (cert_path, key_path)
                extra_info.append('SSL mode: On')
                localhost = 'https://localhost'
            if self.options.ssl_cert and self.options.ssl_key:
                ssl_context=(self.options.ssl_cert,self.options.ssl_key)
                extra_info.append(f'SSL mode: On {ssl_context}')
                localhost = 'https://{host}'.format(host=self.options.ssl_cert.split('/')[-1].split('.pem')[0])
            logger.info(f"Starting server - listening on {localhost}:{port}\t%s", ",".join(extra_info))
            
            run_simple(host, port, gnrServer, use_reloader=self.reloader, threaded=True,
                reloader_type='stat', ssl_context=ssl_context)


