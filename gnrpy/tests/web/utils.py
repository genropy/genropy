import sys
import os
import signal
import subprocess
import time
import io
from urllib.parse import urlencode
from wsgiref.util import setup_testing_defaults
from wsgiref.validate import validator

from gnr.web import logger

class WSGITestClient:
    """
    A simple WSGI client
    """
    def __init__(self, app, validate=True):
        self.app = validator(app) if validate else app

    def _make_environ(self, method, path='/', query_string='', body=None, headers=None):
        body = body or b''
        environ = {}
        setup_testing_defaults(environ)

        environ.update({
            'REQUEST_METHOD': method,
            'PATH_INFO': path,
            'QUERY_STRING': query_string,
            'wsgi.input': io.BytesIO(body),
            'CONTENT_LENGTH': str(len(body)),
        })

        if headers:
            for key, value in headers.items():
                http_key = 'HTTP_' + key.upper().replace('-', '_')
                environ[http_key] = value

        return environ

    def request(self, method, path='/', query=None, data=None, headers=None):
        query_string = urlencode(query or {})
        body = data.encode() if isinstance(data, str) else data or b''

        environ = self._make_environ(method, path, query_string, body, headers)
        result = {}

        def start_response(status, response_headers, exc_info=None):
            result['status'] = status
            result['headers'] = response_headers
            result['body'] = io.BytesIO()

            def write(data):
                result['body'].write(data)

            return write

        response_iter = self.app(environ, start_response)
        for data in response_iter:
            result['body'].write(data)
        if hasattr(response_iter, 'close'):
            response_iter.close()

        result['body'].seek(0)
        result['data'] = result['body'].read()
        return result

    def get(self, path='/', query=None, headers=None):
        return self.request('GET', path, query=query, headers=headers)

    def post(self, path='/', data=None, headers=None):
        return self.request('POST', path, data=data, headers=headers)


class ExternalProcess:
    """
    Simple object to maintain an active process during testing.
    It's developer responsibility to start/stop it in setup/teardown methods.
    """
    
    def __init__(self, command, port_check=None,
                 cwd=None, env=None):
        self.command = command
        self.cwd = cwd
        self.env = env
        self.port_check = port_check
        self.process = None

    def start(self):
        if self.process is not None:
            logger.info("Not starting %s since it's already running", self.command)
            return
        
        self.process = subprocess.Popen(
            self.command,
            cwd=self.cwd,
            env=self.env,
            stdout=sys.stdout,
            stderr=sys.stderr,
            preexec_fn=os.setsid
        )
        time.sleep(2)  # Adjust if your process needs more time

    def stop(self, timeout=5):
        if not self.process:
            return
        logger.info("Stopping external process %s", self.command)
        pgid = os.getpgid(self.process.pid)
        os.killpg(pgid, signal.SIGTERM)
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            logger.warning("Process didn't terminate after SIGTERM, issuing SIGKILL")
            os.kiipg(pgid, signal.SIGKILL)
            self.process.wait()

        if self.port_check:
            self._wait_until_port_free(timeout=5)

    def _wait_until_port_free(self, timeout):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self._is_port_in_use:
                return
            time.sleep(0.2)
        logger.warning("Port still busy after waiting, probably due to TIME_WAIT")

    def _is_port_in_use(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", self.port_check)) == 0
        
