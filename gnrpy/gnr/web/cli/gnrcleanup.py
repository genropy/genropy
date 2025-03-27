#!/usr/bin/env python
# encoding: utf-8

import os

from gnr.core.cli import GnrCliArgParse
from gnr.web.gnrwsgisite import GnrWsgiSite

description = "run data cleanup for site"

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('site_name')

    options = parser.parse_args()
    site = GnrWsgiSite(options.site_name)
    site.connFolderRemove()

if __name__ == "__main__":
    main()

