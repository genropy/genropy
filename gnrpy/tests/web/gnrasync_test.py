import sys

if sys.platform != 'win32':
    # the whole gnarsync implementation is currently
    # depending on AF_UNIX sockets, which has been
    # partially introduced on Windows 10 (but apparently
    # without datagram support), so we'll skip
    # the tests on such platform
    import gnr.web.gnrasync # noqa: F401
