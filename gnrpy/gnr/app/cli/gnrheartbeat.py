#!/usr/bin/env python
# encoding: utf-8
import os
import sys
import glob
import time

import urllib.request, urllib.parse, urllib.error

from gnr.core.cli import GnrCliArgParse
from gnr.core.gnrbag import Bag
from gnr.core.gnrsys import expandpath
from gnr.app.gnrconfig import getGnrConfig


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


def get_site_config( site_path, gnr_config):
    site_config_path = os.path.join(site_path, 'siteconfig.xml')
    base_site_config = Bag(site_config_path)
    site_config = gnr_config['gnr.siteconfig.default_xml'] or Bag()
    template = site_config['site?template'] 
    if template:
        site_config.update(gnr_config['gnr.siteconfig.%s_xml' % template] or Bag())
    if 'sites' in gnr_config['gnr.environment_xml']:
        for path, site_template in gnr_config.digest('gnr.environment_xml.sites:#a.path,#a.site_template'):
            if path == os.path.dirname(site_path):
                site_config.update(gnr_config['gnr.siteconfig.%s_xml' % site_template] or Bag())
    site_config.update(Bag(site_config_path))
    return site_config

def get_site_url(site_name):
    gnr_config = getGnrConfig(set_environment=True)
    if site_name:
        site_path = site_name_to_path(gnr_config, site_name)
        if not site_path:
            site_path = os.path.join(gnr_config['gnr.environment_xml.sites?path'] or '', site_name)
        if not site_path:
            print('no site named %s found'%site_name)
            exit(-1)
        else:
            site_config = get_site_config(site_path, gnr_config)
            return 'http://localhost:%s'%site_config['wsgi?port']

description = "heartbeat"

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('-v', '--verbose',
                      dest='verbose',
                      action='store_true',
                      help="Verbose mode")
    
    parser.add_argument('-s', '--site',
                      dest='site_opt',
                      help="Use command on instance identified by supplied site")

    parser.add_argument("site", nargs="*")
    
    parser.add_argument('--interval',
                      dest='interval',
                      default=60,
                      help="Heartbeat interval (in seconds)")

    options = parser.parse_args()
    
    site_name = options.site and options.site[0] or options.site_opt or None

    if site_name is None:
        parser.print_help()
        sys.exit(1)
        
    if not site_name.startswith('http://') or site_name.startswith('https://'):
        site_url = get_site_url(site_name)
    else:
        site_url = site_name
    url = f"{site_url}/sys/heartbeat"
    
    while True:
        if options.verbose:
            print('Calling url %s'%url)
        try:
            response = urllib.request.urlopen(url)
            response_code = response.getcode()
            if response_code != 200:
                if options.verbose:
                    print('Response code: %s'%response_code)
            time.sleep(options.interval)
        except IOError:
            print('IOError -> will retry in {} seconds'.format(3*options.interval))
            time.sleep(3*options.interval)
        
if __name__ == '__main__':
    main()
        
        
