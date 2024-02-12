#!/usr/bin/env python
# encoding: utf-8
import re
import os

from subprocess import Popen

from gnr.core.cli import GnrCliArgParse
from gnr.core.gnrbag import Bag
from gnr.app.gnrapp import GnrApp
from gnr.app.gnrconfig import gnrConfigPath, getGnrConfig,IniConfStruct
from gnr.web.gnrdaemonhandler import GnrDaemonProxy


APACHE_SITES ='/etc/apache2/sites-enabled'

UWSGIVASSALFINDER = re.compile(r'(?:^pyargv *= *)(\w+)$',re.I |re.M)
APACHECONFFINDER = re.compile(r'(?:WSGIScriptAlias[ /\w]*sites/)(\w*)(?:/root\.py)$',re.I |re.M)

class BaseUpdater(object):
    def __init__(self,instances=None,daemonRestart=None,skip_dbsetup=False,upgrade=None,**kwargs):
        self.instances = self.getInstances()
        self.daemonRestart = daemonRestart
        self.daemonProxy = GnrDaemonProxy(use_environment=True)
        self.stoppedStatus = None
        self.skip_dbsetup = skip_dbsetup
        self.upgrade = upgrade
        if instances:
            self.instances = [inst for inst in instances.split(',') if inst in self.instances]

    def instanceBroadcast(self,cb,**kwargs):
        if not isinstance(cb,list):
            cb = [cb]
        for instance in self.instances:
            for callback in cb:
                print(callback.__name__,'Instance ',instance)
                try:
                    callback(instance,**kwargs)
                except Exception as e:
                    print(e)

    def dbsetup(self,instance=False):
        app = GnrApp(instance)
        db = app.db
        dbstores =[None]
        if db.dbstores:
            dbstores.extend(list(db.dbstores.keys()))
        for storename in dbstores:
            self.dbsetup_one(db,storename=storename)

    def dbsetup_one(self,db,storename=None):
        print('\t running dbsetup ',storename or '')
        with db.tempEnv(storename=storename):
            changes = self.check_db(db)
            if changes:
                print('APPLYING CHANGES TO DATABASE...')
                db.model.applyModelChanges()
                print('CHANGES APPLIED TO DATABASE')
                db.application.pkgBroadcast('onDbSetup,onDbSetup_*')
            if self.upgrade:
                print('RUN UPGRADE')
                db.application.pkgBroadcast('onDbUpgrade,onDbUpgrade_*')
                db.table('sys.upgrade').runUpgrades()
            db.closeConnection()

    def gnrdaemon_restart(self):
        self.gnrdaemon_stop()
        self.gnrdaemon_start()
    
    def web_maintenance(self,status=None):
        with self.daemonProxy.proxy() as p:
            registers = p.siteRegisters()
            if registers:
                registers = dict(registers)
            for sitename in self.instances:
                if sitename in registers:
                    print('setting in maintenance',sitename,status)
                    p.setSiteInMaintenance(sitename,status=status)
                else:
                    print('not found in register',sitename)

    def gnrdaemon_stop(self):
        with self.daemonProxy.proxy() as p:
            self.stoppedStatus = p.siteregister_stop(self.instances,saveStatus=self.daemonRestart=='keep')

    def gnrdaemon_start(self):
        with self.daemonProxy.proxy() as p:
            p.siteregister_start(self.stoppedStatus)

    def check_db(self,db):
        changes = db.model.check()
        dbname = db.currentEnv.get('storename')
        dbname = dbname or 'Main'
        print('DB %s:' % dbname)
        if changes:
            print('STRUCTURE NEEDS CHANGES')
        else:
            print('STRUCTURE OK')
        return changes

    def update(self):
        #instances = [os.path.splitext(l)[0] for l in os.listdir(self.vassals_path) if l not in ('gnrdaemon.ini','pg.ini')]
        self.web_maintenance(True)
        self.web_stop()
        if self.daemonRestart=='keep':
            self.gnrdaemon_restart()
            self.web_maintenance(True)
        elif self.daemonRestart=='clean':
            self.gnrdaemon_stop()
        if not self.skip_dbsetup:
            self.instanceBroadcast(self.dbsetup)
        if self.daemonRestart=='clean':
            self.gnrdaemon_start()
            self.web_maintenance(True)
        self.web_start()
        self.web_maintenance(False)
        print('Update ok')

class ApacheUpdater(BaseUpdater):
    def __init__(self,**kwargs):
        super(ApacheUpdater,self).__init__(**kwargs)

    def web_stop(self):
        #sudo apache2ctl stop
        print('stop apache')
        Popen(['sudo apache2ctl stop'], shell=True)


    def web_start(self):
        #sudo apache2ctl start
        print('start apache')
        Popen(['sudo apache2ctl start'], shell=True)

    def getInstances(self):
        result = []
        for filename in os.listdir(APACHE_SITES):
            with open(os.path.join(APACHE_SITES,filename),'r') as f:
                txt = f.read()
                q = APACHECONFFINDER.search(txt)
                if q:
                    result.append(q.group(1))
        return list(set(result))

