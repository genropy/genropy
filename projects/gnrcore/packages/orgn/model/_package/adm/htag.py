# encoding: utf-8
from gnr.core.gnrdecorator import metadata

class Table(object):
  
    @metadata(mandatory=True)
    def sysRecord_ORGN_AGENT(self):
        return self.newrecord(code='ORGN_AGENT',description='Organizer')