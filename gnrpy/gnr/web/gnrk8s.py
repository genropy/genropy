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
                 env_file=False, env_secret=None,
                 container_port=8000,
                 secret_name=None,
                 replicas=1):
        
        self.instance_name = instance_name
        self.image = image
        if ":" not in self.image:
            self.image = f'{self.image}:latest'
        self.secret_name = secret_name
        self.fqdn = fqdn
        self.container_port = container_port
        self.stack_name = deployment_name or instance_name
        self.application_name = f'{self.stack_name}-application'
        self.split = split
        self.replicas = replicas
        self.env_file = env_file
        self.env_secret = env_secret
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

        self.GNR_DAEMON_PORT = 40407
        self.services = [
            'daemon',
            'application',
            'taskscheduler',
            'taskworker'
        ]
        self.services_port = {
            'daemon': self.GNR_DAEMON_PORT,
            'taskscheduler': 14951,
            'application': self.container_port
        }

        self.env.append(dict(name='GNR_DAEMON_PORT', value=str(self.GNR_DAEMON_PORT)))
        # have gunicorn listen on all interfaces
        self.env.append(dict(name='GNR_GUNICORN_BIND', value='0.0.0.0'))
        self.env.append(dict(name="GNR_EXTERNALHOST", value=f'https://{self.fqdn}'))

    def get_pv(self):
        pv = {
            "apiVersion": "v1",
            "kind": "PersistentVolume",
            "metadata": {
                "name": f"{self.stack_name}-site-pv",
            },
            "spec": {
                "capacity": {
                    "storage": "1Gi",
                },
                "accessModes": ['ReadWriteMany'],
                "storageClassName": "standard",
                "hostPath": {
                    "path": f"/mnt/data/{self.stack_name}-site"
                }
            }
        }
        return [pv]
    
    def get_pvc(self):
        pvc = {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": f"{self.stack_name}-site-pvc",
                },
            "spec": {
                "accessModes": [
                    "ReadWriteMany"
                    ],
                "resources": {
                    "requests": {
                        "storage": "1Gi"
                    }
                },
                "storageClassName": "standard"
            }
        }
        return [pvc]
    
    def generate_conf(self, fp=sys.stdout):
        if self.split:
            deployments, services, ingress = self.get_splitted_conf()
        else:
            deployments, services, ingress = self.get_monolithic_conf()
        resources = []
        resources.extend(self.get_pv())
        resources.extend(self.get_pvc())
        resources.extend(deployments)
        resources.extend(services)
        resources.extend(ingress)
        
        # Output YAML to stdout or write to file
        yaml.dump_all(resources, fp, sort_keys=False)

    def get_splitted_conf(self):
        deployments = []
        services = []
        services_default_parms = {
            # if in split, the daemon should listen on public interface
            # to expose its port
            'daemon': ['-H','0.0.0.0', '-P', str(self.GNR_DAEMON_PORT)]
        }
        self.env.append(dict(name='GNR_DAEMON_HOST', value=f'{self.stack_name}-daemon'))
        
        for service in self.services:
            name = f'{self.stack_name}-{service}'
            args = [self.instance_name, f'--{service}']
            container = {
                'name': f'{name}-container',
                'image': self.image,
                'imagePullPolicy': "Always",
                'command': ['gnr'],
                'args': ['web','stack'] + args,
                'env': self.env
            }
            if self.env_secret:
                container['envFrom'] = [{'secretRef': {'name': self.env_secret}}]

            if self.services_port.get(service, None):
                container['ports'] = [
                    {'containerPort': self.services_port.get(service) }
                ]
                
            if services_default_parms.get(service, None):
                container['args'].extend(services_default_parms.get(service))
                    

            deployment = {
                'apiVersion': 'apps/v1',
                'kind': 'Deployment',
                'metadata': {
                    'name': f'{name}-deployment',
                    'labels': {
                        'app': f'{name}'
                    }
                },
                'spec': {
                    'replicas': self.replicas if service in ['application','taskworker'] else 1,
                    'selector': {
                        'matchLabels': {
                            'app': name
                        }
                    },
                    'template': {
                        'metadata': {
                            'labels': {
                                'app': name
                            }
                        },
                        'spec': {
                            'containers': [container]
                        }
                    }
                }
            }
            if service == "daemon":
                container['readinessProbe'] = {
                    "tcpSocket": {
                        "port": self.GNR_DAEMON_PORT
                    },
                    "initialDelaySeconds": 5,
                    "periodSeconds": 5
                }

            else:
                deployment['spec']['template']['spec']['initContainers'] = [
                    {
                        "name": "wait-for-daemon",
                        "image": "busybox",
                        "command": [
                            "sh", "-c",
                            f"until nc -z {self.stack_name}-daemon {self.GNR_DAEMON_PORT}; do echo \"Waiting for {self.stack_name}-daemon...\"; sleep 2; done"
                        ]
                    }
                ]
            if self.secret_name:
                deployment['spec']['template']['spec']['imagePullSecrets'] = [{"name": self.secret_name}]
            deployments.append(deployment)

            if service != 'taskworker':
                service =   {
                    "apiVersion": "v1",
                    "kind": "Service",
                    "metadata": {
                        "name": name,
                        "labels": {
                            "app": name
                        }
                    },
                    "spec": {
                        "ports": [
                            {
                                "port": self.services_port.get(service),
                                "targetPort": self.services_port.get(service),
                            }
                        ],
                        "selector": {
                            "app": name
                        }
                    }
                }
                services.append(service)
                
        return deployments, services, self.get_ingress()
    
    def get_monolithic_conf(self):
        deployments = []
        containers = []
        services_default_parms = {
            # if in split, the daemon should listen on public interface
            # to expose its port
            'daemon': ['-H','127.0.0.1', '-P', str(self.GNR_DAEMON_PORT)]
        }
        
        args = ['web','stack',self.instance_name, '--all']
        service_def = {
            'name': f'{self.stack_name}-fullstack-container',
            'image': self.image,
            'command': ['gnr'],
            'args': args,
            'env': self.env,
            'securityContext': {
                "runAsUser": 100,
                "runAsGroup": 100
            },
            'volumeMounts': [
                {
                    "name": f'{self.stack_name}-site-volume',
                    "mountPath": "/home/genro/site"
                }
            ]
                
        }

        if self.env_secret:
            service_def['envFrom'] = [{'secretRef': {'name': self.env_secret}}]
            
        for service in self.services:
            if self.services_port.get(service, None):
                if service_def.get("ports", None) is None:
                    service_def['ports'] = []
                service_def['ports'].append(
                    {'containerPort': self.services_port.get(service) }
                )
                
            if services_default_parms.get(service, None):
                service_def['args'].append(f'--{service}')
                service_def['args'].extend(services_default_parms.get(service))
                
        containers.append(service_def)
                            
        deployment = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': f'{self.stack_name}-deployment',
                'labels': {
                    'app': self.stack_name
                }
            },
            'spec': {
                'replicas': 1,
                'selector': {
                    'matchLabels': {
                        'app': self.stack_name
                    }
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'app': self.stack_name
                        }
                    },
                    'spec': {
                        'securityContext': {
                            'fsGroup': 100
                        },
                        'initContainers': [
                            {
                                "name": "volume-permissions",
                                "image": "busybox",
                                "command": ["sh", "-c", f"chown -R 100:100 /mnt/data/{self.stack_name}-site"],
                                "volumeMounts": [
                                    {
                                        "name": f"{self.stack_name}-site-volume",
                                        "mountPath": f"/mnt/data/{self.stack_name}-site",
                                        
                                    }
                                ]
                            }
                        ],
                        'containers':containers,
                        'volumes': [
                            {
                                'name': f'{self.stack_name}-site-volume',
                                'persistentVolumeClaim': {
                                    'claimName': f'{self.stack_name}-site-pvc'
                                    }
                            }
                        ]
                        
                    }
                }
            }
        }
        if self.secret_name:
            deployment['spec']['template']['spec']['imagePullSecrets'] = [{"name": self.secret_name}]

        service =   {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": self.application_name,
                "labels": {
                    "app": self.application_name,
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
                    "app": self.stack_name
                }
            }
        }
        
        return [deployment], [service], self.get_ingress()
    
    def get_ingress(self):
        ingress = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": f'{self.stack_name}-ingress',
                "annotations": {
                    "traefik.ingress.kubernetes.io/router.entrypoints": "websecure",
                    "traefik.ingress.kubernetes.io/router.tls": "true",
                    "traefik.ingress.kubernetes.io/router.tls.certresolver": "letsencrypt",
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
                                            "name": self.application_name,
                                            "port": {
                                                "number": self.container_port
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ],
                "tls": [
                    {
                        "hosts": [
                            self.fqdn
                        ]
                    },
                ],
            }
        }
        
        return [ingress]
    

