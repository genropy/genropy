# encoding: utf-8
"""Computers registered by GenroApp to log a user in with a key kept in secure hardware.

GenroApp creates the key pair, sends the public key at registration and signs, at
each login, a single use challenge together with the site origin and the user.
"""

import base64
import hashlib
import secrets
import time
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from gnr.core.gnrbag import Bag

DEVICE_TAG = '_DEVICE_'
BIOMETRIC_TAG = '_BIOMETRIC_'
SIGNED_HEADER = 'genroapp-device-v1'
ALGORITHM = 'ES256'
VERIFICATIONS = ('biometry', 'user_presence')
CHALLENGE_SECONDS = 120
LOGIN_MODES = ('password', 'signature')
DEFAULT_LOGIN_MODE = 'password'


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('user_device', pkey='id',
                        name_long='!![en]User device',
                        name_plural='!![en]User devices',
                        caption_field='device_name')
        self.sysFields(tbl)
        tbl.column('user_id', size='22', group='_', name_long='!![en]User').relation(
                   'adm.user.id', relation_name='devices', mode='foreignkey', onDelete='cascade')
        tbl.column('key_id', size=':64', unique=True, indexed=True, name_long='!![en]Key id')
        tbl.column('alg', size=':10', name_long='!![en]Algorithm')
        tbl.column('public_key', dtype='T', name_long='!![en]Public key')
        tbl.column('device_name', name_long='!![en]Device name')
        tbl.column('platform', size=':10', name_long='!![en]Platform')
        tbl.column('verification', size=':15', name_long='!![en]Verification',
                   values='biometry:[!![en]Biometry],user_presence:[!![en]User presence]')
        tbl.column('last_used_ts', dtype='DHZ', name_long='!![en]Last used')
        tbl.column('revoked', dtype='B', name_long='!![en]Revoked')

    def newChallenge(self):
        """A single use challenge: the string GenroApp signs and the time it expires."""
        return Bag(dict(challenge=b64url(secrets.token_bytes(32)),
                        expires=time.time() + CHALLENGE_SECONDS))

    def validChallenge(self, challenge):
        """The challenge string of a Bag made by ``newChallenge``, None when missing or expired."""
        if not challenge or challenge['expires'] < time.time():
            return None
        return challenge['challenge']

    def signedBytes(self, origin, user, challenge):
        return '\n'.join((SIGNED_HEADER, origin, user, challenge)).encode('utf-8')

    def keyId(self, public_key):
        return b64url(hashlib.sha256(base64.b64decode(public_key, validate=True)).digest())

    def verifySignature(self, public_key, signature, data):
        """True when ``signature`` (base64 DER) is the ECDSA P-256 SHA-256 signature of ``data``
        made with the key of ``public_key`` (base64 SubjectPublicKeyInfo DER)."""
        try:
            key = serialization.load_der_public_key(base64.b64decode(public_key, validate=True))
            if not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(key.curve, ec.SECP256R1):
                return False
            key.verify(base64.b64decode(signature, validate=True), data, ec.ECDSA(hashes.SHA256()))
        except (ValueError, TypeError, UnsupportedAlgorithm, InvalidSignature):
            return False
        return True

    def registerDevice(self, user_id=None, user=None, origin=None, challenge=None, key_id=None,
                       public_key=None, alg=None, device_name=None, platform=None,
                       verification=None, signature=None):
        """Store the key GenroApp created for ``user`` when it signed ``challenge`` with it.
        Returns the new record, None when the key or its signature are refused."""
        if alg != ALGORITHM or verification not in VERIFICATIONS:
            return None
        if not self.verifySignature(public_key, signature, self.signedBytes(origin, user, challenge)):
            return None
        if self.keyId(public_key) != key_id or self.checkDuplicate(key_id=key_id):
            return None
        record = self.newrecord(user_id=user_id, key_id=key_id, alg=alg, public_key=public_key,
                                device_name=device_name, platform=platform,
                                verification=verification,
                                last_used_ts=datetime.now(timezone.utc))
        self.insert(record)
        return record

    def verifyLogin(self, origin=None, user=None, challenge=None, key_id=None, signature=None):
        """The device row (id, verification) of the key ``key_id`` of ``user`` when it signed
        ``challenge``; None for an unknown or revoked key or a wrong signature."""
        rows = self.query(columns='$id,$public_key,$verification',
                          where='$key_id=:key_id AND @user_id.username=:user AND $revoked IS NOT TRUE',
                          key_id=key_id, user=user).fetch()
        if not rows:
            return None
        row = rows[0]
        if not self.verifySignature(row['public_key'], signature, self.signedBytes(origin, user, challenge)):
            return None
        with self.recordToUpdate(row['id']) as record:
            record['last_used_ts'] = datetime.now(timezone.utc)
        return Bag(dict(id=row['id'], verification=row['verification']))

    def connectionTags(self, verification):
        """The connection tags a login signed by a key with ``verification`` adds."""
        if verification == 'biometry':
            return [DEVICE_TAG, BIOMETRIC_TAG]
        return [DEVICE_TAG]

    def addConnectionTags(self, user_local_tags, verification):
        tags = [t for t in (user_local_tags or '').split(',') if t]
        for tag in self.connectionTags(verification):
            if tag not in tags:
                tags.append(tag)
        return ','.join(tags)

    def restoreConnectionTags(self, user_local_tags, connection_tags):
        """``user_local_tags`` with the device tags of ``connection_tags`` only: a hook or
        a client never adds or drops _DEVICE_ and _BIOMETRIC_."""
        device_tags = (DEVICE_TAG, BIOMETRIC_TAG)
        tags = [t for t in (user_local_tags or '').split(',') if t and t not in device_tags]
        tags += [t for t in (connection_tags or '').split(',') if t in device_tags]
        return ','.join(tags)

    def genroappPreference(self):
        return Bag(self.db.application.getPreference('general.genroapp', pkg='adm'))

    def loginMode(self):
        """``signature``: a valid device signature is the whole login; ``password``: it fixes
        the user and the password is still asked."""
        mode = self.genroappPreference()['login_mode'] or DEFAULT_LOGIN_MODE
        if mode not in LOGIN_MODES:
            raise ValueError(f'Unknown GenroApp login mode {mode}')
        return mode

    def deviceRequired(self, user_tags):
        """True when a user with ``user_tags`` must log in with a device signature."""
        preference = self.genroappPreference()
        required = preference['required'] or 'nobody'
        if required == 'nobody':
            return False
        check = self.db.application.checkResourcePermission
        fallback_tag = preference['fallback_tag']
        if fallback_tag and check(fallback_tag, user_tags):
            return False
        if required == 'all':
            return True
        if required == 'tags':
            return bool(preference['required_tags']) and check(preference['required_tags'], user_tags)
        raise ValueError(f'Unknown GenroApp requirement {required}')

    def userDevices(self, user_id):
        """The devices of ``user_id``, most recent first."""
        rows = self.query(columns='$id,$device_name,$platform,$verification,$__ins_ts,$last_used_ts,$revoked',
                          where='$user_id=:user_id', user_id=user_id, order_by='$__ins_ts DESC').fetch()
        result = Bag()
        for row in rows:
            result.setItem(row['id'], Bag(dict(row)))
        return result

    def revokeDevice(self, pkey, user_id):
        """Revoke the device ``pkey`` of ``user_id``: its key no longer logs in."""
        with self.recordToUpdate(pkey) as record:
            if record['user_id'] != user_id:
                raise self.exception('business_logic', msg='!![en]This device belongs to another user')
            record['revoked'] = True
