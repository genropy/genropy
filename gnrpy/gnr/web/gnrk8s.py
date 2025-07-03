#!/usr/bin/env python
# encoding: utf-8

"""
Generates a k8s deployment file
"""
import yaml
import sys
import os.path
from gnr.web import logger

class GnrK8SGenerator(object):
    def __init__(self, instance_name, image,
                 deployment_name=None, split=False,
                 env_file=False, container_port=8080,
                 replicas=1):
        
        self.instance_name = instance_name
        self.image = image
        if ":" not in self.image:
            self.image = f'{self.image}:latest'

        self.container_port = container_port
        self.deployment_name = deployment_name or instance_name
        self.split = split
        self.replicas = 1
        self.env_file = env_file
        self.env = []
        if self.env_file:
            if not os.path.isfile(self.env_file):
                logger.error("Env file %s does not exists - using empty env, YMMV", self.env_file)
            else:
                with open(self.env_file) as fp:
                    for line in fp.readlines():
                        if "=" in line:
                            line = line.strip()
                            k, v = line.split("=")
                            self.env.append(dict(name=k, value=v))
            
    def generate_conf(self, fp=sys.stdout):

        # have gunicorn listen on all interfaces
        self.env.append(dict(name='GNR_GUNICORN_BIND', value='0.0.0.0'))

        services = [
            'daemon',
            'application',
            'taskscheduler',
            'taskworker'
        ]
        services_default_parms = {
            # if in split, the daemon should listen on public interface
            # to expose its port
            'daemon': ['-H','0.0.0.0']
        }
        
        services_port = {
            'daemon': 40404,
            'taskscheduler': 14951,
            'application': self.container_port
        }
            
        containers = []
        if self.split:
            for service in  services:
                args = [self.instance_name, f'--{service}']
                service_def = {
                    'name': f'{self.deployment_name}-{service}-container',
                    'image': self.image,
                    'command': ['gnr'],
                    'args': ['web','stack'] + args,
                    'env': self.env
                }

                if services_port.get(service, None):
                    service_def['ports'] = [
                        {'containerPort': services_port.get(service) }
                    ]

                if services_default_parms.get(service, None):
                    service_def['args'].extend(services_default_parms.get(service))
                    
                containers.append(service_def)
        else:

            args = ['web','stack',self.instance_name, '--all']
            service_def = {
                'name': f'{self.deployment_name}-fullstack-container',
                'image': self.image,
                'ports': [
                    {'containerPort': self.container_port}
                ],
                'command': ['gnr'],
                'args': args,
                'env': self.env
            }
            for service in services:
                if services_port.get(service, None):
                    if service_def.get("ports", None) is None:
                        service_def['ports'] = []
                    service_def['ports'].append(
                        {'containerPort': services_port.get(service) }
                    )

                if services_default_parms.get(service, None):
                    service_def['args'].append(f'--{service}')
                    service_def['args'].extend(services_default_parms.get(service))

            containers.append(service_def)
            
        deployment = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': f'{self.deployment_name}-deployment',
                'labels': {
                    'app': self.deployment_name
                }
            },
            'spec': {
                'replicas': self.replicas,
                'selector': {
                    'matchLabels': {
                        'app': self.deployment_name
                    }
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'app': self.deployment_name
                        }
                    },
                    'spec': {
                        'containers':containers
                    }
                }
            }
        }
        
        # Output YAML to stdout or write to file
        yaml.dump(deployment, fp, sort_keys=False)
