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

    def addProxyService(self, proxy_url,tenant_id=None,client_base_url=None,
                        batch_size=None, db_max_waiting=None):
        """Create and activate a mailproxy service programmatically.

        Args:
            proxy_url: URL of the mail proxy server
            tenant_id: Tenant identifier (defaults to site_name if empty)
            batch_size: Optional batch size for message processing
            db_max_waiting: Optional max waiting time for DB operations

        Returns:
            dict: Result with 'ok' status and details

        Raises:
            Exception: If mailproxy service already exists

        Note:
            Admin token must be configured in instanceconfig as:
            api_keys.private.genro_mail_proxy?token
        """
        service_tbl = self.db.table('sys.service')
        if service_tbl.checkDuplicate(service_name='mailproxy',service_type='mailproxy'):
            raise Exception('Mailproxy service already exists')

        service_tbl.addService(
            service_type='mailproxy',
            service_name='mailproxy',
            implementation='mailproxy',
            proxy_url=proxy_url,
            tenant_id=tenant_id,
            client_base_url=client_base_url,
            batch_size=batch_size,
            db_max_waiting=db_max_waiting
        )

        self.db.commit()

        try:
            service = self.db.application.site.getService('mailproxy')
            result = service.activateService()

            self.db.commit()

            return result
        except Exception as e:
            service_tbl.delete(service_tbl.record(
                service_type='mailproxy'
            ))
            self.db.commit()
            raise

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

