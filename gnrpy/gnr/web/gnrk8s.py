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
                 fqdn,
                 deployment_name=None, split=False,
                 env_file=False, container_port=8000,
                 secret_name=None,
                 replicas=1):
        
        self.instance_name = instance_name
        self.image = image
        if ":" not in self.image:
            self.image = f'{self.image}:latest'
        self.secret_name = secret_name
        self.fqdn = fqdn
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
        self.env.append(dict(name="GNR_EXTERNALHOST", value=f'http://{self.fqdn}'))
        
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
        service =   {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": self.deployment_name,
                "labels": {
                    "app": self.deployment_name
                }
            },
            "spec": {
                "ports": [
                    {
                        "port": self.container_port,
                        "targetPort": self.container_port,
                    }
                ],
                "selector": {
                    "app": self.deployment_name
                }
            }
        }
        
        ingress = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": self.deployment_name,
                "annotations": {
                    "traefik.ingress.kubernetes.io/router.entrypoints": "web"
                }
            },
            "spec": {
                "rules": [
                    {
                        "host": self.fqdn,
                        "http": {
                            "paths": [
                                {
                                    "path": "/",
                                    "pathType": "Prefix",
                                    "backend": {
                                        "service": {
                                            "name": self.deployment_name,
                                            "port": {
                                                "number": self.container_port
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
        resources = [deployment, service, ingress]
        if self.secret_name:
            deployment['spec']['template']['spec']['imagePullSecrets'] = [{ 'name': self.secret_name }]
            
        # Output YAML to stdout or write to file
        yaml.dump_all(resources, fp, sort_keys=False)
