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
                 fqdns,
                 deployment_name=None, split=False,
                 env_file=False, env_secrets=[],
                 container_port=8000,
                 secret_name=None,
                 replicas=1,
                 resource_profile=None,
                 extra_labels=None,
                 extra_initContainers: list | None = None):
        
        self.instance_name = instance_name
        self.image = image
        if ":" not in self.image:
            self.image = f'{self.image}:latest'
        self.secret_name = secret_name
        self.fqdns = fqdns
        self.resource_profile = resource_profile or {}
        self.container_port = container_port
        self.stack_name = deployment_name or instance_name
        self.application_name = f'{self.stack_name}-application'
        self.split = split
        self.replicas = replicas
        self.env_file = env_file
        self.env_secrets = env_secrets
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
                            
        self.extra_labels = extra_labels if isinstance(extra_labels, dict) else {}

        volume_init_containers = {
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
        
        self.extra_initContainers = [volume_init_containers]
        if extra_initContainers is not None:
            self.extra_initContainers.extend(extra_initContainers)
        
        # validate initContainers
        for eic in self.extra_initContainers:
            if not isinstance(eic, dict):
                raise TypeError(f"Extra init container {eic} must be a dict instance")
            for key in ['name','image','command']:
                if key not in eic:
                    raise ValueError(f"Missing required {key} in initContainer {eic}")
        # ensure name uniqueness
        initContainers_names = [x.get("name") for x in self.extra_initContainers]
        if len(initContainers_names) != len(set(initContainers_names)):
            raise ValueError("initContainers list has duplicates names!")

        
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
        self.env.append(dict(name="GNR_EXTERNALHOST", value=f'https://{self.fqdns[0]}'))

    def get_pv(self):
        pv = {
            "apiVersion": "v1",
            "kind": "PersistentVolume",
            "metadata": {
                "name": f"{self.stack_name}-site-pv"
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
        if self.extra_labels:
            pv['metadata']['labels'] = self.extra_labels
            
        return [pv]
    
    def get_pvc(self):
        pvc = {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": f"{self.stack_name}-site-pvc"

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
        if self.extra_labels:
            pvc['metadata']['labels'] = self.extra_labels
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

        class _NoAliasDumper(yaml.Dumper):
            def ignore_aliases(self, data):  # noqa: ARG002
                return True

        yaml.dump_all(resources, fp, Dumper=_NoAliasDumper, sort_keys=False)

    def get_splitted_conf(self):
        """One deployment per service. daemon and taskscheduler are always replicas=1;
        application and taskworker scale with self.replicas."""
        deployments = []
        services = []
        services_default_parms = {
            # daemon must listen on all interfaces to be reachable by other pods
            'daemon': ['-H', '0.0.0.0', '-P', str(self.GNR_DAEMON_PORT)]
        }
        self.env.append(dict(name='GNR_DAEMON_HOST', value=f'{self.stack_name}-daemon'))

        # Built once, reused as a value (not a reference) per non-daemon deployment
        wait_for_daemon = {
            "name": "wait-for-daemon",
            "image": "busybox",
            "command": [
                "sh", "-c",
                f"until nc -z {self.stack_name}-daemon {self.GNR_DAEMON_PORT}; "
                f"do echo \"Waiting for {self.stack_name}-daemon...\"; sleep 2; done"
            ]
        }

        site_volume = {
            'name': f'{self.stack_name}-site-volume',
            'persistentVolumeClaim': {'claimName': f'{self.stack_name}-site-pvc'}
        }

        for service in self.services:
            name = f'{self.stack_name}-{service}'
            container = {
                'name': f'{name}-container',
                'image': self.image,
                'imagePullPolicy': 'Always',
                'command': ['gnr'],
                'args': ['web', 'stack', self.instance_name, f'--{service}'],
                'env': self.env,
            }
            if self.resource_profile:
                container['resources'] = self.resource_profile
                
            if self.env_secrets:
                container['envFrom'] = [{'secretRef': {'name': s}} for s in self.env_secrets]

            if self.services_port.get(service):
                container['ports'] = [{'containerPort': self.services_port[service]}]

            if services_default_parms.get(service):
                container['args'].extend(services_default_parms[service])

            pod_spec = {'containers': [container]}

            if service == 'daemon':
                container['readinessProbe'] = {
                    'tcpSocket': {'port': self.GNR_DAEMON_PORT},
                    'initialDelaySeconds': 5,
                    'periodSeconds': 5,
                }
            else:
                # Fresh list per deployment — avoids shared-list mutation across iterations
                pod_spec['initContainers'] = list(self.extra_initContainers) + [wait_for_daemon]
                pod_spec['volumes'] = [site_volume]

            if self.secret_name:
                pod_spec['imagePullSecrets'] = [{'name': self.secret_name}]

            deployment = {
                'apiVersion': 'apps/v1',
                'kind': 'Deployment',
                'metadata': {
                    'name': f'{name}-deployment',
                    'labels': {'app': name, **self.extra_labels},
                },
                'spec': {
                    'replicas': self.replicas if service in ('application', 'taskworker') else 1,
                    'selector': {'matchLabels': {'app': name}},
                    'template': {
                        'metadata': {'labels': {'app': name, **self.extra_labels}},
                        'spec': pod_spec,
                    },
                },
            }
            deployments.append(deployment)

            if service != 'taskworker':
                service_port = self.services_port.get(service)
                service_obj = {
                    'apiVersion': 'v1',
                    'kind': 'Service',
                    'metadata': {
                        'name': name,
                        'labels': {'app': name, **self.extra_labels},
                    },
                    'spec': {
                        'ports': [{'name': 'http', 'protocol': 'TCP',
                                   'port': service_port, 'targetPort': service_port}],
                        'selector': {'app': name},
                    },
                }
                services.append(service_obj)

        return deployments, services, self.get_ingress()
    
    def get_monolithic_conf(self):
        deployments = []
        containers = []
        services_default_parms = {
            # if in split, the daemon should listen on public interface
            # to expose its port
            'daemon': ['-H','127.0.0.1', '-P', str(self.GNR_DAEMON_PORT)]
        }
        self.env.append(dict(name='GNR_DAEMON_HOST', value=f'127.0.0.1'))
        
        args = ['web','stack',self.instance_name, '--all']
        service_def = {
            'name': f'{self.stack_name}-fullstack-container',
            'imagePullPolicy': "Always",
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
        if self.resource_profile:
            service_def['resources'] = self.resource_profile
            
        if self.env_secrets:
            service_def['envFrom'] = []
            for env_s in self.env_secrets:
                service_def['envFrom'].append({'secretRef': {'name': env_s}})
            
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
                        'initContainers': [],
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
        
        if self.extra_initContainers:
            deployment['spec']['template']['spec']['initContainers'].extend(self.extra_initContainers)
            
        deployment['metadata']['labels'].update(self.extra_labels)
        deployment['spec']['template']['metadata']['labels'].update(self.extra_labels)
        
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
                        "name": "http",
                        "protocol": "TCP",
                        "port": self.container_port,
                        "targetPort": self.container_port,
                    }
                ],
                "selector": {
                    "app": self.stack_name
                }
            }
        }
        service['metadata']['labels'].update(self.extra_labels)
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
                        "host": fqdn,
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
                    for fqdn in self.fqdns
                ],
                "tls": [
                    {
                        "hosts": self.fqdns
                    },
                ],
            }
        }
        if self.extra_labels:
            ingress['metadata']['labels'] = self.extra_labels
            
        return [ingress]
    

