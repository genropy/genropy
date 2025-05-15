#!/usr/bin/env python
# encoding: utf-8
from gnr.app.gnrdeploy import EntityNotFoundException
from gnr.web.server import NewServer

description = """Start application server for site"""

def main():
    try:
        server = NewServer()
        server.run()
    except EntityNotFoundException as e:
        print(e)
        
if __name__ == '__main__':
    main()
