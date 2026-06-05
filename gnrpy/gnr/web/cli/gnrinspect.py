#!/usr/bin/env python
import sys
from gnr.core.cli import GnrCliArgParse
from gnr.web.gnrwsgisite import GnrWsgiSite

description = "an interactive inspector for daemon data registers"

def main():

    try:
        from IPython import embed
    except:
        print("Python", sys.version)
        print("\nMissing IPython, please install it")
        print("pip install ipython")
        sys.exit(1)

    parser = GnrCliArgParse(description=description)
    parser.add_argument("instance_name")
    _options = parser.parse_args()

    try:
        site = GnrWsgiSite(_options.instance_name)
    except Exception as e:
        print(f"Can't connect: {e}")
        sys.exit(2)

    
    _c = site.datacollector

    ns = { x: getattr(_c, x) for x in dir(_c) if not x.startswith("_") }
    
    ns['siteregister'] = site.register.siteregister
    ns['site'] = site
    embed(user_ns = ns , colors="neutral", display_banner=False)

if __name__ == "__main__":
    main()
