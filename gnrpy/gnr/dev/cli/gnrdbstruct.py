#!/usr/bin/env python
# encoding: utf-8
import sys
import argparse

import urllib.request, urllib.parse, urllib.error

usage = "gnrdbstruct <port> [path]"

def main():
    parser = argparse.ArgumentParser(usage)
    parser.add_argument('port',nargs=1)
    parser.add_argument('path',nargs='?')
    options = parser.parse_args()
    port = options.port[0]
    path = options.path
    if path:
        path = path.replace('.', '/')
    try:
        urlobj = urllib.request.urlopen(f'http://127.0.0.1:{port}/_tools/dbstructure/{path}')
        print(urlobj.read())
    except urllib.error.URLError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
    
