#!/usr/bin/env python
# encoding: utf-8

"""
Generates a k8s deployment file

"""

from gnr.core.cli import GnrCliArgParse
from gnr.web.gnrk8s import GnrK8SGenerator

description = "Create a K8S deployment file for selected instance"
                    
def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('-i', '--image',
                        required=True,
                        dest="image",
                        help="Image name to be deployed")
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
                        default=8000,
                        dest="container_port",
                        help="Container port")
    parser.add_argument('-r', '--replicas',
                        dest="replicas",
                        type=int,
                        default=1,
                        help="Number of replicas")
    parser.add_argument('--secret',
                        dest="secret_name",
                        type=str,
                        help="The secret name for image retrieval")
    
    parser.add_argument('instance_name')
    
    options = parser.parse_args()

    generator = GnrK8SGenerator(options.instance_name, options.image,
                                deployment_name=options.name,
                                split=options.split,
                                env_file=options.env,
                                container_port=options.container_port,
                                secret_name=options.secret_name,
                                replicas=options.replicas)

    generator.generate_conf()
