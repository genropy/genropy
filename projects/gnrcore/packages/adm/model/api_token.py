# encoding: utf-8

import hashlib
import secrets
from datetime import datetime, timezone
from gnr.core.gnrdecorator import public_method


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('api_token', pkey='id',
                        name_long='!!API Token',
                        name_plural='!!API Tokens',
                        rowcaption='$description')
        self.sysFields(tbl)
        tbl.column('token', size='64', unique=True, indexed=True,
                   name_long='!!Token')
        tbl.column('description', name_long='!!Description')
        tbl.column('group_code', size=':15', name_long='!!Group').relation(
                   'group.code', relation_name='api_tokens', mode='foreignkey')
        tbl.column('is_active', dtype='B', default=True, name_long='!!Active')
        tbl.column('expires_ts', dtype='DHZ', name_long='!!Expires')
        tbl.column('last_used_ts', dtype='DHZ', name_long='!!Last Used')
        tbl.column('created_by', size='22', group='_',
                   name_long='!!Created By').relation('adm.user.id',
                   relation_name='api_tokens', onDelete='setnull')
        tbl.column('notes', dtype='T', name_long='!!Notes')
        tbl.column('token_hint', size='8', name_long='!!Token Hint')
        tbl.formulaColumn('all_tags',
                          select=dict(table='adm.api_token_tag',
                                      columns='@tag_id.authorization_tag',
                                      where='$api_token_id=#THIS.id'),
                          dtype='A', name_long='!!Tags')

    def generate_token(self):
        """Generate a new secure token and return the full value."""
        return secrets.token_urlsafe(48)

    def _hash_token(self, token_value):
        # Deterministic SHA-256 (no salt): tokens from secrets.token_urlsafe(48)
        # already carry 384 bits of entropy, so rainbow tables are not a threat
        # and we need O(1) lookup on every authenticated request.
        return hashlib.sha256(token_value.encode('utf-8')).hexdigest()

    @public_method
    def create_api_token(self, description=None, expires_ts=None,
                         notes=None, created_by=None):
        """Create a new API token. Returns (record_id, full_token).

        Only the SHA-256 hash is persisted; the full token is returned
        ONLY at creation time and never stored.
        """
        token_value = self.generate_token()
        record = self.newrecord(
            token=self._hash_token(token_value),
            description=description or '',
            is_active=True,
            expires_ts=expires_ts,
            notes=notes or '',
            created_by=created_by,
            token_hint=f'...{token_value[-4:]}'
        )
        self.insert(record)
        return record['id'], token_value

    def validate_token(self, token_value):
        """Validate a Bearer token.

        Returns dict with auth_tags, description, token_id if valid.
        Returns None if invalid, expired, or inactive.
        """
        records = self.query(
            columns='$id,$description,$expires_ts,$is_active,$all_tags,$group_code',
            where='$token=:t AND $is_active=:a',
            t=self._hash_token(token_value), a=True
        ).fetch()
        if not records:
            return None
        record = records[0]
        expires_ts = record['expires_ts']
        if expires_ts and expires_ts < datetime.now(timezone.utc):
            return None
        # Piggy-back the last_used_ts update on the caller's commit instead of
        # forcing a synchronous commit on every Bearer-authenticated request.
        self.db.deferToCommit(self.raw_update,
                              record={'id': record['id'],
                                      'last_used_ts': datetime.now(timezone.utc)},
                              _deferredId=record['id'])
        return {
            'token_id': record['id'],
            'auth_tags': record.get('all_tags', ''),
            'group_code': record.get('group_code', ''),
            'description': record['description']
        }
