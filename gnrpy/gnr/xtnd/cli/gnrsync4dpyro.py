#!/usr/bin/env python
# encoding: utf-8

import os
From Pyro5.server import Daemon
from gnr.xtnd.sync4Dpyro import Sync4DCommander

description = "Run Sync4DCommander daemon"

def main():
    daemon = Daemon()
    synccomm = Sync4DCommander(daemon, os.getcwd())
    synccomm.run()

if __name__ == "__main__":
    main()
