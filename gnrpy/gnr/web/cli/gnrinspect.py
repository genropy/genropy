#!/usr/bin/env python
import sys
import datetime
from gnr.core.cli import GnrCliArgParse
from gnr.web.gnrwsgisite import GnrWsgiSite
from collections import defaultdict

try:
    from IPython import embed
except:
    print("Python", sys.version)
    print("\nMissing IPython, please install it")
    print("pip install ipython")
    sys.exit(1)

description = "an interactive inspector for daemon data registers"

class FilterableCollection(list):
    def __init__(self, *args):
        super().__init__(*args)

    def _filter(self, o, k, v):
        return v.lower() in o.get(k, "").lower()
    
    def filter(self, k, v):
        return [x for x in self if self._filter(x, k, v)]
        
        
class DataCollector(object):
    def __init__(self, register):
        self._r = register

    @property
    def users(self):
        """ List of active users """
        return FilterableCollection(self._r.users())

    @property
    def pages(self):
        """ List of active pages """
        return FilterableCollection(self._r.pages())

    @property
    def pages_by_user(self):
        r = defaultdict(list)
        for p in self.pages:
            r[p['user']].append(p)
        return dict(r)

    @property
    def connections(self):
        """ List of active connections """
        return FilterableCollection(self._r.connections())

    @property
    def connections_by_user(self):
        r = defaultdict(list)
        for p in self.connections:
            r[p['user']].append(p)
        return dict(r)

    def stale_connections(self, seconds=0):
        now = datetime.datetime.now()
        for c in self.connections:
            if (now - c['last_refresh_ts']).seconds > seconds:
                yield c
        
    @property
    def counters(self):
        """ Stats counters """
        return self._r.counters()

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument("instance_name")
    _options = parser.parse_args()

    try:
        site = GnrWsgiSite(_options.instance_name)
    except Exception as e:
        print(f"Can't connect: {e}")
        sys.exit(2)
        
    siteregister = site.register.siteregister
    locals()["siteregister"] = siteregister
    _collector = DataCollector(siteregister)

    # register elements
    for x in dir(_collector):
        if not x.startswith("_"):
            locals()[x] = getattr(_collector, x)

    embed(colors="neutral", display_banner=False)

if __name__ == "__main__":
    main()
