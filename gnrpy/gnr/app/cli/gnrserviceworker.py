#!/usr/bin/env python
# encoding: utf-8

import os
import sys
from gnr.core.gnrlang import gnrImport
from gnr.app.gnrdeploy import PathResolver

description = "Run a service defined in a project"

def main():
    # FIXME: using sys.argv[1] can be shifted in a nested command structure
    # FIXME: the parameter must be validated
    instance_name,package_name,service_type,service_name = sys.argv[1].split('.')
    path_resolver = PathResolver()
    package_path = path_resolver.package_name_to_path(package_name)
    module_path = os.path.join(package_path,'lib','services', service_type,'service.py')
    module = gnrImport(module_path)
    service_class = getattr(module,'Service')
    service = service_class(instance_name=instance_name, package_name=package_name, 
                                service_name=service_name)
    service.run()
    
    #TO RUN SERVICE USE:
    #gnrserviceworker instance.package.servicetype.servicename
    #e.g. gnrserviceworker sandboxpg.genrobot.telegram.telegram

if __name__ == '__main__':
    main()
