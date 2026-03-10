#!/usr/bin/env python
# encoding: utf-8

"""
Generates a k8s deployment file

"""
import argparse
from gnr.core.cli import GnrCliArgParse
from gnr.web.gnrk8s import GnrK8SGenerator

description = "Create a K8S deployment file for selected instance"
                    
def main():

    def kv_pair(s):
        # split only on the first colon, so values may contain ':' if needed
        k, sep, v = s.partition(":")
        if not sep or not k:
            raise argparse.ArgumentTypeError("expected LABELNAME:VALUE")
        return k, v
    
    parser = GnrCliArgParse(description=description)
    parser.add_argument('-i', '--image',
                        required=True,
                        dest="image",
                        help="Image name to be deployed")
    parser.add_argument('-l', '--labels',
                        action="append",
                        type=kv_pair,
                        default=[],
                        metavar = "LABELNAME:VALUE",
                        help="May be repeated. Ex: -l customer:myself -l price:10")
    parser.add_argument('-f', '--fqdn',
                        action="append",
                        required=True,
                        dest="fqdns",
                        help="One (or more) FQDN of the deployed service")
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
    parser.add_argument('-k', '--env-secrets',
                        dest="env_secrets",
                        help="K8s Secret for environment",
                        default=[],
                        action='append')
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
    extra_labels = dict(options.labels) if options.labels else None
    generator = GnrK8SGenerator(options.instance_name, options.image,
                                options.fqdns,
                                deployment_name=options.name,
                                split=options.split,
                                env_file=options.env,
                                env_secrets=options.env_secrets,
                                container_port=options.container_port,
                                secret_name=options.secret_name,
                                replicas=options.replicas,
                                extra_labels=extra_labels)

    generator.generate_conf()
