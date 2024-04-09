#!/usr/bin/env python3

import time
import hashlib
import base64
import hmac
import logging
import datetime
from urllib.parse import parse_qs, urlparse

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
FORMAT = '%(asctime)s  %(message)s'
logging.basicConfig(format=FORMAT)

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
        log.info(f"Generating payload {value}")
        payload = f"{value}"
        if expire_ts:
            payload = f"{payload}{self.payload_sep}{expire_ts}"
        signed_payload = self._sign(payload)
        return f"{payload}{self.payload_sep}{signed_payload}"
    
    def verify(self, value):
        log.info(f"Verifying payload {value}")
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
        if isinstance(expire_ts,datetime.date):
            expire_ts = datetime.datetime(expire_ts.year,expire_ts.month,expire_ts.day)
        if expire_minutes and not expire_ts:
            expire_ts = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=expire_minutes)
        if isinstance(expire_ts,datetime.datetime):
            expire_ts = str(int(expire_ts.timestamp()))

        ts = expire_ts or ''
        #first_separator = "&" if len(url.split('?',1))>1 else '?'
        first_separator = "?" in url and "&" or "?"
        newurl = f'{url}{first_separator}{qs_param}={ts}'
        signature = self._sign(newurl)
        return f"{newurl}{self.payload_sep}{signature}"

    def verify_url(self, url, qs_param="_vld"):
        log.info(f"Verifying url {url}")
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

    
