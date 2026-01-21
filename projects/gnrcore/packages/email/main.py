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

    def addProxyService(self, proxy_url, proxy_token, tenant_id=None,
                        batch_size=None, db_max_waiting=None):
        """Create and activate a mailproxy service programmatically.

        Args:
            proxy_url: URL of the mail proxy server
            proxy_token: API token for authentication
            tenant_id: Tenant identifier (defaults to site_name if empty)
            batch_size: Optional batch size for message processing
            db_max_waiting: Optional max waiting time for DB operations

        Returns:
            dict: Result with 'ok' status and details

        Raises:
            Exception: If mailproxy service already exists
        """
        if self.application.site.getService('mailproxy'):
            raise Exception('Mailproxy service already exists')

        service_tbl = self.application.db.table('sys.service')

        service_tbl.addService(
            service_type='mailproxy',
            service_name='mailproxy',
            implementation='mailproxy',
            proxy_url=proxy_url,
            proxy_token=proxy_token,
            tenant_id=tenant_id,
            batch_size=batch_size,
            db_max_waiting=db_max_waiting
        )

        self.application.db.commit()

        try:
            service = self.application.site.getService('mailproxy')
            result = service.activateService()

            self.application.db.commit()

            return result
        except Exception as e:
            service_tbl.delete(service_tbl.record(
                service_type='mailproxy'
            ))
            self.application.db.commit()
            raise

class Table(GnrDboTable):
    def use_dbstores(self,forced_dbstore=None, env_forced_dbstore=None,**kwargs):
        result = forced_dbstore or \
                env_forced_dbstore or \
                boolean(self.pkg.attributes.get('use_dbstores','f'))
        return result

