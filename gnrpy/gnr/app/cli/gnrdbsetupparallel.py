#!/usr/bin/env python
# encoding: utf-8
import os
import glob
from multiprocessing import Pool

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapp import GnrApp
from gnr.core.gnrsys import expandpath
from gnr.core.gnrlog import enable_colored_logging
from gnr.app.gnrconfig import getGnrConfig

enable_colored_logging()

S_GNRHOME = os.path.split(os.environ.get('GNRHOME', '/usr/local/genro'))
GNRHOME = os.path.join(*S_GNRHOME)
S_GNRINSTANCES = (os.environ.get('GNRINSTANCES') and os.path.split(os.environ.get('GNRINSTANCES'))) or (
S_GNRHOME + ('data', 'instances'))
GNRINSTANCES = os.path.join(*S_GNRINSTANCES)

description = "create/update/check database models in Genro framework (parallel)"
def site_name_to_path(gnr_config, site_name):
    path_list = []
    if 'sites' in gnr_config['gnr.environment_xml']:
        path_list.extend([expandpath(path) for path in gnr_config['gnr.environment_xml'].digest('sites:#a.path') if
                          os.path.isdir(expandpath(path))])
    if 'projects' in gnr_config['gnr.environment_xml']:
        projects = [expandpath(path) for path in gnr_config['gnr.environment_xml'].digest('projects:#a.path') if
                    os.path.isdir(expandpath(path))]
        for project_path in projects:
            path_list.extend(glob.glob(os.path.join(project_path, '*/sites')))
        for path in path_list:
            site_path = os.path.join(path, site_name)
            if os.path.isdir(site_path):
                return site_path
        raise Exception(
                'Error: no site named %s found' % site_name)

def instance_name_to_path(gnr_config, instance_name):
    path_list = []
    if 'instances' in gnr_config['gnr.environment_xml']:
        path_list.extend([expandpath(path) for path in gnr_config['gnr.environment_xml'].digest('instances:#a.path') if
                          os.path.isdir(expandpath(path))])
    if 'projects' in gnr_config['gnr.environment_xml']:
        projects = [expandpath(path) for path in gnr_config['gnr.environment_xml'].digest('projects:#a.path') if
                    os.path.isdir(expandpath(path))]
        for project_path in projects:
            path_list.extend(glob.glob(os.path.join(project_path, '*/instances')))
        for path in path_list:
            instance_path = os.path.join(path, instance_name)
            if os.path.isdir(instance_path):
                return instance_path
        raise Exception(
                'Error: no instance named %s found' % instance_name)


def get_app_path_and_store(options):
    storename = None
    if options.directory:
        instance_path = options.directory
        if os.path.isdir(instance_path):
            return instance_path
        else:
            raise Exception("No valid instance provided")
    gnr_config = getGnrConfig(config_path=options.config_path,
                              set_environment=True)
    instance_name = options.instance
    if instance_name:
        if '.' in instance_name:
            instance_name, storename = instance_name.split('.')
        instance_path = instance_name_to_path(gnr_config, instance_name)
        if os.path.isdir(instance_path):
            return instance_path, storename
        else:
            raise Exception("No valid instance provided")
    if options.site:
        site_path = site_name_to_path(gnr_config, options.site)
        if not site_path:
            site_path = os.path.join(gnr_config['gnr.environment_xml.sites?path'] or '', options.site)
        instance_path = os.path.join(site_path, 'instance')
        if os.path.isfile(os.path.join(instance_path, 'instanceconfig.xml')):
            return instance_path, storename
        else:
            raise "No valid instance provided"
    return os.getcwd(), storename


def check_db(app, options):
    changes = app.db.model.check()
    dbname = app.db.currentEnv.get('storename')
    dbname = dbname or 'Main'
    print('DB %s:' % dbname)
    if changes:
        if options.verbose:
            print('*CHANGES:\n%s' % '\n'.join(app.db.model.modelChanges))
        else:
            print('STRUCTURE NEEDS CHANGES')
    else:
        print('STRUCTURE OK')
    return changes

def import_db(app,filepath):
    app.db.importXmlData(filepath)
    app.db.commit()

def check_store(args):
    instance_path, storename, options = args
    app = GnrApp(instance_path, debug=options['debug'])
    app.db.use_store(storename)
    if options.check:
        check_db(app)
    elif options.import_file:
        import_db(app, options.import_file)
    else:
        changes = check_db(app)
        if changes:
            print('APPLYING CHANGES TO DATABASE...')
            app.db.model.applyModelChanges()
            print('CHANGES APPLIED TO DATABASE')
        app.db.model.checker.addExtesions()
    app.db.closeConnection()

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('-c', '--check',
                        dest='check',
                        action='store_true',
                        help="Check only, don't apply changes")
    parser.add_argument('-v', '--verbose',
                        dest='verbose',
                        action='store_true',
                        help="Verbose mode")
    parser.add_argument('-d', '--debug',
                        dest='debug',
                        default=False,
                        action='store_true',
                        help="Debug mode")
    parser.add_argument('-i', '--instance',
                        dest='instance',
                        help="Use command on instance identified by supplied name")
    parser.add_argument('-D', '--directory',
                        dest='directory',
                        help="Use command on instance identified by supplied directory (overrides -i)")
    parser.add_argument('-s', '--site',
                        dest='site',
                        help="Use command on instance identified by supplied site")
    parser.add_argument('-I', '--import',
                        dest='import_file',
                        help="Import specified XML file")
    parser.add_argument('--config',
                        dest='config_path',
                        help="gnrserve file path")
    parser.add_argument('instance', nargs='?')
    
    options = parser.parse_args()
    

    p = Pool(6)
    instance_path, storename = get_app_path_and_store(options)
    if storename == '*':
        app = GnrApp(instance_path)
        stores = [None] + list(app.db.dbstores.keys())
    else:
        stores = [storename]
    options_dict = options.__dict__
    starstores = [(instance_path,store,options_dict) for store in sorted(stores)]
    p.map(check_store,starstores)
    
if __name__ == '__main__':
    main()

