#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  webtools to export prometheus metrics
#
#  Copyright (c) 2024 Softwell. All rights reserved.
#

import json
import time
from gnr.web.gnrbaseclasses import BaseWebtool
from gnr.web.cli.gnrinspect import DataCollector
from gnr.core.gnrdecorator import metadata

METRIC_PREFIX = "genropy_site_counters"

class Prometheus(BaseWebtool):
    content_type = "text/plain"

    def get_metrics(self, ts):
        collector = DataCollector(self.site.register.siteregister)
        counters = ['users', 'pages', 'connections']
        payload = []
        for counter in counters:
            val = len(getattr(collector, counter))
            payload.append(f'{METRIC_PREFIX}{{counter="{counter}"}} {val}')
            
        stale = list(collector.stale_connections(seconds=60*5))
        payload.append(f'{METRIC_PREFIX}{{counter="stale_connections_5min"}} {len(stale)}')
        return "\n".join(payload)
    
    @metadata(alias_url="/metrics")
    def __call__(self, *args, **kwargs):
        ts = int(time.time()/60)
        return self.get_metrics(ts)

