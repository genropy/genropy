"""Column-level encryption engine for GenroPy.

Provides three encryption modes:

- ``'R'`` (Reversible): Fernet (AES-128-CBC + HMAC-SHA256).
  Non-deterministic — same plaintext produces different ciphertext each time.
  Use for secrets (API tokens, service passwords).

- ``'Q'`` (Querable): AES-SIV deterministic encryption.
  Same plaintext + same key always produces the same ciphertext.
  Use for searchable personal data (tax IDs, IBANs).

- ``'X'`` (one-shot): SHA-256 hash with per-value random salt.
  Irreversible — original value cannot be recovered.
  Use for tokens you issue (auth tokens, API keys given to users).

Encrypted values are stored with a prefix to identify the mode:
``$R$<base64>``, ``$Q$<base64>``, ``$X$<hex_salt>$<hex_hash>``.
"""

import hashlib
import os
import base64

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.ciphers.aead import AESSIV
except ImportError:
    raise ImportError(
        "The 'cryptography' package is required for encrypted columns. "
        "Install it with: pip install genropy[encryption]"
    )


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


class ColumnEncryptor:
    """Encrypt and decrypt column values using one of the three modes.

    Args:
        secret_key: The master secret key string.
    """

    def __init__(self, secret_key):
        self._fernet = Fernet(_derive_fernet_key(secret_key))
        self._siv_key = _derive_siv_key(secret_key)

    def encrypt(self, value, mode='R'):
        """Encrypt a value according to the specified mode.

        Args:
            value: The plaintext string to encrypt.
            mode: One of ``'R'``, ``'Q'``, ``'X'``.

        Returns:
            The encrypted string with mode prefix.
        """
        if value is None:
            return None
        text = str(value).encode('utf-8')
        if mode == 'R':
            return PREFIX_R + self._fernet.encrypt(text).decode('ascii')
        if mode == 'Q':
            ct = AESSIV(self._siv_key).encrypt(text, None)
            return PREFIX_Q + base64.b64encode(ct).decode('ascii')
        if mode == 'X':
            salt = os.urandom(SALT_LENGTH)
            h = hashlib.sha256(salt + text).hexdigest()
            return PREFIX_X + salt.hex() + '$' + h
        raise ValueError(f"Unknown encryption mode: {mode!r}")

    def decrypt(self, value):
        """Decrypt an encrypted value, detecting the mode from its prefix.

        For mode ``'X'`` (one-shot hash), returns ``None`` since the original
        value cannot be recovered.

        Args:
            value: The stored encrypted string (with prefix).

        Returns:
            The decrypted plaintext string, or ``None`` for mode ``'X'``.
            If the value has no recognized prefix, it is returned as-is
            (plain-text fallback for migration).
        """
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        if value.startswith(PREFIX_R):
            token = value[len(PREFIX_R):].encode('ascii')
            return self._fernet.decrypt(token).decode('utf-8')
        if value.startswith(PREFIX_Q):
            ct = base64.b64decode(value[len(PREFIX_Q):])
            return AESSIV(self._siv_key).decrypt(ct, None).decode('utf-8')
        if value.startswith(PREFIX_X):
            return None
        return value

    def verify(self, plain_value, stored_hash):
        """Verify a plain value against a stored mode-X hash.

        Args:
            plain_value: The candidate plaintext string.
            stored_hash: The stored ``$X$<salt>$<hash>`` string.

        Returns:
            ``True`` if the plain value matches the stored hash.
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
