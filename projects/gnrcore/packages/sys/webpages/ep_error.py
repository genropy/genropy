# -*- coding: utf-8 -*-


class GnrCustomWebPage(object):
    auth_tags = '_DEV_,admin'
    skip_connection = False

    def windowTitle(self):
        return 'Error Detail'

    def main(self, root, error_code=None, error_id=None, **kwargs):
        if not error_code and not error_id:
            root.div('No error_code or error_id provided.')
            return
        pkey = error_id
        if error_code and not error_id:
            rec = self.db.table('sys.error').record(
                where='$error_code = :ec', ec=error_code,
                ignoreMissing=True).output('bag')
            if not rec:
                root.div('Error not found: %s' % error_code)
                return
            pkey = rec['id']
        root.dataRecord('main.record', 'sys.error', pkey=pkey, _onStart=True)
        root.contentPane(overflow='hidden').tracebackViewer(
            value='^main.record.error_data',
            title='^main.record.description',
            height='100%')
