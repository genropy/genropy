#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  webtools providing an health and readyness endpoints,
#  using naming convention for endpoints, when application
#  are executed in a containerd-based environment.
#
#  Copyright (c) 2026 Softwell. All rights reserved.
#

from gnr.web.gnrbaseclasses import BaseWebtool
from gnr.core.gnrdecorator import metadata


class Health(BaseWebtool):
    content_type = "application/json"

    @metadata(alias_url="/healthz")
    def __call__(self, *args, **kwargs):
        return '{"status": "ok"}'

class Ready(BaseWebtool):
    content_type = "application/json"

    @metadata(alias_url="/readyz")
    def __call__(self, *args, **kwargs):
        return '{"status": "ready"}'
