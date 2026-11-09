"""Serve the browser transport contract tests against real HTTP endpoints.

Run from the repository root: python gnrjs/tests/dojo_xhr_server.py
Open http://127.0.0.1:8765/gnrjs/tests/dojo_xhr.html
"""

import json
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parents[2]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        parsed = urlsplit(self.path)
        if not parsed.path.startswith('/transport-test/'):
            if parsed.path.startswith(('/gnrjs/', '/dojo_libs/')):
                return super().do_GET()
            self.send_error(404)
            return
        started = time.perf_counter()
        query = parse_qs(parsed.query)
        delay = min(float(query.get('delay', ['0'])[0]), 2)
        time.sleep(delay)
        body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        status = int(query.get('status', ['200'])[0])
        content_type = 'application/json'
        result = json.dumps(dict(
            method=self.command, query=query, body=body.decode(),
            headers=dict(self.headers))).encode()
        if parsed.path.endswith(('/xml', '/xml-no-content-type',
                                 '/xml-invalid', '/xml-text')):
            content_type = 'application/xml'
            result = b'<GenRoBag><result answer="yes">hello</result></GenRoBag>'
            if parsed.path.endswith('/xml-no-content-type'):
                content_type = None
            elif parsed.path.endswith('/xml-invalid'):
                result = b'<GenRoBag><result></GenRoBag>'
            elif parsed.path.endswith('/xml-text'):
                content_type = 'text/plain'
        elif parsed.path.endswith('/invalid-json'):
            result = b'{broken'
        elif parsed.path.endswith('/close'):
            self.close_connection = True
            self.connection.close()
            return
        self.send_response(status)
        if content_type:
            self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(result)))
        self.send_header('X-GnrTime', str(time.perf_counter() - started))
        self.end_headers()
        if parsed.path.endswith('/slow-body'):
            self.wfile.flush()
            time.sleep(0.12)
        try:
            self.wfile.write(result)
        except (BrokenPipeError, ConnectionResetError):
            pass

    do_POST = do_GET
    do_PUT = do_GET
    do_DELETE = do_GET
    do_PATCH = do_GET

    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    print('Open http://127.0.0.1:8765/gnrjs/tests/dojo_xhr.html', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8765), Handler).serve_forever()
