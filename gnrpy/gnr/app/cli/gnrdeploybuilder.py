#!/usr/bin/env python
# encoding: utf-8

"""
create a new deploy gunicorn nginx websocket environment for a site
usage: gnrdeploybuilder site

"""
import os
import sys

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrdeploy import GunicornDeployBuilder, gnrdaemonServiceBuilder
from gnr.app.gnrdeploy import gnrsiterunnerServiceBuilder,createVirtualEnv

description = "create nginx vhosts, siterunner systemd service, virtualenvs, gnrdaemon services"

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument("-d", "--domain", dest="domain",
                      help="The nginx domain")
    parser.add_argument('-s', '--make_service',dest='make_service',
                      action="store_true", help="Make service")
    parser.add_argument('-e', '--make_virtualenv',dest='make_virtualenv',
                       help="Make virtualenv")
    parser.add_argument('-g', '--make_gnrdaemon',dest='make_gnrdaemon',
                       action="store_true", help="Make gnrdaemon service")
    parser.add_argument('-c', '--copy_genropy',dest='copy_genropy',
                      action="store_true", help="Copy genropy")
    parser.add_argument('-p', '--copy_projects',dest='copy_projects',
                       help="Copy projects")
    parser.add_argument('-b', '--branch',dest='branch',
                       help="Switch in genropy branch (if making a virtualenv and copy_genropy is set)")
    parser.add_argument('site', nargs='?')
    
    options = parser.parse_args()
    site = options.site
    if not (site or options.make_virtualenv or options.make_gnrdaemon or options.make_service):
        parser.print_help()
        
    if options.make_virtualenv:
        createVirtualEnv(name=options.make_virtualenv, copy_genropy=options.copy_genropy,
            branch=options.branch, copy_projects=options.copy_projects)
    if site:
        deployer = GunicornDeployBuilder(site)
        deployer.write_gunicorn_conf()
        deployer.local_supervisor_conf()
        deployer.main_supervisor_conf()
        if options.domain:
            print('Writing nginx conf in cwd please copy in /etc/nginx/sites-enabled')
            deployer.write_nginx_conf(options.domain)

    if options.make_gnrdaemon:
        gnrdaemonServiceBuilder()

    if options.make_service:
        gnrsiterunnerServiceBuilder()

if __name__ == '__main__':
    main()
