#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gnrcrypto - Authentication token generation and verification.

This module provides classes for generating and verifying signed authentication
tokens with optional expiration timestamps. It supports both plain payloads
and URL signing.

Classes:
    AuthTokenError: Base exception for token validation errors.
    AuthTokenExpired: Exception raised when a token has expired.
    AuthTokenGenerator: Token generation and verification utility.

Example:
    >>> from gnr.core.gnrcrypto import AuthTokenGenerator
    >>> atg = AuthTokenGenerator(enckey='secret', salt='mysalt')
    >>> token = atg.generate('user123', expire_ts=1735689600)
    >>> value = atg.verify(token)
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import hmac
from urllib.parse import parse_qs, urlparse

from gnr.core import logger


class AuthTokenError(Exception):
    """Exception raised when a token is not valid.

    This is the base exception for all token validation errors.
    """

    pass


class AuthTokenExpired(AuthTokenError):
    """Exception raised when a token has expired.

    Inherits from AuthTokenError so catching AuthTokenError will also
    catch expired token exceptions.
    """

    pass


class AuthTokenGenerator:
    """Generates and verifies signed authentication tokens.

    Uses HMAC-SHA1 for signing tokens with an optional salt. Supports
    both plain payload tokens and URL signing with expiration timestamps.

    Args:
        enckey: The secret encryption key for signing.
        salt: Optional salt to strengthen the key. Defaults to empty string.
        payload_sep: Separator used between payload parts. Defaults to ';'.

    Attributes:
        enckey: The encryption key.
        payload_sep: The payload separator.
        salt: The salt value.

    Example:
        >>> atg = AuthTokenGenerator('mysecret', salt='pepper')
        >>> token = atg.generate('user@example.com')
        >>> atg.verify(token)
        'user@example.com'
    """

    def __init__(
        self,
        enckey: str,
        salt: str | None = None,
        payload_sep: str = ";",
    ) -> None:
        self.enckey = enckey
        self.payload_sep = payload_sep
        self.salt = salt or ""

    def _b64_encode(self, s: bytes) -> bytes:
        """Encode bytes to URL-safe base64 without padding.

        Args:
            s: Bytes to encode.

        Returns:
            URL-safe base64 encoded bytes without trailing '=' padding.
        """
        return base64.urlsafe_b64encode(s).strip(b"=")

    def _sign(self, value: str) -> str:
        """Create HMAC-SHA1 signature for a value.

        Args:
            value: The string value to sign.

        Returns:
            URL-safe base64 encoded signature.
        """
        h = hashlib.sha1
        k2 = h(self.salt.encode("utf-8") + self.enckey.encode("utf-8")).digest()
        payload = hmac.new(k2, msg=value.encode("utf-8"), digestmod=h)
        return self._b64_encode(payload.digest()).decode()

    def generate(self, value: str, expire_ts: int | str | None = None) -> str:
        """Generate a signed token for a value.

        Args:
            value: The payload value to encode in the token.
            expire_ts: Optional expiration timestamp (Unix epoch seconds).

        Returns:
            A signed token string in the format 'value;[expire_ts;]signature'.
        """
        logger.info(f"Generating payload {value}")
        payload = f"{value}"
        if expire_ts:
            payload = f"{payload}{self.payload_sep}{expire_ts}"
        signed_payload = self._sign(payload)
        return f"{payload}{self.payload_sep}{signed_payload}"

    def verify(self, value: str) -> str:
        """Verify a signed token and return its payload.

        Args:
            value: The signed token string to verify.

        Returns:
            The original payload value if verification succeeds.

        Raises:
            AuthTokenError: If the token format is invalid or signature doesn't match.
            AuthTokenExpired: If the token has expired.
        """
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
                if int(expire_ts) < int(
                    datetime.datetime.now(datetime.timezone.utc).timestamp()
                ):
                    raise AuthTokenExpired("Token has expired!")
        return val

    def generate_url(
        self,
        url: str,
        expire_ts: datetime.datetime | datetime.date | int | str | None = None,
        expire_minutes: int | None = None,
        qs_param: str = "_vld",
    ) -> str:
        """Generate a signed URL with optional expiration.

        Args:
            url: The URL to sign.
            expire_ts: Optional expiration as datetime, date, or Unix timestamp.
            expire_minutes: Optional minutes from now until expiration.
            qs_param: Query string parameter name for the validation token.

        Returns:
            The signed URL with validation token appended.

        Note:
            If both expire_ts and expire_minutes are provided, expire_ts takes
            precedence.
        """
        ts: str | int
        if isinstance(expire_ts, datetime.date) and not isinstance(
            expire_ts, datetime.datetime
        ):
            expire_ts = datetime.datetime(
                expire_ts.year, expire_ts.month, expire_ts.day
            )
        if expire_minutes and not expire_ts:
            expire_ts = datetime.datetime.now(
                datetime.timezone.utc
            ) + datetime.timedelta(minutes=expire_minutes)
        if isinstance(expire_ts, datetime.datetime):
            ts = str(int(expire_ts.timestamp()))
        else:
            ts = expire_ts or ""

        first_separator = "&" if "?" in url else "?"
        newurl = f"{url}{first_separator}{qs_param}={ts}"
        signature = self._sign(newurl)
        return f"{newurl}{self.payload_sep}{signature}"

    def verify_url(self, url: str, qs_param: str = "_vld") -> str | None:
        """Verify a signed URL.

        Args:
            url: The signed URL to verify.
            qs_param: Query string parameter name containing the validation token.

        Returns:
            None if valid and not expired.
            'not_valid' if the signature doesn't match or token is missing.
            'expired' if the token has expired.
        """
        logger.info(f"Verifying url {url}")
        signature_token = parse_qs(urlparse(url).query).get(qs_param, [""])[0]
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

        return None


__all__ = ["AuthTokenError", "AuthTokenExpired", "AuthTokenGenerator"]