class GunicornUpdater(BaseUpdater):
    def __init__(self,**kwargs):
        self.gnr_vassal_options = dict()
        self.gnr_config = getGnrConfig()
        self.gnr_path = gnrConfigPath()
        conf = IniConfStruct(os.path.join(self.gnr_path,'supervisord.py'))
        self.instances = [r for r in conf.digest('#a.name') if r]
        super(GunicornUpdater,self).__init__(**kwargs)

    def web_stop(self):
        #sudo apache2ctl stop
        print('gnrsiterunner stop')
        Popen(['sudo service gnrsiterunner stop'], shell=True)


    def web_start(self):
        #sudo apache2ctl start
        print('gnrsiterunner start')
        Popen(['sudo service gnrsiterunner start'], shell=True)

    def getInstances(self):
        return self.instances

class UwsgiUpdater(BaseUpdater):
    def __init__(self,**kwargs):
        self.gnr_vassal_options = dict()
        self.gnr_config = getGnrConfig()
        self.gnr_path = gnrConfigPath()
        self.socket_path = os.path.join(self.gnr_path, 'sockets')
        home_path = os.environ.get('HOME', '')
        if home_path.startswith('/containers'):
            default_vassals_path = os.path.join(home_path, 'vassals')
        else:
            default_vassals_path = os.path.join(self.gnr_path, 'uwsgi', 'vassals')
        self.vassals_path = self.gnr_config['gnr.environment_xml.vassals?path'] or default_vassals_path
        #self.vassals_path = os.path.join(self.gnr_path, 'uwsgi', 'vassals')
        for dir_path in (self.socket_path, self.vassals_path):
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        super(UwsgiUpdater,self).__init__(**kwargs)

    def getInstances(self):
        result = []
        for filename in os.listdir(self.vassals_path):
            basename, extension = os.path.splitext(filename)
            if basename.lower() in ('gnrdaemon', 'pg') or extension.lower() not in ('.ini', '.off'):
                continue
            with open(os.path.join(self.vassals_path,filename),'r') as f:
                txt = f.read()
                q = UWSGIVASSALFINDER.search(txt)
                if q:
                    result.append(q.group(1))
                else:
                    print(filename,txt)
        return list(set(result))

    def web_stop(self):
        self.instanceBroadcast(self.stop_vassal)

    def web_start(self):
        self.instanceBroadcast(self.start_vassal)

    def stop_vassal(self,name):
        vassal_start_path = os.path.join(self.vassals_path,'%s.ini' %name)
        vassal_off_path = os.path.join(self.vassals_path, '%s.off' %name)
        if os.path.exists(vassal_start_path):
            os.rename(vassal_start_path, vassal_off_path)
            print("Site %s stopped" % name)

    def start_vassal(self,name):
        vassal_start_path = os.path.join(self.vassals_path,'%s.ini' %name)
        vassal_off_path = os.path.join(self.vassals_path, '%s.off' %name)
        if os.path.exists(vassal_off_path):
            os.rename(vassal_off_path, vassal_start_path)
            print("Site %s start" % name)

    def restart_vassal(self,name):
        vassal_path = os.path.join(self.vassals_path,'%s.ini' %name)
        if os.path.exists(vassal_path):
            with open(vassal_path, 'a'):
                os.utime(vassal_path,None)
            print("Vassal %s restarted" % name)

description = "update something (FIXME)"
def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('--stop',
                        dest='stop',
                        action='store_true',
                        help="Stop web")
    parser.add_argument('--nodbsetup',
                        dest='skip_dbsetup',
                        action='store_true',
                        help="Touch all vassals and gnrdaemon, skips dbsetup")
    parser.add_argument('--upgrade',
                        dest='data_upgrade',
                        action='store_true',
                        help="Run upgrade scripts")
    parser.add_argument('--daemon_keep',
                        dest='daemon_keep',
                        action='store_true',
                        help="Restart gnrdaemon saving status")
    parser.add_argument('--daemon_clean',
                        dest='daemon_clean',
                        action='store_true',
                        help="Restart gnrdaemon clean status")
    parser.add_argument('--apache',
                        dest='apache',
                        action='store_true',
                        help="Apache")
    parser.add_argument('--uwsgi',
                        dest='uwsgi',
                        action='store_true',
                        help="Uwsgi")  
    parser.add_argument('--gunicorn',
                        dest='gunicorn',
                        action='store_true',
                        help="Gunicorn")  
    parser.add_argument("instances", nargs="+")
    
    options = parser.parse_args()
    instances = options.instances

    if not(options.apache or options.uwsgi or options.gunicorn):
        print('select an option')
        return
    
    daemonRestart = False
    if options.daemon_keep:
        daemonRestart = 'keep'
    if options.daemon_clean:
        daemonRestart = 'clean'
    kw = dict(instances=instances,daemonRestart= daemonRestart,
              skip_dbsetup=options.skip_dbsetup,upgrade=options.data_upgrade)

    if options.apache:
        updater = ApacheUpdater(**kw)
    elif options.uwsgi:
        updater = UwsgiUpdater(**kw)
    elif options.gunicorn:
        updater = GunicornUpdater(**kw)
    if options.stop:
        updater.web_stop()
    else:
        updater.update()


if __name__ == '__main__':
    main()
