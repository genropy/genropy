#!/usr/bin/env python
# encoding: utf-8
"""
create a new genroproject

"""
import sys, os, shutil
import argparse

from gnr.core.gnrbag import Bag
from gnr.app.gnrapp import GnrApp
from gnr.app.gnrdeploy import InstanceMaker, PathResolver

usage = "gnrmkinstance instancename"

def main():
    parser = argparse.ArgumentParser(usage)
    parser.add_argument("-b", "--base-path", dest="base_path",
                      help="base path where project will be created")

    parser.add_argument("args", nargs="+")
    options = parser.parse_args()
    args = options.args
    
    base_path = getattr(options, 'base_path', None)
    if not args:
        print('You should specify an instance name')
    else:
        instance_name = args[0]
        if '.' in args[0]:
            path_resolver = PathResolver()
            project_name, instance_name = args[0].split('.')
            base_path = base_path or os.path.join(path_resolver.project_name_to_path(project_name), 'instances')
        print('Creating instance %s in %s...' % (instance_name, base_path or 'current directory'))
        instance_maker = InstanceMaker(instance_name, base_path=base_path, packages=args[1:])
        print('Instance %s created' % instance_name)
        instance_maker.do()

        
if __name__ == '__main__':
    main()
