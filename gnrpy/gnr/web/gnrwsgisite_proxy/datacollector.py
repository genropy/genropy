#!/usr/bin/env python
# encoding: utf-8

import datetime
from collections import defaultdict

class FilterableCollection(list):
    def __init__(self, *args):
        super().__init__(*args)

    def _filter(self, o, k, v):
        return v.lower() in o.get(k, "").lower()
    
    def filter(self, k, v):
        return [x for x in self if self._filter(x, k, v)]
        
        
class DataCollector(object):
    def __init__(self, siteregister):
        self._r = siteregister

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

