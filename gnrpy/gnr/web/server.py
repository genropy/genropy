import werkzeug
if werkzeug.__version__<='2.0.0':
    from gnr.web.serverwsgi_legacy import Server
else:
    from gnr.web.serverwsgi import Server
# preserve the following line for backward compatibility
NewServer = Server