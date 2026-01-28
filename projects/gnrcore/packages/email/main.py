#!/usr/bin/env python
# encoding: utf-8
from gnr.core.gnrstring import boolean
from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage

class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(comment='email package',sqlschema='email',
                name_short='Email', name_long='Email', name_full='Email')

    def config_db(self, pkg):
        pass

    def required_packages(self):
        return ['gnrcore:adm']

    def loginUrl(self):
        return 'email/login'

    def services(self):
        return [dict(service_name='mail',resource='emailservice')]

    def packageTags(self, branch):
        branch.authTag(label='_MAILPROXY_', description='Mail proxy service access')


    def getMailProxy(self, raise_if_missing=True):
        """Get the configured and activated mailproxy service.

        Args:
            raise_if_missing: If True, raises exception when service not available.
                             If False, returns None.

        Returns:
            The mailproxy service instance or None.
        """
        service = self.db.application.site.getService('mailproxy')
        if not service:
            return
        if service and service.disabled:
            return None

        if not service or not service.proxy_url:
            if raise_if_missing:
                raise Exception('Mailproxy service is not configured')
            return None

        if not service.tenant_registered:
            if raise_if_missing:
                raise Exception('Mailproxy service is not activated')
            return None

        return service

class Table(GnrDboTable):
    def use_dbstores(self,forced_dbstore=None, env_forced_dbstore=None,**kwargs):
        result = forced_dbstore or \
                env_forced_dbstore or \
                boolean(self.pkg.attributes.get('use_dbstores','f'))
        return result

