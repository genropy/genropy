#!/usr/bin/env python
# encoding: utf-8
from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage


class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(comment='External audit', sqlschema='audit',
                    name_short='Audit', name_long='!!External audit',
                    name_full='External audit', history_tags='auditHistory')

    def packageTags(self, root):
        root.authTag('auditHistory', description='Audit history')

    def historyAllowed(self, userTags):
        """Whether a user may read the audit history: the ``history_tags`` of the
        package, which an instance may set on its package node in instanceconfig."""
        return self.application.checkResourcePermission(self.attributes.get('history_tags'), userTags)

    def config_db(self, pkg):
        pkg.sqlCode(sql_file='audit.sql')

    def required_packages(self):
        return ['gnrcore:sys']


class Table(GnrDboTable):
    pass
