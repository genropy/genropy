#!/usr/bin/env python
# encoding: utf-8

from gnr.core.cli import GnrCliArgParse
from gnr.core.gnrconfig import setRmsOptions
from gnr.lib.services.rms import RMS

def register_instance(instance,**kwargs):
    rms = RMS()
    rms.registerInstance(instance,**kwargs)

def register_pod(pod=None, service_url=None,customer_code=None,rebuild=None):
    setRmsOptions(code=pod,customer_code=customer_code, url=service_url,rebuild=rebuild)
    rms = RMS()
    rms.registerPod()

description = ""

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('--pod','-p',
                        dest='pod',
                        help="Pod")
    parser.add_argument('--rebuild','-r',
                        dest='rebuild',
                        action='store_true',
                        help="Rebuild conf")
    parser.add_argument('--service_url',
                        dest='service_url',
                        help="Service url")
    parser.add_argument('--domain','-d',
                        dest='domain',
                        help="Domain")
    parser.add_argument('--customer_code','-c',
                        dest='customer_code',
                        help="Customer Code")
    parser.add_argument("instance", nargs='?',
                        help="Instance name")

    options = parser.parse_args()
    instance = options.instance
    
    if instance:
        register_instance(instance,domain=options.domain, customer_code=options.customer_code)
    else:
        pod = options.pod
        service_url = options.service_url or "https://deploy.softwell.it/deploy/rms_endpoint"
        if pod:
            register_pod(pod=pod, service_url=service_url, customer_code=options.customer_code, rebuild=options.rebuild)
        else:
            print('Missing pod code')

if __name__ == '__main__':
    main()
