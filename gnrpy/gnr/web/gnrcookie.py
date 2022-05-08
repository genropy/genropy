import base64
import pickle
import warnings
from hashlib import sha1 as _default_hash
from time import time
import sys
from datetime import date, datetime
from werkzeug.urls import url_quote_plus
from werkzeug.urls import url_unquote_plus
import  marshal
import hmac
from werkzeug.datastructures import CallbackDict

class ModificationTrackingDict(CallbackDict):
    __slots__ = ("modified",)

    def __init__(self, *args, **kwargs):
        def on_update(self):
            self.modified = True

        self.modified = False
        super(ModificationTrackingDict, self).__init__(on_update=on_update)
        dict.update(self, *args, **kwargs)

    def copy(self):
        """Create a flat copy of the dict."""
        missing = object()
        result = object.__new__(self.__class__)
        for name in self.__slots__:
            val = getattr(self, name, missing)
            if val is not missing:
                setattr(result, name, val)
        return result

    def __copy__(self):
        return self.copy()



_epoch_ord = date(1970, 1, 1).toordinal()
iteritems = lambda d, *args, **kwargs: iter(d.items(*args, **kwargs))

str_to_bytes = lambda s: s.encode("utf-8") if isinstance(s, str) else s
safe_str_cmp = lambda a, b: hmac.compare_digest(str_to_bytes(a), str_to_bytes(b))

def _date_to_unix(arg):
    if isinstance(arg, datetime):
        arg = arg.utctimetuple()
    elif isinstance(arg, (float,int)):
        return int(arg)
    year, month, day, hour, minute, second = arg[:6]
    days = date(year, month, 1).toordinal() - _epoch_ord + day - 1
    hours = days * 24 + hour
    minutes = hours * 60 + minute
    seconds = minutes * 60 + second
    return seconds

def to_bytes(x, charset=sys.getdefaultencoding(), errors="strict"):
    if x is None:
        return None
    if isinstance(x, (bytes, bytearray, memoryview)):  # noqa
        return bytes(x)
    if isinstance(x, str):
        return x.encode(charset, errors)
    raise TypeError("Expected bytes")
def to_native(x, charset=sys.getdefaultencoding(), errors="strict"):
    if x is None or isinstance(x, str):
        return x
    return x.decode(charset, errors)



class UnquoteError(Exception):
    """Internal exception used to signal failures on quoting."""


