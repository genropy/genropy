#!/usr/bin/env python
# encoding: utf-8
"""
create a new genroproject
usage: gnrmkproject projectname

"""

import os

from gnr.core.cli import GnrCliArgParse
from gnr.core.gnrbag import Bag
from gnr.app.gnrapp import GnrApp
from gnr.app.gnrdeploy import ProjectMaker, InstanceMaker, SiteMaker,PackageMaker, PathResolver

description = "Bootstrap a new project folder and subfolders"

def main():
    parser = GnrCliArgParse()
    parser.add_argument("-b", "--base-path", dest="base_path",
                      help="base path where project will be created")
    parser.add_argument("-i", "--create-instance", dest="create_instance", default=False,
                      help="create instance")
    parser.add_argument("-a", "--create-all", dest="create_all", action='store_true', default=False,
                      help="create both site and instance")
    parser.add_argument("-p", "--wsgi-port", dest="wsgi_port", default='8080',
                      help="Specify WSGI port")
    parser.add_argument("-r", "--wsgi-reload", dest="wsgi_reload", default=True,
                      help="Specify WSGI autoreload")
    parser.add_argument("-d", "--wsgi-debug", dest="wsgi_debug", default=True,
                      help="Specify WSGI debug")
    parser.add_argument("-P", "--main-package", dest="main_package", help="Main Package")
    parser.add_argument("-A", "--add-packages", dest="add_packages", help="Add Packages")
    parser.add_argument('--helloworld',help="Create helloworld page",action='store_true',default=False)
    parser.add_argument('--dbdemo',help="Create some tables to show gnrsql",action='store_true',default=False)
    parser.add_argument("project_name")
    
    options = parser.parse_args()
    
    base_path = options.base_path
    create_all = options.create_all
    create_instance = options.create_instance or create_all
    main_package = options.main_package
    add_packages = options.add_packages
    helloworld = options.helloworld
    
    if helloworld:
        if not main_package:
            main_package = 'hello'
            if not create_instance:
                create_instance = 'baseinstance'
                
    project_name = options.project_name
    if '.' in project_name:
        path_resolver = PathResolver()
        repo_name, project_name = project_name.split('.')
        base_path = base_path or path_resolver.project_repository_name_to_path(repo_name)
    print('Creating project %s in %s...' % (project_name, base_path or 'current directory'))
    project_maker = ProjectMaker(project_name, base_path=base_path)
    print('Project %s created' % project_name)
    project_maker.do()
    packages = [x.strip() for x in add_packages.split(',')] if add_packages else []
    
    if main_package:
        package_maker = PackageMaker(main_package,base_path=os.path.join((base_path or '.'),
                                                                         project_name,'packages'),helloworld=helloworld)
        package_maker.do()
        packages.append(main_package)

    if create_instance:
        if create_instance is True:
            create_instance = project_name
        print('Creating instance %s in %s...' % (create_instance, project_maker.instances_path))
        instance_maker = InstanceMaker(create_instance, base_path=project_maker.instances_path,packages=packages,main_package=main_package)
        instance_maker.do()
        print('Instance %s created' % create_instance)

if __name__ == '__main__':
    main()
