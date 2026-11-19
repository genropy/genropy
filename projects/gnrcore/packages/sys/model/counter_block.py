# encoding: utf-8
"""The blocks of the numbers of a sys.counter, one row per block and period.

A block is a run of consecutive numbers, occupied (in use) or free (released).
order_first and order_last are the order_field values of its first and last
number, encoded as integers (sys.counter.orderKey); for a free block, those of
the occupied numbers that delimit it.
"""


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('counter_block', pkey='id', name_long='!![en]Counter block',
                        name_plural='!![en]Counter blocks', multi_tenant=True)
        self.sysFields(tbl, ldel=False)
        tbl.column('counter_codekey', size=':80', name_long='!![en]Counter', indexed=True).relation(
            'sys.counter.codekey', relation_name='blocks', mode='foreignkey', onDelete='cascade')
        tbl.column('period', size=':10', name_long='!![en]Period', indexed=True)
        tbl.column('block_start', 'L', name_long='!![en]First number')
        tbl.column('block_end', 'L', name_long='!![en]Last number')
        tbl.column('occupied', 'B', name_long='!![en]Occupied')
        tbl.column('order_first', 'L', name_long='!![en]Order value of the first number')
        tbl.column('order_last', 'L', name_long='!![en]Order value of the last number')

    def use_dbstores(self, forced_dbstore=None, env_forced_dbstore=None, **kwargs):
        return True
