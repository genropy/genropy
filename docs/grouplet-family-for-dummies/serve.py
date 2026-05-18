#!/usr/bin/env python3
"""Serve the Grouplet Family — For Dummies documentation locally.

The doc uses fetch() to load tab fragments from tabs/*.html, so opening
index.html via file:// is blocked by the browser's CORS policy. This
script starts a small http.server in the doc directory, opens the
browser, and waits for Ctrl-C.

Usage:
    python serve.py              # auto port + open browser
    python serve.py --port 8080  # explicit port
    python serve.py --no-browser # don't auto-open
"""
import argparse
import http.server
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path


def find_free_port(start=8000, stop=9000):
    """Return the first free TCP port in [start, stop)."""
    for port in range(start, stop):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    raise RuntimeError(f'No free port in [{start}, {stop})')


def main():
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--port', type=int, default=None,
                        help='port to bind (default: auto-detect from 8000)')
    parser.add_argument('--no-browser', action='store_true',
                        help="don't open browser automatically")
    parser.add_argument('--host', default='127.0.0.1',
                        help='host to bind (default: 127.0.0.1)')
    args = parser.parse_args()

    # Always serve from the directory this script lives in,
    # regardless of where the user invoked it from.
    here = Path(__file__).resolve().parent
    os.chdir(here)

    port = args.port if args.port else find_free_port()
    url = f'http://{args.host}:{port}/'

    handler = http.server.SimpleHTTPRequestHandler
    with http.server.ThreadingHTTPServer((args.host, port), handler) as server:
        print(f'Serving {here} at {url}')
        print('Press Ctrl-C to stop.')

        if not args.no_browser:
            # Open the browser after the server is actually listening.
            threading.Timer(0.3, lambda: webbrowser.open(url)).start()

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('\nStopped.')
            sys.exit(0)


if __name__ == '__main__':
    main()
