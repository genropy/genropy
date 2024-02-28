#!/usr/bin/env python3

import time
import hashlib
import base64
import hmac
import logging
import datetime

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
        payload = f"{value}{self.payload_sep}"
        if expire_ts:
            payload = f"{payload}{expire_ts}"
        signed_payload = self._sign(payload)
        return f"{payload}{self.payload_sep}{signed_payload}"
    
    def generate_url(self, url, expire_ts=None,expire_minutes=None):
        if isinstance(expire_ts,datetime.date):
            expire_ts = datetime.datetime(expire_ts.year,expire_ts.month,expire_ts.day)
        if expire_minutes and not expire_ts:
            expire_ts = datetime.datetime.utcnow() + datetime.timedelta(minutes=expire_minutes)
        if isinstance(expire_ts,datetime.datetime):
            expire_ts = str(int(expire_ts.timestamp()))
        ts = expire_ts or ''
        first_separator = "&" if len(url.split('?',1))>1 else '?'
        newurl = f'{url}{first_separator}_vld={ts}'
        signature = self._sign(newurl)
        return f"{newurl}{self.payload_sep}{signature}"
    
    
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
                if int(expire_ts) < int(datetime.datetime.utcnow().timestamp()):
                    raise AuthTokenExpired("Token has expired!")                    
        return val

    
    def verify_url(self, url,_vld=''):
        log.info(f"Verifying url {url}")
        if not (_vld and (self.payload_sep in _vld)):
            return 'not_valid'
        val, signature = url.rsplit(self.payload_sep, 1)
        print('val',val,'signature',signature)
        if self._sign(val) != signature:
            return 'not_valid'
        expire_ts = _vld.split(self.payload_sep)[0]
        ts_now = datetime.datetime.utcnow().timestamp()
        print('expire_ts',expire_ts,'ts_now',int(ts_now))
        if expire_ts and ts_now>int(expire_ts):
            return 'expired'                 
    
if __name__ == "__main__":
    SECRET_KEY = "mysecretkey"
    SALT = "mysalt"
    payload = "username"
    
    log.debug(f"New Token Generor with key {SECRET_KEY} and salt {SALT}")
    ATG = AuthTokenGenerator(SECRET_KEY, SALT)

    # base signature
    log.debug(f"Signing payload {payload}")
    r = ATG.generate(payload)
    log.debug(f"Got signed payload '{r}'")
    log.debug(f"Verifying payload '{r}'")
    try:
        r = ATG.verify(r)
        log.debug(f"Payload is correctly signed and contains: {r}")
    except Exception as e:
        log.debug(f"Verification failed: {e}")

    # timed operations
    log.debug(f"Signing timestamped payload {payload}")
    # expire in 10 seconds
    r = ATG.generate("username", expire_ts=int(time.time())+2)
    log.debug(f"Got timestamped signed payload '{r}'")
    log.debug(f"Verifying timestamped payload '{r}'")
    try:
        r = ATG.verify(r)
        log.debug(f"Payload is correctly signed and contains: {r}")
    except Exception as e:
        log.debug(f"Verification failed: {e}")

    # testing errors
    log.debug(f"Signing timestamped payload {payload}")
    r = ATG.generate("username", expire_ts=int(time.time())+2)
    log.debug(f"Got timestamped signed payload '{r}'")
    pause = 2
    log.debug(f"Pause for {pause} seconds")
    time.sleep(pause)
    log.debug(f"Verifying timestamped payload '{r}'")
    try:
        r = ATG.verify(r)
        log.debug(f"Payload is correctly signed and contains: {r}")
    except Exception as e:
        log.debug(f"Verification failed: {e}")
    
