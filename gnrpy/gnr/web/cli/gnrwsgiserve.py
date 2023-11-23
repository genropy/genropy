#!/usr/bin/env python
# encoding: utf-8

from gnr.web.server import NewServer

def main():
    server = NewServer()
    server.run()

if __name__ == '__main__':
    main()
