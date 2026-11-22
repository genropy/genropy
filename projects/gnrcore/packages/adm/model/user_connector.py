# encoding: utf-8
"""Personal GenroApp site connectors given to the users of this site.

One row for each connector the signing service signed. A user holds a place of the
site while one of its connectors is neither revoked nor expired; ``max_users`` of the
``<genroapp>`` tag limits the places. A renewal is a new row of the same user.
"""

from datetime import datetime, timezone

from gnr.core.gnrdecorator import public_method
from gnr.web import gnrgenroapp

REVOKE_TAGS = 'admin'


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('user_connector', pkey='id',
                        name_long='!![en]GenroApp connector',
                        name_plural='!![en]GenroApp connectors',
                        caption_field='connector_id')
        self.sysFields(tbl)
        tbl.column('user_id', size='22', group='_', name_long='!![en]User').relation(
                   'adm.user.id', relation_name='connectors', mode='foreignkey', onDelete='cascade')
        tbl.column('connector_id', size=':40', unique=True, indexed=True, name_long='!![en]Connector id')
        tbl.column('expires', dtype='DHZ', name_long='!![en]Expires')
        tbl.column('revoked', dtype='B', name_long='!![en]Revoked')

    def placeHolders(self):
        """The ids of the users that hold a place: a connector neither revoked nor expired."""
        rows = self.query(columns='$user_id', distinct=True,
                          where='$revoked IS NOT TRUE AND $expires>:now',
                          now=datetime.now(timezone.utc)).fetch()
        return {row['user_id'] for row in rows}

    def newConnector(self, config, user_id=None, user=None, url=None):
        """The signed connector ``{payload, signature}`` of ``user`` for the site at ``url``,
        asked to the signing service with the ``<genroapp>`` data of ``config`` and recorded
        here. A user with no place on a full site is refused before the signing service
        is called."""
        if config['max_users'] is not None:
            holders = self.placeHolders()
            if user_id not in holders and len(holders) >= config['max_users']:
                raise gnrgenroapp.ConnectorUsersExceeded(
                    f"This site already has {config['max_users']} GenroApp users")
        token = gnrgenroapp.signing_token(self.db.application, config)
        connector, connector_id, expires = gnrgenroapp.sign_connector(config, token, url, user)
        self.insert(self.newrecord(user_id=user_id, connector_id=connector_id, expires=expires))
        return connector

    def validConnector(self, connector_id=None, user=None):
        """True when ``connector_id`` is a connector of ``user`` that is not revoked."""
        return self.query(where='$connector_id=:connector_id AND @user_id.username=:user AND $revoked IS NOT TRUE',
                          connector_id=connector_id, user=user).count() > 0

    @public_method(tags=REVOKE_TAGS)
    def revokeConnector(self, pkey=None):
        """Revoke the connector ``pkey``: the device login refuses it and, with no other
        connector, its user frees a place. Only for an administrator."""
        application = self.db.application
        if not application.checkResourcePermission(REVOKE_TAGS, self.db.currentEnv.get('userTags')):
            raise self.exception('business_logic', msg='!![en]Only an administrator revokes a GenroApp connector')
        with self.recordToUpdate(pkey) as record:
            record['revoked'] = True
        self.db.commit()
