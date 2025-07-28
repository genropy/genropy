import os

import Pyro4.core

from gnr.xtnd import logger
from gnr.xtnd.sync4Dapp import GnrAppSync4D

class Sync4DCommander(Pyro4.core.DaemonObject):
    def __init__(self, daemon, instancefolder):
        super().__init__(self)

        self.app = GnrAppSync4D(instancefolder)
        self.daemon = daemon
        self.instancefolder = instancefolder
        self.instancename = os.path.basename(instancefolder)

    def loopCondition(self):
        logger.debug("loop")
        self.app.do()
        return True

    def run(self):
        self.app.beforeLoop()

        self.ns = Pyro4.locateNS()
        self.daemon.useNameServer(self.ns)
        uri = self.daemon.connect(self, "sync4d_%s" % self.instancename)

        logger.info("The daemon runs on port: %s", self.daemon.port)
        logger.info("The object's uri is: %s", uri)

        self.daemon.requestLoop(timeout=self.app.sync4d_timing, condition=self.loopCondition)

    def stop(self):
        self.daemon.shutdown(True)
    
