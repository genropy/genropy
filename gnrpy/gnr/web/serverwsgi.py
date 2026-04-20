import sys
import os
import atexit
import webbrowser
import socket

from werkzeug.serving import make_server, is_running_from_reloader
from werkzeug._reloader import run_with_reloader
from werkzeug.debug.tbtools import render_console_html
try:
    from werkzeug.debug.tbtools import DebugTraceback
    def traceback_frames(e,show_hidden_frames):
        tb = DebugTraceback(e, skip=1, hide=not show_hidden_frames)
        return tb,tb.all_frames

    def render_tb(tb, *args, **kwargs):
        return tb.render_debugger_html(*args, **kwargs)

except ImportError:
    from werkzeug.debug.tbtools import get_current_traceback
    def traceback_frames(e,show_hidden_frames):
        tb = get_current_traceback(skip=1,
                show_hidden_frames=show_hidden_frames,
                ignore_system_exceptions=True)
        return tb, tb.frames

    def render_tb(tb, *args, **kwargs):
        return tb.render_full(*args, **kwargs)

from werkzeug.debug import DebuggedApplication,_ConsoleFrame
from werkzeug.wrappers import Response, Request

from gnr.core.cli import GnrCliArgParse
from gnr.core.gnrconfig import getGnrConfig, gnrConfigPath
from gnr.core.gnrdict import dictExtract
from gnr.app.pathresolver import PathResolver
from gnr.web.gnrwsgisite import GnrWsgiSite
from gnr.web import logger
wsgi_options = dict(
        port=8080,
        host='0.0.0.0',
        reload=False,
        debug=True,
        noclean=False,
        restore=False,
        source_instance=None,
        remote_edit=None,
        tornado=None
        )


