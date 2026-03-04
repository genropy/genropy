#!/usr/bin/env python
# encoding: utf-8

import os

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrdeploy import SiteMaker, PathResolver

description = "Create a new Genropy site"
def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument("-b", "--base-path", dest="base_path",
                      help="base path where project will be created")
    parser.add_argument("site_name", nargs=1)
    

    options = parser.parse_args()
    base_path = getattr(options,'base_path', None)
    site_name = options.site_name[0]
    
    if '.' in site_name:
        path_resolver = PathResolver()
        project_name,site_name = site_name.split('.')
        base_path = base_path or os.path.join(path_resolver.project_name_to_path(project_name),'sites')
    print('Creating site %s in %s...'%(site_name,base_path or 'current directory'))
    site_maker = SiteMaker(site_name, base_path=base_path)
    print('Site %s created'%site_name)
    site_maker.do()

if __name__ == '__main__':
    main()
