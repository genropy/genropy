import pytest
import datetime
import time
from gnr.core import gnrcrypto as gc

class TestGnrCrypto():
    def setup_class(cls):
        cls.SECRET_KEY = "mysecretkey"
        cls.SALT = "mysalt"
        cls.atg = gc.AuthTokenGenerator(cls.SECRET_KEY, cls.SALT)
        cls.failing_atg = gc.AuthTokenGenerator(cls.SECRET_KEY+"1", cls.SALT+"1")
        cls.payload = "brian cohen"
        cls.url = "/unsubscribe/12345678?q=1"
        
    def test_generate_format(self):
        r = self.atg.generate(self.payload)
        r2 = r.replace(";", "@")
        with pytest.raises(gc.AuthTokenError):
            self.atg.verify(r2)
            
    def test_generate_verify(self):
        r = self.atg.generate(self.payload)
        r2 = self.atg.verify(r)
        assert r2 == self.payload
        with pytest.raises(gc.AuthTokenError):
            self.failing_atg.verify(r)

    def test_verify_tampered_signature(self):
        r = self.atg.generate(self.payload)
        tampered = r[:-1] + ('A' if r[-1] != 'A' else 'B')
        with pytest.raises(gc.AuthTokenError):
            self.atg.verify(tampered)

    def test_verify_non_numeric_expiry_is_ignored(self):
        # Documents current, unchanged behaviour: a non-numeric expire_ts
        # fails the isnumeric() gate and expiry is silently skipped, so the
        # token verifies as if it never carried an expiry at all.
        forged = f"{self.payload}{self.atg.payload_sep}2020-01-01"
        forged_signature = self.atg._sign(forged)
        forged_token = f"{forged}{self.atg.payload_sep}{forged_signature}"
        assert self.atg.verify(forged_token) == self.payload

    def test_generate_timed(self):
        r = self.atg.generate(self.payload, expire_ts=int(time.time()+1))
        assert self.atg.verify(r) == self.payload
        time.sleep(3)
        with pytest.raises(gc.AuthTokenExpired):
            r = self.atg.verify(r)

    def test_generate_verify_url(self):
        qs_param = "pippo"
        r = self.atg.generate_url(self.url, expire_ts=int(time.time()+1), qs_param=qs_param)
        assert qs_param in r

        r2 = self.atg.verify_url(r, qs_param="wrong")
        assert r2 == "not_valid"
        
        r2 = self.atg.verify_url(r.replace(";", "@"), qs_param=qs_param)
        assert r2 == "not_valid"

        wrong_signature = list(r[:])
        wrong_signature[wrong_signature.index(";")+1] = "@"
        wrong_signature = "".join(wrong_signature)
        
        r2 = self.atg.verify_url(wrong_signature, qs_param=qs_param)
        assert r2 == "not_valid"

        r2 = self.atg.verify_url(r, qs_param=qs_param)

        # verify expiration
        time.sleep(2)
        r2 = self.atg.verify_url(r, qs_param=qs_param)
        assert r2 == "expired"

        # with date object
        r = self.atg.generate_url(self.url, expire_ts=datetime.date(2024,1,1))
        r2 = self.atg.verify_url(r)
        assert r2 == "expired"

        # with expire minutes - valid
        r = self.atg.generate_url(self.url, expire_minutes=200)
        r2 = self.atg.verify_url(r)
        assert r2 == None

        # with expire minutes
        r = self.atg.generate_url(self.url, expire_minutes=0.01)
        time.sleep(1)
        r2 = self.atg.verify_url(r)
        assert r2 == "expired"

    def test_verify_url_non_numeric_expiry(self):
        # A malformed _vld value (not produced by generate_url, e.g. a
        # hand-crafted or corrupted link) must be rejected through the
        # function's own "not_valid" contract, not raise ValueError.
        separator = "&" if "?" in self.url else "?"
        url = f"{self.url}{separator}_vld=2020-01-01"
        signature = self.atg._sign(url)
        forged_url = f"{url}{self.atg.payload_sep}{signature}"
        assert self.atg.verify_url(forged_url) == "not_valid"
