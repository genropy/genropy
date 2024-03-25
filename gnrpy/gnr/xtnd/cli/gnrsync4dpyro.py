#!/usr/bin/env python
# encoding: utf-8

import os
import Pyro4.core
from gnr.xtnd.sync4Dpyro import Sync4DCommander

description = "Run Sync4DCommander daemon"

def main():
    daemon = Pyro4.core.Daemon()
    
    synccomm = Sync4DCommander(daemon, os.getcwd())
    synccomm.run()

if __name__ == "__main__":
    main()
