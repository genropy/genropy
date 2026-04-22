import multiprocessing
import warnings
import os
import sys
import site
import pathlib
import shutil
import random
import string
from venv import EnvBuilder

import gnr as gnrbase
from gnr.core.gnrbag import Bag, DirectoryResolver
from gnr.core.gnrconfig import IniConfStruct
from gnr.core.gnrconfig import getGnrConfig,gnrConfigPath
from gnr.app.pathresolver import PathResolver as _PathResolver
from gnr.app import logger


# PathResolver has been moved.
def __getattr__(name):
    if name == "PathResolver":
        warnings.warn(
            "PathResolver has moved to gnr.app.pathresolver. Import from there instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return _PathResolver
    raise AttributeError(f"module {__name__} has no attribute {name}")


class GnrConfigException(Exception):
    pass


def get_random_password(size = 12):
    return ''.join( random.Random().sample(string.ascii_letters+string.digits, size)).lower()

def get_gnrdaemon_port(set_last=False):
    base_config_path  = gnrConfigPath(no_virtualenv=True)
    if not base_config_path or not os.path.exists(base_config_path):
        return '40404'
    environment_xml_path = os.path.join(base_config_path,'environment.xml')
    if not os.path.exists(environment_xml_path):
        return '40404'
    environment_bag = Bag(environment_xml_path)
    gnrdaemon_port = int(environment_bag['gnrdaemon?last_port'] or environment_bag['gnrdaemon?port'] or '40404') + 1
    if set_last:
        environment_bag.getNode('gnrdaemon').attr.update(last_port = gnrdaemon_port)
        environment_bag.toXml(environment_xml_path, typevalue=False,pretty=True)
    return str(gnrdaemon_port)

def build_environment_xml(path=None, gnrpy_path=None, gnrdaemon_password=None, gnrdaemon_port=None):
    genropy_home = gnrpy_path

    # hack to understand if we're running genropy from a checkout
    # or from an installation
    if "gnrpy" in genropy_home:
        genropy_home = os.path.realpath(os.path.join(genropy_home, "..", ".."))
        genropy_projects = os.path.join(genropy_home,'projects')
        genropy_packages = os.path.join(genropy_home,'packages')
        genropy_resources = os.path.join(genropy_home,'resources')
        genropy_webtools = os.path.join(genropy_home,'webtools')
        dojo_11_path = os.path.join(genropy_home, 'dojo_libs', 'dojo_11')
        dojo_20_path = os.path.join(genropy_home, 'dojo_libs', 'dojo_20')
        gnr_d11_path = os.path.join(genropy_home,'gnrjs', 'gnr_d11')
        gnr_d20_path = os.path.join(genropy_home,'gnrjs', 'gnr_d20')
    else:
        genropy_projects = os.path.join(genropy_home,'projects')
        genropy_packages = os.path.join(genropy_home,'packages')
        genropy_resources = os.path.join(genropy_home,'resources')
        genropy_webtools = os.path.join(genropy_home,'webtools')
        dojo_11_path = os.path.join(genropy_home, 'dojo_libs', 'dojo_11')
        dojo_20_path = os.path.join(genropy_home, 'dojo_libs', 'dojo_20')
        gnr_d11_path = os.path.join(genropy_home,'gnrjs', 'gnr_d11')
        gnr_d20_path = os.path.join(genropy_home,'gnrjs', 'gnr_d20')

    # FIXME: this needs to be handled differently when we're installing the package
    # otherwise genropy_project will be helded inside {dist,site}-packages dir
    custom_projects = os.path.normpath(os.path.join(genropy_home,'..','genropy_projects'))
    create_folder(custom_projects)
    
    environment_bag = Bag()
    environment_bag.setItem('environment.gnrhome', None, dict(value=genropy_home))
    environment_bag.setItem('projects.genropy', None, dict(path=genropy_projects))
    environment_bag.setItem('projects.custom', None, dict(path=custom_projects))
    environment_bag.setItem('packages.genropy', None, dict(path=genropy_packages))
    environment_bag.setItem('static.js.dojo_11',None, dict(path=dojo_11_path, cdn=""))
    environment_bag.setItem('static.js.dojo_20',None, dict(path=dojo_20_path, cdn=""))
    environment_bag.setItem('static.js.gnr_11', None, dict(path=gnr_d11_path))
    environment_bag.setItem('static.js.gnr_20', None, dict(path=gnr_d20_path))
    environment_bag.setItem('resources.genropy', None, dict(path=genropy_resources))
    environment_bag.setItem('webtools.genropy', None, dict(path=genropy_webtools))
    gnrdaemon_port = gnrdaemon_port or get_gnrdaemon_port(set_last=True)
    environment_bag.setItem('gnrdaemon', None, dict(host='localhost', port=gnrdaemon_port, hmac_key=gnrdaemon_password))
    environment_bag.toXml(path,typevalue=False,pretty=True)

def build_instanceconfig_xml(path=None,avoid_baseuser=None):
    instanceconfig_bag = Bag()
    instanceconfig_bag.setItem('packages',None)
    instanceconfig_bag.setItem('authentication.xml_auth',None, dict(defaultTags='user,xml'))
    password = get_random_password(size=6)
    if not avoid_baseuser:
        instanceconfig_bag.setItem('authentication.xml_auth.admin',None, dict(pwd=password, tags='superadmin,_DEV_,admin,user'))
        print("Default password for user admin is %s, you can change it by editing %s" %(password, path))
    instanceconfig_bag.toXml(path,typevalue=False,pretty=True)
    
def build_siteconfig_xml(path=None, gnrdaemon_password=None, gnrdaemon_port=None):
    siteconfig_bag = Bag()
    siteconfig_bag.setItem('wsgi', None, dict(debug=True, reload=True, port='8080'))
    siteconfig_bag.setItem('gui', None, dict(css_theme=os.environ.get('GNR_CSS_THEME', 'mimi')))
    siteconfig_bag.setItem('jslib', None, dict(dojo_version='11', gnr_version='11'))
    siteconfig_bag.setItem('resources.common', None)
    siteconfig_bag.setItem('resources.js_libs', None)
    siteconfig_bag.setItem('gnrdaemon', None, dict(host='localhost', port=gnrdaemon_port or '40404', hmac_key=gnrdaemon_password))
    siteconfig_bag.toXml(path,typevalue=False,pretty=True)

def create_folder(folder_path=None):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
    elif not os.path.isdir(folder_path):
        raise GnrConfigException("A file named %s already exists so i couldn't create a folder at same path" % folder_path)

def check_file(xml_path=None):
    if os.path.exists(xml_path):
        raise GnrConfigException("A file named %s already exists so i couldn't create a config file at same path" % xml_path)

def initgenropy(gnrdaemon_password=None,avoid_baseuser=False):
    gnrpy_path = os.path.dirname(gnrbase.__file__)
    config_path  = gnrConfigPath(force_return=True)
    instanceconfig_path = os.path.join(config_path,'instanceconfig')
    siteconfig_path = os.path.join(config_path,'siteconfig')
    for folder_path in (config_path, instanceconfig_path, siteconfig_path):
        create_folder(folder_path=folder_path)

    environment_xml_path = os.path.join(config_path,'environment.xml')
    default_instanceconfig_xml_path = os.path.join(instanceconfig_path,'default.xml')
    default_siteconfig_xml_path = os.path.join(siteconfig_path,'default.xml')

    for xml_path in (environment_xml_path, default_instanceconfig_xml_path, default_siteconfig_xml_path):
        check_file(xml_path=xml_path)
    gnrdaemon_password = gnrdaemon_password or get_random_password()
    gnrdaemon_port = get_gnrdaemon_port(set_last=True)
    build_environment_xml(path=environment_xml_path, gnrpy_path=gnrpy_path, gnrdaemon_password=gnrdaemon_password,
        gnrdaemon_port=gnrdaemon_port)
    build_instanceconfig_xml(path=default_instanceconfig_xml_path,avoid_baseuser=avoid_baseuser)
    build_siteconfig_xml(path=default_siteconfig_xml_path, gnrdaemon_password=gnrdaemon_password, gnrdaemon_port=gnrdaemon_port)



GNRDAEMON_SERVICE_TPL = """
[Unit]
Description=GnrDaemon Service
After=multi-user.target

[Service]
Type=idle
User=%(user)s
%(environments)s
ExecStart=%(binpath)s

[Install]
WantedBy=multi-user.target
"""

def gnrdaemonServiceBuilder():
    import pwd
    service_name = 'gnrdaemon'
    if 'VIRTUAL_ENV' in os.environ or hasattr(sys,'real_prefix'):
        pyprefix = os.environ.get('VIRTUAL_ENV', sys.prefix)
        environments = "Environment=VIRTUAL_ENV=%s" %pyprefix
        service_name = '%s_%s'%(service_name, os.path.basename(pyprefix))
    else:
        environments = ''
    current_username = pwd.getpwuid(os.getuid())[0]
    binpath = shutil.which('gnrdaemon')
    content = GNRDAEMON_SERVICE_TPL %dict(environments=environments,binpath=binpath, user= current_username)
    service_name = '%s.service'%service_name
    with open(service_name,'w') as service_file:
        service_file.write(content)
    print("""
Gnrdaemon service created Now run these commands:

$ sudo cp %(service_name)s /etc/systemd/system/%(service_name)s
$ sudo chmod 644 /etc/systemd/system/%(service_name)s
$ sudo systemctl daemon-reload  # Refresh the available service list
$ sudo systemctl enable %(service_name)s
$ sudo systemctl start %(service_name)s
...
$ sudo systemctl status %(service_name)s
$ sudo journalctl -e -u %(service_name)s
        """ % dict(service_name=service_name))


GNRSITERUNNERSERVICE_TPL = """
[Unit]
Description=%(service_name)s GnrSupervisorSiteRunner Service
After=multi-user.target

[Service]
Type=forking
%(environments)s
User=%(user)s
ExecStart=%(binpath)s
ExecReload=kill -HUP $MAINPID
ExecStop=%(ctl_binpath)s shutdown

[Install]
WantedBy=multi-user.target
"""

def gnrsiterunnerServiceBuilder():
    import pwd
    current_username = pwd.getpwuid(os.getuid())[0]
    daemon_path = shutil.which('supervisord')
    ctl_binpath = shutil.which('supervisorctl')
    service_name = 'gnrsiterunner'
    if 'VIRTUAL_ENV' in os.environ or hasattr(sys, 'real_prefix'):
        pyprefix = os.environ.get('VIRTUAL_ENV', sys.prefix)
        environments = f"Environment=VIRTUAL_ENV={pyprefix}"
        service_name = '%s_%s' % (service_name, os.path.basename(pyprefix))
    else:
        environments = ''
    gnr_path = gnrConfigPath()
    supervisor_conf_path_ini = os.path.join(gnr_path,'supervisord.conf')
    supervisor_log_path = os.path.join(gnr_path,'supervisord.log')
    binpath = '%s -c %s -l %s' % (daemon_path,supervisor_conf_path_ini,
        supervisor_log_path)
    content = GNRSITERUNNERSERVICE_TPL % dict(environments=environments, binpath=binpath,
                                              user=current_username, ctl_binpath=ctl_binpath,
                                              service_name=service_name)
    service_name = f'{service_name}.service'
    with open(service_name,'w') as service_file:
        service_file.write(content)
    print("""
Gnrsiterunner service created, now run these commands:

$ sudo cp %(service_name)s /etc/systemd/system/%(service_name)s
$ sudo chmod 644 /etc/systemd/system/%(service_name)s
$ sudo systemctl daemon-reload  # Refresh the available service list
$ sudo systemctl enable %(service_name)s

$ sudo systemctl start %(service_name)s
...
$ sudo systemctl status %(service_name)s
# Blah blah blah you should see something happy and green
# Want to check your logs?
$ sudo journalctl -e -u %(service_name)s
        """ % dict(service_name=service_name))

def activateVirtualEnv(path):
    bin_dir = os.path.join(path, 'bin')
    os.environ["PATH"] = os.pathsep.join([bin_dir] + os.environ.get("PATH", "").split(os.pathsep))
    base = os.path.dirname(bin_dir)
    os.environ["VIRTUAL_ENV"] = base
    IS_WIN = sys.platform == "win32"
    if IS_WIN:
        site_packages = os.path.join(base, "Lib", "site-packages")
    else:
        site_packages = os.path.join(base, "lib", "python{}".format(sys.version[:3]), "site-packages")

    prev = set(sys.path)
    site.addsitedir(site_packages)
    sys.real_prefix = sys.prefix
    sys.prefix = base

    new = list(sys.path)
    sys.path[:] = [i for i in new if i not in prev] + [i for i in new if i in prev]

def createVirtualEnv(name=None, copy_genropy=False, copy_projects=None, 
    branch=None):
    venv_path = os.path.join(os.getcwd(), name)
    logger.info('Creating virtual environment %s in %s' , name, venv_path)
    builder = EnvBuilder(with_pip=True)

    if os.name == "nt" or sys.platform == 'win32':
        use_symlinks = False
    else:
        use_symlinks = True
        
    builder = EnvBuilder(with_pip=True, symlinks=use_symlinks)
    builder.create(name)
        
    gitrepos_path = os.path.join(venv_path, 'gitrepos')
    if not os.path.exists(gitrepos_path):
        os.makedirs(gitrepos_path, exist_ok=True)
    base_path_resolver = _PathResolver()
    base_gnr_config = getGnrConfig()
    activateVirtualEnv(venv_path)
    if copy_projects:
        projects_path = os.path.join(gitrepos_path, 'genropy_projects')
        if not os.path.exists(projects_path):
            os.makedirs(projects_path, exist_ok=True)
        projects = copy_projects.split(',')
        for project in projects:
            prj_path = base_path_resolver.project_name_to_path(project)
            if prj_path:
                destpath = os.path.join(projects_path, project)
                logger.info('Copying project %s from %s to %s', project, prj_path, destpath)
                try:
                    shutil.copytree(prj_path, destpath)
                except shutil.Error as e:
                    logger.exception(e)

    if copy_genropy:
        newgenropy_path = os.path.join(gitrepos_path, 'genropy')
        
        genropy_path = base_gnr_config['gnr.environment_xml.environment.gnrhome?value']
        if genropy_path:
            logger.info('Copying genropy from %s to %s', genropy_path,newgenropy_path)
            shutil.copytree(genropy_path,newgenropy_path)
            import subprocess
            curr_cwd = os.getcwd()
            if branch:
                os.chdir(newgenropy_path)
                logger.info('Switching to branch %s', branch)
                subprocess.check_call(['git', 'stash'])
                subprocess.check_call(['git', 'fetch'])
                subprocess.check_call(['git', 'checkout', branch])
                subprocess.check_call(['git', 'pull'])
                os.chdir(curr_cwd)
            gnrpy_path = os.path.join(newgenropy_path,'gnrpy')
            pip_path = os.path.join(venv_path,'bin', 'pip')
            subprocess.check_call([pip_path, 'install', 'paver'])
            paver_path = os.path.join(venv_path,'bin', 'paver')
            os.chdir(gnrpy_path)
            subprocess.check_call([paver_path, 'develop'])
            initgenropy(gnrpy_path=gnrpy_path)
            os.chdir(curr_cwd)
    

def projectBag(project_name,packages=None,branches=None,exclude_branches=None):
    p=_PathResolver()
    result = Bag()
    branches = branches.split(',') if isinstance(branches, str) else (branches or [])
    packages = packages.split(',') if isinstance(packages, str) else (packages or [])

    dr = DirectoryResolver(p.project_name_to_path(project_name),include='*.py',dropext=True)
    for pkg,pkgval in list(dr['packages'].items()):
        if packages and pkg not in packages:
            continue
        packagecontent = Bag()
        result[pkg] = packagecontent
        for tbl in list(pkgval['model'].keys()):
            if tbl=='_packages':
                continue
            packagecontent['tables.%s' %tbl] = '%s.%s' %(pkg,tbl)
        for branch in branches:
            branchbag = Bag()
            packagecontent[branch.replace('.','_')] = branchbag
            branchval  = pkgval.pop(branch)
            if branchval:
                for path in branchval.getIndexList():
                    branchbag[path] = path.split('.')[-1]
    return result

    

################################# DEPLOY CONF BUILDERS ################################

GUNICORN_DEFAULT_CONF_TEMPLATE ="""

bind = 'unix:%(gunicorn_socket_path)s'
pidfile = '%(pidfile_path)s'
daemon = False
#accesslog = '%(logs_path)s/access.log'
errorlog = '%(logs_path)s/error.log'
logfile = '%(logs_path)s/main.log'
workers = %(workers)i
threads = %(threads)i
loglevel = 'error'
chdir = '%(chdir)s'
reload = False
capture_output = True
#worker_class = 'gevent'
max_requests = %(max_requests)i
max_requests_jitter = %(max_requests_jitter)i
timeout = 1800
graceful_timeout = 600
"""


NGINX_TEMPLATE = """
map $http_x_forwarded_proto $real_scheme {
            default $http_x_forwarded_proto;
            ''      $scheme;
}
server {
        listen 80;

        server_name %(domain)s;

        root %(site_path)s;

        error_log %(logs_path)s/nginx_error.log;
        proxy_connect_timeout       1800;
        proxy_send_timeout          1800;
        proxy_read_timeout          1800;
        send_timeout                1800;
        location /websocket {
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "Upgrade";
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $http_host;
            proxy_set_header X-Forwarded-Proto $real_scheme;
            proxy_pass http://unix:%(gnrasync_socket_path)s;
        }
        %(supervisord_location)s
        location / {
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $real_scheme;
            proxy_set_header Host $http_host;
            proxy_redirect off;
            proxy_pass http://unix:%(gunicorn_socket_path)s;
        }
}

"""

TRAEFIK_TEMPLATE = """
http:
  routers:
    {site_name}-main:
      rule: "Host(`{domain}`) && PathPrefix(`/`)"
      entryPoints:
        - websecure
      service: gunicorn-service
      middlewares:
        - common-headers
      tls:
        certResolver: letsencrypt

    {site_name}-websocket:
      rule: "Host(`{domain}`) && PathPrefix(`/websocket`)"
      entryPoints:
        - websecure
      service: websocket-service
      middlewares:
        - websocket-headers
      tls:
        certResolver: letsencrypt

    {site_name}-http-redirect:
      rule: "Host(`{domain}`)"
      entryPoints:
        - web
      middlewares:
        - redirect-to-https
      service: noop

  services:
    gunicorn-service:
      loadBalancer:
        servers:
          - url: "http://unix//{gunicorn_socket_path}"

    websocket-service:
      loadBalancer:
        servers:
          - url: "http://unix//{gnrasync_socket_path}"

    noop:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1"

  middlewares:
    redirect-to-https:
      redirectScheme:
        scheme: https
        permanent: true

    common-headers:
      headers:
        customRequestHeaders:
          X-Forwarded-Proto: "https"

    websocket-headers:
      headers:
        customRequestHeaders:
          Connection: "Upgrade"
          Upgrade: "websocket"
          X-Forwarded-Proto: "https"
"""

class GunicornDeployBuilder(object):
    default_port = 8080
    default_processes = 1
    default_threads = 8
    conf_template = GUNICORN_DEFAULT_CONF_TEMPLATE
    
    

    def __init__(self, site_name, **kwargs):
        self.site_name = site_name
        self.path_resolver = _PathResolver()
        self.site_path = self.path_resolver.site_name_to_path(site_name)
        self.instance_path = self.path_resolver.instance_name_to_path(site_name)
        self.site_config = self.path_resolver.get_siteconfig(site_name)
        self.instance_config = self.path_resolver.get_instanceconfig(site_name)
        if os.path.exists(os.path.join(self.site_path,'siteconfig.xml')):
            self.config_folder = self.site_path #oldconfig
        else:
            self.config_folder = os.path.join(self.instance_path,'config')
        self.gnr_path = gnrConfigPath()
        self.supervisor_conf_path_py = os.path.join(self.gnr_path,'supervisord.py') 
        self.supervisor_conf_path_ini = os.path.join(self.gnr_path,'supervisord.conf')
        self.supervisor_log_path = os.path.join(self.gnr_path,'supervisord.log')
        self.supervisord_socket_path = os.path.join(self.gnr_path,'supervisord.sock')
        self.supervisord_monitor_parameters = self.path_resolver.gnr_config.getAttr('gnr.environment_xml.supervisord')
        self.bin_folder = os.path.join(os.environ.get('VIRTUAL_ENV'),'bin') if 'VIRTUAL_ENV' in  os.environ else ''
        self.socket_path = os.path.join(self.site_path, 'sockets')
        if len(self.socket_path)>90:
            self.socket_path = os.path.join('/tmp', os.path.basename(self.instance_path), 'gnr_sock')
        self.logs_path = os.path.join(self.site_path, 'logs')
        self.pidfile_path = os.path.join(self.site_path, '%s_pid' % site_name)
        self.gunicorn_conf_path = os.path.join(self.config_folder,'gunicorn.py')
        self.gnrasync_socket_path = os.path.join(self.socket_path, "async.tornado" )
        self.gunicorn_socket_path = os.path.join(self.socket_path,'gunicorn.sock')
        

        self.create_dirs()

        self.default_workers = multiprocessing.cpu_count() + 1
        self.default_max_requests = 300
        self.default_max_requests_jitter = 50
        self.options = kwargs

    def create_dirs(self):
        for dir_path in (self.socket_path,self.logs_path):
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)

    def write_gunicorn_conf(self):
        pars = dict()
        opt = self.options
        pars['gunicorn_socket_path'] = self.gunicorn_socket_path
        pars['pidfile_path'] = self.site_name
        pars['workers'] = int(opt.get('workers') or self.default_workers)
        pars['threads'] = int(opt.get('threads') or self.default_threads)

        pars['pidfile_path'] = self.pidfile_path
        pars['site_path'] = self.site_path
        pars['logs_path'] = self.logs_path
        pars['max_requests'] = self.default_max_requests
        pars['max_requests_jitter'] = self.default_max_requests_jitter
        pars['chdir'] = self.site_path if os.path.exists(os.path.join(self.site_path,'root.py')) else self.instance_path
        conf_content = GUNICORN_DEFAULT_CONF_TEMPLATE %pars
        logger.info('Writing gunicorn conf file at %s', self.gunicorn_conf_path)

        # ensure the directory exists before writing the file, to support
        # older instances with new deploys
        gunicorn_base_conf_dir = os.path.dirname(self.gunicorn_conf_path)
        pathlib.Path(gunicorn_base_conf_dir).mkdir(parents=True, exist_ok=True)
        
        with open(self.gunicorn_conf_path,'w') as conf_file:
            conf_file.write(conf_content)

    def local_supervisor_conf(self):
        root = IniConfStruct()
        supervisord = root.section(u"supervisord")
        supervisord.parameter("nodaemon",value="true")
        group = root.section('group',self.site_name)
        gunicorn = group.section('program','%s_gunicorn' %self.site_name)
        gunicorn.parameter('command','%s -c %s root' %(os.path.join(self.bin_folder,'gunicorn'),self.gunicorn_conf_path))
        gunicorn.parameter('stdout_logfile','/dev/stdout')
        gunicorn.parameter('stdout_logfile_maxbytes','0')
        gunicorn.parameter('stderr_logfile','/dev/stderr')
        gunicorn.parameter('stderr_logfile_maxbytes','0')

        gnrasync = group.section('program', f'{self.site_name}_gnrasync')
        gnrasync.parameter('command', f"{os.path.join(self.bin_folder,'gnrasync')} {self.site_name}")

        
        from gnr.web.gnrtask import USE_ASYNC_TASKS
        if USE_ASYNC_TASKS:
            self.taskSchedulerConf(group)

        self.taskWorkersConf(group)
        root.toIniConf(os.path.join(self.config_folder,'supervisord.conf'))

    def taskSchedulerConf(self, group):
        """
        create the configuration to start the local task scheduler
        """
        has_sys = 'gnrcore:sys' in self.instance_config['packages']
        secondary = has_sys and self.instance_config['packages'].getAttr('gnrcore:sys').get('secondary')
        if not has_sys or secondary:
            return
        scheduler_section = group.section("program", f"{self.site_name}_taskscheduler")
        scheduler_section.parameter("process_name", f"{self.site_name}_gnrtaskscheduler")
        scheduler_section.parameter('command', f'{os.path.join(self.bin_folder,"gnr")} web taskscheduler {self.site_name}')
        
    def taskWorkersConf(self,group):
        """
        create the configuration to start the local task worker
        """
        taskworkers = self.site_config.getAttr('taskworkers') or {'count':'1'}
        has_sys = 'gnrcore:sys' in self.instance_config['packages']
        secondary = has_sys and self.instance_config['packages'].getAttr('gnrcore:sys').get('secondary')
        if not has_sys or secondary:
            return
        if taskworkers:
            tw_base = group.section('program', f'{self.site_name}_taskworkers')
            nice = taskworkers.pop('nice', None)
            nicecommand = 'nice' if nice is None else 'nice -%s' %nice
            tw_base.parameter('process_name', f"{self.site_name}_gnrtaskworker%%(process_num)s")
            tw_base.parameter('command', f"{nicecommand} {os.path.join(self.bin_folder,'gnr')} web taskworker {self.site_name}")
            tw_base.parameter('numprocs',taskworkers.pop('count','1'))
            for key,val in taskworkers.items():
                command,key = key.split('_')
                if command=='nice':
                    continue
                subnice = taskworkers.get('nice_%s' %key,nice)
                subnicecommand = 'nice' if subnice is None else nicecommand
                tw =  group.section('program','%s_taskworkers_%s' %(self.site_name,key))
                tw.parameter('process_name',"%s_gnrtaskworker_%s_%%(process_num)s" %(self.site_name,key))
                tw.parameter('command','%s %s %s --code %s' %(subnicecommand,os.path.join(self.bin_folder,'gnrtaskworker'),self.site_name,key))
                tw.parameter('numprocs',val)


    def main_supervisor_conf(self):
        if os.path.isfile(self.supervisor_conf_path_py):
            root = IniConfStruct(self.supervisor_conf_path_py)
        else:
            root = IniConfStruct()
            supervisord = root.section(u"supervisord")
            supervisord.parameter("loglevel",value="error")
        root.pop(self.site_name)    
        root.pop('xmlrpcmonitor')
        root.pop('rpcinterface_supervisor')       
        group = root.section('group',self.site_name)
        gunicorn = group.section('program','%s_gunicorn' %self.site_name)
        gunicorn.parameter('command','%s -c %s root' %(os.path.join(self.bin_folder,'gunicorn'),self.gunicorn_conf_path))
        gnrasync = group.section('program','%s_gnrasync' %self.site_name)
        gnrasync.parameter('command','%s %s' %(os.path.join(self.bin_folder,'gnrasync'),self.site_name))

        from gnr.web.gnrtask import USE_ASYNC_TASKS
        if USE_ASYNC_TASKS:
            self.taskSchedulerConf(group)
            
        self.taskWorkersConf(group)
        if self.supervisord_monitor_parameters:
            self.xmlRpcServerConf(root)
        rms = group.section('program','%s_rms' %self.site_name)
        rms.parameter('command','%s %s' %(os.path.join(self.bin_folder,'gnrrms'),self.site_name))
        root.toPython(self.supervisor_conf_path_py)
        root.toIniConf(self.supervisor_conf_path_ini)

    def xmlRpcServerConf(self,root):
        mp = self.supervisord_monitor_parameters
        if mp.get('port'):
            sec = root.section(u"inet_http_server",label='xmlrpcmonitor')
            sec.parameter("port",value='*:%(port)s' %mp)
            sec.parameter('username',value=mp['username'])
            sec.parameter('password',value=mp['password'])
        else:
            sec = root.section(u"unix_http_server",label='xmlrpcmonitor')
            sec.parameter("file",value=self.supervisord_socket_path)
            sec.parameter('chmod',value=mp.get('chmod','0777'))
            sec.parameter('chown',value=mp.get('chown','nobody:nogroup'))
            sec.parameter('username',value=mp['username'])
            sec.parameter('password',value=mp['password'])
        sec = root.section("rpcinterface",name='supervisor',label='rpcinterface_supervisor')
        sec.parameter('supervisor.rpcinterface_factory',value='supervisor.rpcinterface:make_main_rpcinterface')

    def supervisord_monitor_location(self):
        mp = self.supervisord_monitor_parameters
        if not mp or mp.get('port'):
            return ''
        
        return """
        location /supervisord {
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "Upgrade";
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $http_host;
            proxy_set_header X-Forwarded-Proto $real_scheme;
            proxy_pass http://unix:%(supervisord_socket_path)s;
        }""" %{'supervisord_socket_path':self.supervisord_socket_path }


    def write_nginx_conf(self,domain=None):
        pars = {}
        pars['domain'] = domain
        pars['site_path'] = self.site_path
        pars['logs_path'] = self.logs_path
        pars['gnrasync_socket_path'] = self.gnrasync_socket_path
        pars['gunicorn_socket_path'] = self.gunicorn_socket_path
        pars['supervisord_location'] = self.supervisord_monitor_location()
        conf_content = NGINX_TEMPLATE % pars
        filename = f"{self.site_name}.conf"
        with open(filename,'w') as conf_file:
            conf_file.write(conf_content)
        return filename
    
    def write_traefik_conf(self,domain=None):
        pars = {}
        pars['domain'] = domain
        pars['site_name'] = self.site_name
        pars['site_path'] = self.site_path
        pars['logs_path'] = self.logs_path
        pars['gnrasync_socket_path'] = self.gnrasync_socket_path
        pars['gunicorn_socket_path'] = self.gunicorn_socket_path
        pars['supervisord_location'] = self.supervisord_monitor_location()
        conf_content = TRAEFIK_TEMPLATE.format(**pars)
        filename = f"{self.site_name}-traefik.yaml"
        with open(filename,'w') as conf_file:
            conf_file.write(conf_content)
        return filename
