#!/usr/bin/env python
# encoding: utf-8

"""
Create a Dockerfile for an instance, starting from a specific configuration file,
and build the finale image
"""
import yaml
import sys

from gnr.core.cli import GnrCliArgParse

description = "Create a K8S deployment file for selected instance"
                    
def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('-r', '--replicas',
                        dest="replicas",
                        type=int,
                        default=1,
                        help="Number of replicas")
    parser.add_argument('-n', '--name',
                        dest="name",
                        help="The application name (default to instance name)")
    parser.add_argument('-s', '--split',
                        action="store_true",
                        dest='split',
                        help="Deploy application stack on multiple containers")
    parser.add_argument('-e', '--env-file',
                        dest="env",
                        help="Env file to load")
    parser.add_argument('-p', '--container-port',
                        type=int,
                        default=8080,
                        dest="container_port",
                        help="Container port")
    parser.add_argument('-i', '--image',
                        required=True,
                        dest="image",
                        help="Image name to be deployed")
    
    parser.add_argument('instance_name')
    
    options = parser.parse_args()
    env = []
    if options.env:
        # load the env file
        with open(options.env) as fp:
            for line in fp.readlines():
                if "=" in line:
                    line = line.strip()
                    k, v = line.split("=")
                    env.append(dict(name=k, value=v))
                    
    if not options.name:
        options.name = options.instance_name

    if "/" not in options.image:
        options.image = f"softwellsrl/{options.image}"
        
    if ":" not in options.image:
        options.image = f'{options.image}:latest'

    if options.split:
        containers = []
        services = [
            'daemon',
            'application',
            'taskscheduler',
            'taskworker'
        ]

        for service in  services:
            args = [f'--no-{x}' for x in services if x != service]
            service_def = {
                'name': f'{options.name}-{service}-container',
                'image': options.image,
                'command': ['gnr'],
                'args': ['web','stack'] + args,
                'ports': [
                    {'containerPort': options.container_port} if service == 'application' else None
                ],
                'env': env
            }
            containers.append(service_def)
    else:
        containers =  [
            {
                'name': f'{options.name}-application-application',
                'image': options.image,
                'ports': [
                    {'containerPort': options.container_port}
                ],
                'command': ['gnr'],
                'args': ['web','stack',options.instance_name],
                'env': env
            }
        ]
        
    
    deployment = {
        'apiVersion': 'apps/v1',
        'kind': 'Deployment',
        'metadata': {
            'name': f'{options.name}-deployment',
            'labels': {
                'app': options.name
            }
        },
        'spec': {
            'replicas': options.replicas,
            'selector': {
                'matchLabels': {
                    'app': options.name
                }
            },
            'template': {
                'metadata': {
                    'labels': {
                        'app': options.name
                    }
                },
                'spec': {
                    'containers':containers
                }
            }
        }
    }
    
    # Output YAML to stdout or write to file
    yaml.dump(deployment, sys.stdout, sort_keys=False)
