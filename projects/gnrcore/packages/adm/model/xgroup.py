# encoding: utf-8

from gnr.core.gnrdecorator import metadata


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('xgroup', pkey='code', name_long='!!Deployment group',
                        name_plural='!!Deployment groups',
                        caption_field='description', lookup=True)
        self.sysFields(tbl, id=False)
        tbl.column('code', size=':10', name_long='!!Code')
        tbl.column('description', name_long='!!Description')

    @metadata(mandatory=True)
    def sysRecord_ALPHA(self):
        return self.newrecord(code='ALPHA', description='Alpha')

    @metadata(mandatory=True)
    def sysRecord_CANARY(self):
        return self.newrecord(code='CANARY', description='Canary')

    @metadata(mandatory=True)
    def sysRecord_BETA(self):
        return self.newrecord(code='BETA', description='Beta')

    @metadata(mandatory=True)
    def sysRecord_STANDARD(self):
        return self.newrecord(code='STANDARD', description='Standard')

    @metadata(mandatory=True)
    def sysRecord_LTS(self):
        return self.newrecord(code='LTS', description='LTS')
