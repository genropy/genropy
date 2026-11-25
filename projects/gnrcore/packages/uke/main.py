#!/usr/bin/env python
# encoding: utf-8
from gnr.app import pkglog as logger
from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage


class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(comment='Unified Knowledge Environment (deprecated)', sqlschema='uke',
                    name_short='uke', name_long='UKE', name_full='Unified Knowledge Environment')

    def onApplicationInited(self):
        logger.warning("gnrcore:uke is deprecated and will be removed on 2026-12-31. "
                       "Remove it from the instance packages; its 'uke' SQL schema "
                       "must then be dropped manually.")


class Table(GnrDboTable):
    pass