class SecureCookie(ModificationTrackingDict):
    """Represents a secure cookie. You can subclass this class and
    provide an alternative mac method. The import thing is that the mac
    method is a function with a similar interface to the hashlib.
    Required methods are :meth:`update` and :meth:`digest`.

    Example usage:

    >>> x = SecureCookie({"foo": 42, "baz": (1, 2, 3)}, "deadbeef")
    >>> x["foo"]
    42
    >>> x["baz"]
    (1, 2, 3)
    >>> x["blafasel"] = 23
    >>> x.should_save
    True

    :param data: The initial data. Either a dict, list of tuples, or
        ``None``.
    :param secret_key: The secret key. If not set ``None`` or not
        specified it has to be set before :meth:`serialize` is called.
    :param new: The initial value of the ``new`` flag.
    """

    #: The hash method to use. This has to be a module with a new
    #: function or a function that creates a hashlib object, such as
    #: func:`hashlib.md5`. Subclasses can override this attribute. The
    #: default hash is sha1. Make sure to wrap this in
    #: :func:`staticmethod` if you store an arbitrary function there
    #: such as :func:`hashlib.sha1` which might be implemented as a
    #: function.
    hash_method = staticmethod(_default_hash)

    #: The module used for serialization. Should have a ``dumps`` and a
    #: ``loads`` method that takes bytes. The default is :mod:`pickle`.
    #:
    #: .. versionchanged:: 0.1
    #:     The default of ``pickle`` will change to :mod:`json` in 1.0.
    serialization_method = pickle

    #: If the contents should be base64 quoted. This can be disabled if
    #: the serialization process returns cookie safe strings only.
    quote_base64 = True

    def __init__(self, data=None, secret_key=None, new=True):
        ModificationTrackingDict.__init__(self, data or ())

        if secret_key is not None:
            secret_key = to_bytes(secret_key, "utf-8")

        self.secret_key = secret_key
        self.new = new

        if self.serialization_method is pickle:
            warnings.warn(
                "The default SecureCookie.serialization_method will"
                " change from pickle to json in 1.0. To upgrade"
                " existing tokens, override unquote to try pickle if"
                " json fails."
            )

    def __repr__(self):
        return "<%s %s%s>" % (
            self.__class__.__name__,
            dict.__repr__(self),
            "*" if self.should_save else "",
        )

    @property
    def should_save(self):
        """True if the session should be saved. By default this is only
        true for :attr:`modified` cookies, not :attr:`new`.
        """
        return self.modified

    @classmethod
    def quote(cls, value):
        """Quote the value for the cookie. This can be any object
        supported by :attr:`serialization_method`.

        :param value: The value to quote.
        """
        if cls.serialization_method is not None:
            value = cls.serialization_method.dumps(value)

        if cls.quote_base64:
            value = b"".join(
                base64.b64encode(to_bytes(value, "utf8")).splitlines()
            ).strip()

        return value

    @classmethod
    def unquote(cls, value):
        """Unquote the value for the cookie. If unquoting does not work
        a :exc:`UnquoteError` is raised.

        :param value: The value to unquote.
        """
        try:
            if cls.quote_base64:
                value = base64.b64decode(value)

            if cls.serialization_method is not None:
                value = cls.serialization_method.loads(value)

            return value
        except Exception:
            # Unfortunately pickle and other serialization modules can
            # cause pretty much every error here. If we get one we catch
            # it and convert it into an UnquoteError.
            raise UnquoteError()

    def serialize(self, expires=None):
        """Serialize the secure cookie into a string.

        If expires is provided, the session will be automatically
        invalidated after expiration when you unseralize it. This
        provides better protection against session cookie theft.

        :param expires: An optional expiration date for the cookie (a
            :class:`datetime.datetime` object).
        """
        if self.secret_key is None:
            raise RuntimeError("no secret key defined")

        if expires:
            self["_expires"] = _date_to_unix(expires)

        result = []
        mac = hmac.new(self.secret_key, None, self.hash_method)

        for key, value in sorted(self.items()):
            result.append(
                (
                    "%s=%s" % (url_quote_plus(key), self.quote(value).decode("ascii"))
                ).encode("ascii")
            )
            mac.update(b"|" + result[-1])

        return b"?".join([base64.b64encode(mac.digest()).strip(), b"&".join(result)])

    @classmethod
    def unserialize(cls, string, secret_key):
        """Load the secure cookie from a serialized string.

        :param string: The cookie value to unserialize.
        :param secret_key: The secret key used to serialize the cookie.
        :return: A new :class:`SecureCookie`.
        """
        if isinstance(string, str):
            string = string.encode("utf-8", "replace")

        if isinstance(secret_key, str):
            secret_key = secret_key.encode("utf-8", "replace")

        try:
            base64_hash, data = string.split(b"?", 1)
        except (ValueError, IndexError):
            items = ()
        else:
            items = {}
            mac = hmac.new(secret_key, None, cls.hash_method)

            for item in data.split(b"&"):
                mac.update(b"|" + item)

                if b"=" not in item:
                    items = None
                    break

                key, value = item.split(b"=", 1)
                # try to make the key a string
                key = url_unquote_plus(key.decode("ascii"))

                try:
                    key = to_native(key)
                except UnicodeError:
                    pass

                items[key] = value

            # no parsing error and the mac looks okay, we can now
            # sercurely unpickle our cookie.
            try:
                client_hash = base64.b64decode(base64_hash)
            except TypeError:
                items = client_hash = None

            if items is not None and safe_str_cmp(client_hash, mac.digest()):
                try:
                    for key, value in iteritems(items):
                        items[key] = cls.unquote(value)
                except UnquoteError:
                    items = ()
                else:
                    if "_expires" in items:
                        if time() > items["_expires"]:
                            items = ()
                        else:
                            del items["_expires"]
            else:
                items = ()
        return cls(items, secret_key, False)

    @classmethod
    def load_cookie(cls, request, key="session", secret_key=None):
        """Load a :class:`SecureCookie` from a cookie in the request. If
        the cookie is not set, a new :class:`SecureCookie` instance is
        returned.

        :param request: A request object that has a `cookies` attribute
            which is a dict of all cookie values.
        :param key: The name of the cookie.
        :param secret_key: The secret key used to unquote the cookie.
            Always provide the value even though it has no default!
        """
        data = request.cookies.get(key)

        if not data:
            return cls(secret_key=secret_key)

        return cls.unserialize(data, secret_key)

    def save_cookie(
        self,
        response,
        key="session",
        expires=None,
        session_expires=None,
        max_age=None,
        path="/",
        domain=None,
        secure=None,
        httponly=True,
        force=False,
    ):
        """Save the data securely in a cookie on response object. All
        parameters that are not described here are forwarded directly
        to :meth:`~BaseResponse.set_cookie`.

        :param response: A response object that has a
            :meth:`~BaseResponse.set_cookie` method.
        :param key: The name of the cookie.
        :param session_expires: The expiration date of the secure cookie
            stored information. If this is not provided the cookie
            ``expires`` date is used instead.
        """
        if force or self.should_save:
            data = self.serialize(session_expires or expires)
            response.set_cookie(
                key,
                data,
                expires=expires,
                max_age=max_age,
                path=path,
                domain=domain,
                secure=secure,
                httponly=httponly,
            )


class BaseCookie(object):
    def __init__(self, value=None):
        self._value = value

    def output(self):
        return self.value.encode('ascii')

class MarshalCookie(SecureCookie):
    serialization_method = marshal

    def output(self):
        return self.serialize()

    