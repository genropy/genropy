# encoding: utf-8

import hashlib
import secrets
from datetime import datetime, timezone


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
        tbl.column('activated_ts', dtype='DHZ', name_long='!!Activated')
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
        tbl.formulaColumn('status',
            """CASE
                 WHEN $token IS NULL THEN 'to_activate'
                 WHEN $is_active IS NOT TRUE THEN 'inactive'
                 WHEN $expires_ts IS NOT NULL AND $expires_ts < CURRENT_TIMESTAMP THEN 'expired'
                 ELSE 'active'
               END""",
            dtype='A', name_long='!!Status')

    def generate_token(self):
        """Generate a new secure token and return the full value."""
        return secrets.token_urlsafe(48)

    def _hash_token(self, token_value):
        # Deterministic SHA-256 (no salt): tokens from secrets.token_urlsafe(48)
        # already carry 384 bits of entropy, so rainbow tables are not a threat
        # and we need O(1) lookup on every authenticated request.
        return hashlib.sha256(token_value.encode('utf-8')).hexdigest()

    def activate_api_token(self, record_id=None):
        """Generate and persist a token on an existing record.

        Only the SHA-256 hash is stored; the full token is returned to
        the caller ONCE and never stored. Idempotent: if the record
        already has a token, returns None and leaves the record alone.

        Internal helper — the caller (a @public_method on the Form) is
        responsible for the surrounding commit.
        """
        token_value = self.generate_token()
        activated = False
        with self.recordToUpdate(pkey=record_id) as rec:
            if rec.get('token'):
                return None
            rec['token'] = self._hash_token(token_value)
            rec['token_hint'] = f'...{token_value[-4:]}'
            rec['is_active'] = True
            rec['activated_ts'] = datetime.now(timezone.utc)
            activated = True
        return token_value if activated else None

    def revoke_api_token(self, record_id=None):
        """Soft-revoke a token by clearing its is_active flag.

        The hash stays in the row so audits can still match historical
        usage; re-enabling is a one-flag flip via `reactivate_api_token`.

        Internal helper — the caller commits.
        """
        with self.recordToUpdate(pkey=record_id) as rec:
            if not rec.get('is_active'):
                return False
            rec['is_active'] = False
        return True

    def reactivate_api_token(self, record_id=None):
        """Flip is_active back to True on a previously-revoked token.

        Internal helper — the caller commits.
        """
        with self.recordToUpdate(pkey=record_id) as rec:
            if rec.get('is_active'):
                return False
            rec['is_active'] = True
        return True

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