class GnrDebuggedApplication(DebuggedApplication):

    def debug_application(self, environ, start_response):
        """Run the application and conserve the traceback frames."""
        app_iter = None
        if not hasattr(self,'tracebacks'):
            self.tracebacks = {}
        try:
            app_iter = self.app(environ, start_response)
            for item in app_iter:
                yield item
            if hasattr(app_iter, 'close'):
                app_iter.close()
        except Exception as e:
            if hasattr(app_iter, 'close'):
                app_iter.close()


            traceback, tb_frames = traceback_frames(e,self.show_hidden_frames)
            traceback_id = id(traceback)
            for frame in tb_frames:
                self.frames[id(frame)] = frame
            self.tracebacks[traceback_id] = traceback
            request = Request(environ)
            debug_url = '%sconsole?error=%i'%(request.host_url, traceback_id)

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
                yield render_tb(traceback,evalex=self.evalex,
                                            evalex_trusted=is_trusted,
                                            secret=self.secret) \
                    .encode('utf-8', 'replace')


    def display_console(self, request):
        """Display a standalone shell."""
        error = request.args.get('error', type=int)
        traceback = self.tracebacks.get(error)
        is_trusted = bool(self.check_pin_trust(request.environ))
        if traceback:
            return Response(render_tb(traceback,evalex=self.evalex,
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

def host_binding_address(host):
    """
    Type validator for command line
    """
    try:
        socket.getaddrinfo(host, 1)
        return host
    except:
        raise ValueError(f"Invalid address: {host}")
    
class Server(object):
    description = "This command serves a genropy web application."


    def __init__(self, site_script=None):
        parser = GnrCliArgParse(description=self.description)
        parser.add_argument('--reload',
                            dest='reload',
                            action='store_true',
                            help="Use auto-restart file monitor")
        parser.add_argument('--noreload',
                            dest='reload',
                            action='store_false',
                            help="Do not use auto-restart file monitor")
        parser.add_argument('--nodebug',
                            dest='nodebug',
                            action='store_true',
                            help="Don't use werkzeug debugger")
        parser.add_argument('-t','--tornado',
                            dest='tornado',
                            action='store_true',
                            help="Serve using tornado")
        
        parser.add_argument('-o','--open',
                            dest='open_browser',
                            action='store_true',
                            help="Automatically open the browser to this application")
        parser.add_argument('-c', '--config',
                            dest='config_path',
                            help="gnrserve directory path")
        parser.add_argument('-p', '--port',
                            dest='port',
                            help="Sets server listening port (Default: 8080)")
        parser.add_argument('-H', '--host',
                            dest='host',
                            type=host_binding_address,
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
        parser.add_argument('--remotedb',
                            nargs="?",
                            const=True,
                            default=None,
                            dest='remotedb',
                            help="Use a remote db")
        parser.add_argument('site_name', nargs='?')
        parser.add_argument('-s', '--site',
                            dest='site_name_opt',
                            help="Use command on site identified by supplied name")

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
        
        parser.add_argument('--debugpy',
                    dest='debugpy',
                    action='store_true',
                    help="Enable Debugpy for remote debugging on port 5678, change port with --debugpy-port")
        
        parser.add_argument('--debugpy-port',
                dest='debugpy_port',
                type=int,
                help="Debugpy port (defaults to 5678)")

        self.site_script = site_script
        self.app_scheme = 'http'
        self.app_host = '127.0.0.1'
        self.app_port = '8080'
        
        parser.set_defaults(loglevel="info")
        self.options = parser.parse_args()
        if hasattr(self.options, 'config_path') and self.options.config_path:
            self.config_path = self.options.config_path
        else:
            self.config_path = gnrConfigPath()
        self.gnr_config = getGnrConfig(config_path=self.config_path, set_environment=True)

        self.site_name = self.options.site_name_opt or self.options.site_name or os.getenv('GNR_CURRENT_SITE')
        if not self.site_name and not self.site_script:
            logger.error("site name is required")
            sys.exit(1)

        if not self.site_name:
            self.site_name = os.path.basename(os.path.dirname(site_script))
            
        # the use --remotedb options is defined, use the instance name
        # as a default remotedb name, if a value is provided, use it

        if self.options.remotedb:
            if self.options.remotedb is True:
                self.site_name = f"{self.site_name}:{self.site_name}"
            else:
                self.site_name = f"{self.site_name}:{self.options.remotedb}"
            
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

    def site_name_to_path(self, site_name):
        return PathResolver().site_name_to_path(site_name)


    def init_options(self):
        self.siteconfig = self.get_config()
        options = self.options.__dict__
        envopt = dictExtract(os.environ,'GNR_WSGI_OPT_')
        for option in list(options.keys()):

            if not options.get(option, None): # not specified on the command-line
                option_value = wsgi_options.get(option)

                site_option_value = self.siteconfig['wsgi?%s' % option]
                if site_option_value is not None:
                    option_value = site_option_value
                if option in envopt:
                    option_value = envopt.get(option)

                self.options.__dict__[option] = option_value

    def get_config(self):
        return PathResolver().get_siteconfig(self.site_name)

    def run(self):
        try:
            import debugpy
            self.debugpy = self.options.debugpy or self.options.debugpy_port is not None
            self.debugpy_port = self.options.debugpy_port or 5678
        except ImportError:
            logger.error(f"Failed to import debugpy: {sys.exc_info()[1]}. Install debugpy or genropy's developer profile.")
            self.debugpy = False
            self.debugpy_port = None
            
        self.reloader = not self.debugpy and not (self.options.reload == 'false' or self.options.reload == 'False' or self.options.reload == False or self.options.reload == None)
        self.debug = not (self.options.debug == 'false' or self.options.debug == 'False' or self.options.debug == False or self.options.debug == None or self.options.nodebug)
        if self.debugpy:
            logger.debug("Starting debugpy service on port localhost:%s", self.debugpy_port)
            debugpy.listen(("localhost", self.debugpy_port))
        self.serve()

    @property
    def app_url(self):
        connect_host = '127.0.0.1' if self.app_host == '0.0.0.0' else self.app_host
        return f'{self.app_scheme}://{connect_host}:{self.app_port}'
        
    def serve(self):
        self.app_port = int(self.options.port)
        self.app_host = self.options.host
        site_name= f'{self.site_name}:{self.remote_db}' if self.remote_db else self.site_name

        if self.options.tornado:
            self.app_host = '127.0.0.1' if self.options.host == '0.0.0.0' else self.options.host

            from gnr.web.gnrasync import GnrAsyncServer
            site_options= dict(_config=self.siteconfig,_gnrconfig=self.gnr_config,
                counter=getattr(self.options, 'counter', None),
                noclean=self.options.noclean, options=self.options)
            logger.info(f"Starting Tornado server - listening on {self.app_host}:{self.app_port}")
            server=GnrAsyncServer(port=self.app_port, instance=site_name,
                                  web=True, autoreload=self.options.reload,
                                  site_options=site_options)
            server.start()
        else:
            ssl_context = None
            if not self.debugpy and self.reloader and not is_running_from_reloader():
                gnrServer='FakeApp'
            else:
                gnrServer = GnrWsgiSite(self.site_script,
                                        site_name=site_name,
                                        _config=self.siteconfig,
                                        _gnrconfig=self.gnr_config,
                                        counter=getattr(self.options, 'counter', None),
                                        noclean=self.options.noclean,
                                        options=self.options,
                                        debugpy=self.debugpy)
                gnrServer._local_mode=True
                atexit.register(gnrServer.on_site_stop)
                extra_info = []
                if self.debugpy:
                    extra_info.append(f'Debugpy on port {self.debugpy_port} on loopback interface')
                elif self.debug:
                    gnrServer = GnrDebuggedApplication(gnrServer, evalex=True, pin_security=False)
                    extra_info.append('Debug mode: On')
                else:
                    extra_info.append('Debug mode: Off')

                if self.options.ssl:
                    cert_path = os.path.join(self.config_path,'localhost.pem')
                    key_path = os.path.join(self.config_path,'localhost-key.pem')
                    if os.path.exists(cert_path) and os.path.exists(key_path):
                        ssl_context = (cert_path, key_path)
                    extra_info.append('SSL mode: On')
                    app_scheme = 'https'
                if self.options.ssl_cert and self.options.ssl_key:
                    ssl_context=(self.options.ssl_cert,self.options.ssl_key)
                    extra_info.append(f'SSL mode: On {ssl_context}')
                    app_scheme = 'https'
                    self.app_host = self.options.ssl_cert.split('/')[-1].split('.pem')[0]
                    
                logger.info(f"Started server on {self.app_host}:{self.app_port}\t%s", ",".join(extra_info))
                logger.info(f"Connect at {self.app_url}")
                
            if self.options.open_browser and not os.environ.get("WERKZEUG_RUN_MAIN", None):
                logger.info(f'Opening browser to application on {self.app_url}')
                webbrowser.open(self.app_url)

            if not is_running_from_reloader():
                fd = None
            else:
                fd = int(os.environ["WERKZEUG_SERVER_FD"])

            srv = make_server(
                self.app_host,
                self.app_port,
                gnrServer,
                threaded=True,
                processes=1,
                ssl_context=ssl_context,
                fd=fd)
            srv.socket.set_inheritable(True)
            os.environ["WERKZEUG_SERVER_FD"] = str(srv.fileno())

            if self.reloader:
                
                # werkzeug reloader expects sys.argv without
                # spaces for the reloader on python3.8
                if " " in sys.argv[0]:
                    cmd_name = sys.argv.pop(0).split()
                    sys.argv = cmd_name + sys.argv

                run_with_reloader(
                    srv.serve_forever,
                    #extra_files=extra_files,
                    #exclude_patterns=exclude_patterns,
                    interval=1,
                    reloader_type="auto",
                )
            else:
                try:
                    srv.serve_forever()
                finally:
                    srv.server_close()
            if not is_running_from_reloader():
                logger.info("Shutting down")

