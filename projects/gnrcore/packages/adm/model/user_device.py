# encoding: utf-8
"""Computers registered by GenroApp to log a user in with a key kept in secure hardware.

GenroApp creates the key pair, sends the public key at registration and signs, at
each login, a single use challenge together with the site origin and the user.

The same key confirms an action of the logged user: a page calls
``genro.genroapp.confirm(text)``, GenroApp shows ``text`` in the identity check of the
computer and signs it, and the server method that acts calls ``popConfirmed(text)`` first.
"""

import base64
import hashlib
import secrets
import time
import unicodedata
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method

# a login signed by a registered key proves the possession of that key: _DEVICE_
DEVICE_TAG = '_DEVICE_'
# never granted: ``verification`` is declared by the client and the server has no evidence
# of the biometric reading; it is only kept out of what a client or a hook may add
BIOMETRIC_TAG = '_BIOMETRIC_'
SERVER_TAGS = (DEVICE_TAG, BIOMETRIC_TAG)
SIGNED_HEADER = 'genroapp-device-v1'
# another first line: a confirmation never logs in and a login never confirms
CONFIRM_HEADER = 'genroapp-confirm-v1'
CONFIRM_TEXT_MAX = 120
CONFIRM_CHALLENGE = 'genroapp_confirm_challenge'
CONFIRMED = 'genroapp_confirmed'
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
        tbl.column('verification', size=':15', name_long='!![en]Declared verification',
                   values='biometry:[!![en]Biometry],user_presence:[!![en]User presence]')
        tbl.column('last_used_ts', dtype='DHZ', name_long='!![en]Last used')
        tbl.column('revoked', dtype='B', name_long='!![en]Revoked')
        tbl.column('connector_id', size=':40', indexed=True, name_long='!![en]Connector id')

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

    def confirmText(self, text):
        """``text`` when GenroApp signs it as the text of a confirmation: one line of at most
        CONFIRM_TEXT_MAX characters, without spaces at its ends. None otherwise."""
        if not text or text != text.strip() or len(text) > CONFIRM_TEXT_MAX:
            return None
        if any(unicodedata.category(c) == 'Cc' for c in text):
            return None
        return text

    def confirmBytes(self, origin, user, challenge, text):
        digest = b64url(hashlib.sha256(text.encode('utf-8')).digest())
        return '\n'.join((CONFIRM_HEADER, origin, user, challenge, digest)).encode('utf-8')

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
                       verification=None, signature=None, connector_id=None):
        """Store the key GenroApp created for ``user`` when it signed ``challenge`` with it.
        Returns the new record, None when the key, its signature or ``connector_id`` are refused."""
        if alg != ALGORITHM or verification not in VERIFICATIONS:
            return None
        if not self.connectorAccepted(connector_id, user):
            return None
        if not self.verifySignature(public_key, signature, self.signedBytes(origin, user, challenge)):
            return None
        if self.keyId(public_key) != key_id or self.checkDuplicate(key_id=key_id):
            return None
        record = self.newrecord(user_id=user_id, key_id=key_id, alg=alg, public_key=public_key,
                                device_name=device_name, platform=platform,
                                verification=verification, connector_id=connector_id,
                                last_used_ts=datetime.now(timezone.utc))
        self.insert(record)
        return record

    def connectorAccepted(self, connector_id, user):
        """False when ``connector_id`` is not a connector of ``user``, is revoked or is
        expired. No ``connector_id`` is accepted: the GenroApp releases that send none."""
        if not connector_id:
            return True
        return self.db.table('adm.user_connector').validConnector(connector_id=connector_id, user=user)

    def verifyLogin(self, origin=None, user=None, challenge=None, key_id=None, signature=None,
                    connector_id=None):
        """The device row (id) of the key ``key_id`` of ``user`` when it signed ``challenge``;
        None for an unknown or revoked key, a wrong signature or a refused connector."""
        return self.verifySigned(self.signedBytes(origin, user, challenge), user=user, key_id=key_id,
                                 signature=signature, connector_id=connector_id)

    def verifyConfirm(self, origin=None, user=None, challenge=None, text=None, key_id=None,
                      signature=None, connector_id=None):
        """As ``verifyLogin``, for the confirmation of ``text``."""
        return self.verifySigned(self.confirmBytes(origin, user, challenge, text), user=user, key_id=key_id,
                                 signature=signature, connector_id=connector_id)

    def verifySigned(self, data, user=None, key_id=None, signature=None, connector_id=None):
        """The device row (id) of the key ``key_id`` of ``user`` when it signed ``data``;
        None for an unknown or revoked key, a wrong signature or a refused connector.
        The connector is ``connector_id``, which is then stored on the device, or without
        it the one already stored: a revoked connector stays refused when GenroApp
        sends none."""
        rows = self.query(columns='$id,$public_key,$connector_id',
                          where='$key_id=:key_id AND @user_id.username=:user AND $revoked IS NOT TRUE',
                          key_id=key_id, user=user).fetch()
        if not rows:
            return None
        row = rows[0]
        if not self.verifySignature(row['public_key'], signature, data):
            return None
        if not self.connectorAccepted(connector_id or row['connector_id'], user):
            return None
        with self.recordToUpdate(row['id']) as record:
            record['last_used_ts'] = datetime.now(timezone.utc)
            if connector_id:
                record['connector_id'] = connector_id
        return Bag(dict(id=row['id']))

    def connectionTags(self, user_local_tags, device=False):
        """``user_local_tags`` of a login without the server tags a hook may have added:
        _DEVICE_ only for a login signed by a registered key (``device``), whatever
        verification the key declared."""
        tags = [t for t in (user_local_tags or '').split(',') if t and t not in SERVER_TAGS]
        if device:
            tags.append(DEVICE_TAG)
        return ','.join(tags)

    def restoreConnectionTags(self, user_local_tags, connection_tags):
        """``user_local_tags`` with the device tag of ``connection_tags`` only: a hook or
        a client never adds or drops _DEVICE_, and never adds _BIOMETRIC_."""
        tags = [t for t in (user_local_tags or '').split(',') if t and t not in SERVER_TAGS]
        if DEVICE_TAG in (connection_tags or '').split(','):
            tags.append(DEVICE_TAG)
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

    @public_method
    def userDevices(self):
        """The devices of the logged user, most recent first."""
        rows = self.query(columns='$id,$device_name,$platform,$verification,$__ins_ts,$last_used_ts,$revoked',
                          where='$user_id=:env_user_id', order_by='$__ins_ts DESC').fetch()
        result = Bag()
        for row in rows:
            result.setItem(row['id'], Bag(dict(row)))
        return result

    @public_method
    def revokeDevice(self, pkey=None):
        """Revoke the device ``pkey`` of the logged user: its key no longer logs in."""
        with self.recordToUpdate(pkey) as record:
            if record['user_id'] != self.db.currentEnv.get('user_id'):
                raise self.exception('business_logic', msg='!![en]This device belongs to another user')
            record['revoked'] = True
        self.db.commit()

    @public_method
    def confirmChallenge(self, text=None):
        """A single use challenge for GenroApp to sign with ``text``, the action the logged
        user confirms on this page; kept in the page store. None for a text GenroApp refuses."""
        if not self.confirmText(text):
            return None
        challenge = self.newChallenge()
        challenge['text'] = text
        with self.db.application.site.currentPage.pageStore() as ps:
            ps.setItem(CONFIRM_CHALLENGE, challenge)
            ps.setItem(CONFIRMED, None)
        return challenge['challenge']

    @public_method
    def confirmSigned(self, key_id=None, signature=None, connector_id=None):
        """Check the confirmation signed by GenroApp for the challenge of this page: True when
        a registered key of the logged user signed it. ``popConfirmed`` then answers once."""
        page = self.db.application.site.currentPage
        with page.pageStore() as ps:
            asked = ps.getItem(CONFIRM_CHALLENGE)
            ps.setItem(CONFIRM_CHALLENGE, None)
            ps.setItem(CONFIRMED, None)
        challenge = self.validChallenge(asked)
        user = self.db.currentEnv.get('user')
        if not challenge or not user:
            return False
        device = self.verifyConfirm(origin=page.request.host_url.rstrip('/'), user=user, challenge=challenge,
                                    text=asked['text'], key_id=key_id, signature=signature,
                                    connector_id=connector_id)
        if not device:
            return False
        self.db.commit()
        with page.pageStore() as ps:
            ps.setItem(CONFIRMED, Bag(dict(text=asked['text'], user=user,
                                           expires=time.time() + CHALLENGE_SECONDS)))
        return True

    def popConfirmed(self, text):
        """True, once, when the logged user confirmed ``text`` on this page with the identity
        check of the computer in the last CHALLENGE_SECONDS. The server method that acts on
        ``text`` calls it before acting: the answer of the page alone proves nothing."""
        with self.db.application.site.currentPage.pageStore() as ps:
            confirmed = ps.getItem(CONFIRMED)
            ps.setItem(CONFIRMED, None)
        if not confirmed or confirmed['expires'] < time.time():
            return False
        return confirmed['text'] == text and confirmed['user'] == self.db.currentEnv.get('user')
