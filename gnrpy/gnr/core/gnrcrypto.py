#!/usr/bin/env python3

import hashlib
import base64
import hmac
import os
import datetime
from urllib.parse import parse_qs, urlparse

from gnr.core import logger


# ---------------------------------------------------------------------------
#  Encryptor — three-mode column encryption (R/Q/X)
# ---------------------------------------------------------------------------

SALT_LENGTH = 16
PREFIX_R = '$R$'
PREFIX_Q = '$Q$'
PREFIX_X = '$X$'


def _derive_fernet_key(secret_key):
    """Derive a 32-byte url-safe base64 Fernet key from an arbitrary secret."""
    dk = hashlib.sha256(secret_key.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(dk)


def _derive_siv_key(secret_key):
    """Derive a 64-byte key for AES-SIV (requires 256 or 512 bit key).

    AES-SIV with a 512-bit key uses AES-256 internally.
    """
    dk = hashlib.sha512(secret_key.encode('utf-8')).digest()
    return dk


class Encryptor:
    """Encrypt and decrypt values using one of three modes.

    Modes:

    - ``'R'`` (Reversible): Fernet (AES-128-CBC + HMAC-SHA256).
      Non-deterministic. Use for secrets (API tokens, service passwords).
    - ``'Q'`` (Querable): AES-SIV deterministic encryption.
      Same plaintext + same key = same ciphertext. Use for searchable
      personal data (tax IDs, IBANs).
    - ``'X'`` (one-shot): SHA-256 hash with per-value random salt.
      Irreversible. Use for tokens you issue.

    Encrypted values are stored with a prefix: ``$R$``, ``$Q$``, ``$X$``.

    The instance is always created (even without a key or without
    ``cryptography`` installed). Errors are raised only when you actually
    call ``encrypt()`` or ``decrypt()``.

    Args:
        secret_key: The master secret key string, or ``None``.
    """

    def __init__(self, secret_key=None):
        self._secret_key = secret_key
        self._initialized = False
        self._fernet = None
        self._siv_key = None
        self._aessiv_cls = None

    def _ensure_initialized(self):
        """Initialize crypto primitives on first use. Raises if key or
        cryptography package is missing."""
        if self._initialized:
            return
        if not self._secret_key:
            raise ValueError(
                "No encryption key configured. "
                "Set encryption_key in db config or GNR_ENCRYPTION_KEY env var."
            )
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives.ciphers.aead import AESSIV

        self._fernet = Fernet(_derive_fernet_key(self._secret_key))
        self._siv_key = _derive_siv_key(self._secret_key)
        self._aessiv_cls = AESSIV
        self._initialized = True

    @property
    def has_key(self):
        """Return ``True`` if an encryption key is configured."""
        return bool(self._secret_key)

    def encrypt(self, value, mode='R'):
        """Encrypt a value according to the specified mode.

        Args:
            value: The plaintext string to encrypt.
            mode: One of ``'R'``, ``'Q'``, ``'X'``.

        Returns:
            The encrypted string with mode prefix.

        Raises:
            ValueError: If no encryption key is configured.
            ImportError: If ``cryptography`` is not installed.
        """
        if value is None:
            return None
        self._ensure_initialized()
        text = str(value).encode('utf-8')
        if mode == 'R':
            return PREFIX_R + self._fernet.encrypt(text).decode('ascii')
        if mode == 'Q':
            ct = self._aessiv_cls(self._siv_key).encrypt(text, None)
            return PREFIX_Q + base64.b64encode(ct).decode('ascii')
        if mode == 'X':
            salt = os.urandom(SALT_LENGTH)
            h = hashlib.sha256(salt + text).hexdigest()
            return PREFIX_X + salt.hex() + '$' + h
        raise ValueError(f"Unknown encryption mode: {mode!r}")

    def decrypt(self, value):
        """Decrypt an encrypted value, detecting the mode from its prefix.

        For mode ``'X'``, returns ``None`` (irreversible).
        Values without a recognized prefix are returned as-is (migration fallback).

        Raises:
            ValueError: If no encryption key is configured.
            ImportError: If ``cryptography`` is not installed.
        """
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        if value.startswith(PREFIX_X):
            return None
        if not (value.startswith(PREFIX_R) or value.startswith(PREFIX_Q)):
            return value
        self._ensure_initialized()
        if value.startswith(PREFIX_R):
            token = value[len(PREFIX_R):].encode('ascii')
            return self._fernet.decrypt(token).decode('utf-8')
        if value.startswith(PREFIX_Q):
            ct = base64.b64decode(value[len(PREFIX_Q):])
            return self._aessiv_cls(self._siv_key).decrypt(ct, None).decode('utf-8')

    def verify(self, plain_value, stored_hash):
        """Verify a plain value against a stored mode-X hash.

        Returns ``True`` if the plain value matches.
        """
        if not stored_hash or not isinstance(stored_hash, str):
            return False
        if not stored_hash.startswith(PREFIX_X):
            return False
        parts = stored_hash[len(PREFIX_X):].split('$', 1)
        if len(parts) != 2:
            return False
        salt = bytes.fromhex(parts[0])
        expected_hash = parts[1]
        text = str(plain_value).encode('utf-8')
        actual_hash = hashlib.sha256(salt + text).hexdigest()
        return actual_hash == expected_hash

    def decrypt_row(self, row, encrypted_columns):
        """Decrypt all encrypted fields in a row dict, in place.

        Args:
            row: A dict-like row object (modified in place).
            encrypted_columns: A dict ``{field_name: mode}`` from the
                compiled query's ``encryptedColumns``.
        """
        for field in encrypted_columns:
            v = row.get(field)
            if v is not None:
                row[field] = self.decrypt(v)


# ---------------------------------------------------------------------------
#  AuthTokenGenerator — HMAC-based signed tokens
# ---------------------------------------------------------------------------

class AuthTokenError(Exception):
    """
    The token is not valid
    """
    pass


class AuthTokenExpired(AuthTokenError):
    """
    The token is expired
    """


class AuthTokenGenerator:
    def __init__(self, enckey, salt=None, payload_sep=";"):
        self.enckey = enckey
        self.payload_sep = payload_sep
        self.salt = salt or ''

    def _b64_encode(self, s):
        return base64.urlsafe_b64encode(s).strip(b'=')

    def _sign(self, value):
        h = hashlib.sha1
        k2 = h(self.salt.encode('utf-8') + self.enckey.encode('utf-8')).digest()
        payload = hmac.new(k2, msg=value.encode('utf-8'), digestmod=h)
        return self._b64_encode(payload.digest()).decode()

    def generate(self, value, expire_ts=None):
        logger.info(f"Generating payload {value}")
        payload = f"{value}"
        if expire_ts:
            payload = f"{payload}{self.payload_sep}{expire_ts}"
        signed_payload = self._sign(payload)
        return f"{payload}{self.payload_sep}{signed_payload}"

    def verify(self, value):
        logger.info(f"Verifying payload {value}")
        if self.payload_sep not in value:
            raise AuthTokenError("Payload format error")

        val, signature = value.rsplit(self.payload_sep, 1)
        if self._sign(val) != signature:
            raise AuthTokenError("Token is not valid")
        if self.payload_sep in val:
            # verify timestamp
            val, expire_ts = val.rsplit(self.payload_sep, 1)
            if expire_ts and expire_ts.isnumeric():
                if int(expire_ts) < int(datetime.datetime.now(datetime.timezone.utc).timestamp()):
                    raise AuthTokenExpired("Token has expired!")
        return val

    def generate_url(self, url,
                     expire_ts=None,
                     expire_minutes=None,
                     qs_param="_vld"):
        if isinstance(expire_ts, datetime.date):
            expire_ts = datetime.datetime(expire_ts.year, expire_ts.month, expire_ts.day)
        if expire_minutes and not expire_ts:
            expire_ts = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=expire_minutes)
        if isinstance(expire_ts, datetime.datetime):
            expire_ts = str(int(expire_ts.timestamp()))

        ts = expire_ts or ''
        #first_separator = "&" if len(url.split('?',1))>1 else '?'
        first_separator = "?" in url and "&" or "?"
        newurl = f'{url}{first_separator}{qs_param}={ts}'
        signature = self._sign(newurl)
        return f"{newurl}{self.payload_sep}{signature}"

    def verify_url(self, url, qs_param="_vld"):
        logger.info(f"Verifying url {url}")
        signature_token = parse_qs(urlparse(url).query).get(qs_param, [''])[0]
        if not signature_token:
            return "not_valid"

        if self.payload_sep not in signature_token:
            return "not_valid"

        val, signature = url.rsplit(self.payload_sep, 1)
        if self._sign(val) != signature:
            return "not_valid"

        expire_ts = signature_token.split(self.payload_sep)[0]
        if expire_ts:
            ts_now = datetime.datetime.now(datetime.timezone.utc).timestamp()
            if ts_now > int(expire_ts):
                return "expired"
