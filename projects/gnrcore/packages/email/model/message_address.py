# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl =  pkg.table('message_address',pkey='id',name_long='!!Message address',
                      name_plural='!!Message addresses', retention_policy=('__ins_ts', 1))
        self.sysFields(tbl)
        tbl.column('message_id',size='22',name_long='!!Message id').relation('email.message.id', mode='foreignkey',
                                                                            relation_name='addresses',onDelete='cascade',deferred=True)
        tbl.column('address',name_long='!!Address',indexed=True)
        tbl.column('reason',name_long='!!Reason')

    def retention_extra_where(self):
        """
        Cleanup message_address records based on email preferences.
        - If collect_addresses is False: delete all records older than 1 day
        - If exclude_from_address is True: delete only 'from' records older than 1 day
        - Otherwise: keep everything (no cleanup)
        """
        prefs = self.db.application.getPreference('', pkg='email') or {}

        # If address collection is disabled, remove all records
        if not prefs.get('collect_addresses'):
            return "$id IS NOT NULL"  # Always true - delete everything (older than 1 day)

        # If from addresses should be excluded, remove them
        if prefs.get('exclude_from_address'):
            return "$reason = 'from'"

        # Otherwise, keep everything
        return "$id IS NULL"  # Always false - delete nothing (id is never NULL)