# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('xgroup', pkey='code', name_long='!!Deployment group',
                        name_plural='!!Deployment groups',
                        caption_field='description', lookup=True)
        self.sysFields(tbl, id=False)
        tbl.column('code', size=':10', name_long='!!Code')
        tbl.column('description', name_long='!!Description')

    # Base deployment groups, aligned with the sticky-proxy worker groups
    # (standard/beta/canary). These are modifiable defaults, not constraints:
    # an instance may add, rename or remove them. Codes are upper-case here;
    # the proxy lower-cases them to match the worker group names. STANDARD is
    # the default/fallback channel for users without an explicit group.
    def sysRecord_STANDARD(self):
        return self.newrecord(code='STANDARD', description='Standard')

    def sysRecord_BETA(self):
        return self.newrecord(code='BETA', description='Beta')

    def sysRecord_CANARY(self):
        return self.newrecord(code='CANARY', description='Canary')
