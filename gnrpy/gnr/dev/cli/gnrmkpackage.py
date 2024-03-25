#!/usr/bin/env python
# encoding: utf-8

import sys, os, shutil

from gnr.core.cli import GnrCliArgParse
from gnr.core.gnrbag import Bag
from gnr.app.gnrapp import GnrApp
from gnr.app.gnrdeploy import PackageMaker, PathResolver

description = """Create a new Genropy package"""

def main():
    parser = GnrCliArgParse()
    parser.add_argument("-b", "--base-path", dest="base_path",
                      help="base path where project will be created")
    parser.add_argument("packagename", nargs=1)
    
    options = parser.parse_args()
    base_path = getattr(options, 'base_path', None)
    package_name = options.packagename[0]
    
    if '.' in package_name:
        path_resolver = PathResolver()
        project_name, package_name = package_name.split('.')
        base_path = base_path or os.path.join(path_resolver.project_name_to_path(project_name), 'packages')
    print('Creating package %s in %s...' % (package_name, base_path or 'current directory'))
    package_maker = PackageMaker(package_name, base_path=base_path)
    print('Package %s created' % package_name)
    package_maker.do()

if __name__ == '__main__':
    main()
