import pytest
import datetime
import time
from gnr.core import gnrcrypto as gc
from urllib.parse import parse_qs, urlparse

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
        
