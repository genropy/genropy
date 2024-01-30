#!/usr/bin/env python
# encoding: utf-8

from gnr.web.server import NewServer

description = """Start application server for site"""
def main():
    server = NewServer()
    server.run()

if __name__ == '__main__':
    main()
