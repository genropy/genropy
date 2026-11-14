# encoding: utf-8
"""The numbers of a counter series kept as blocks (xmldocs/proposal/counter-blocks).

The numbers of a series are a contiguous sequence of blocks, without overlaps,
from the first number to the last one assigned. A block is occupied
(consecutive numbers in use) or free (consecutive numbers released). Every
block carries its first and last number and the ``order_field`` value of its
first and last number; for a free block, those of the occupied numbers that
delimit it.

The series itself is the ``adm.counter`` record (``codekey``): its row is the
lock of every operation and its ``counter`` column follows the last number.
"""

from contextlib import nullcontext
from datetime import date, datetime

from gnr.core.gnrdecorator import public_method

BASE = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'


class NumberBlocks(object):
    """The blocks of one series, sorted by number.

    Each block is a dict: ``id`` (None for a block not yet stored), ``start``,
    ``end``, ``occupied``, ``first``, ``last`` (order values). Every operation
    leaves the sequence normalized: adjacent blocks of the same kind merged,
    no free block at the end, free blocks carrying the values of their
    occupied neighbours."""

    def __init__(self, blocks=None):
        self.blocks = sorted(blocks or [], key=lambda b: b['start'])

    @property
    def last_number(self):
        return self.blocks[-1]['end'] if self.blocks else None

    def index_of(self, number):
        for i, block in enumerate(self.blocks):
            if block['start'] <= number <= block['end']:
                return i
        return None

    def is_occupied(self, number):
        i = self.index_of(number)
        return i is not None and self.blocks[i]['occupied']

    def window(self, number):
        """(lower, upper) order values allowed for number: the values of the
        occupied numbers around it; None is an open bound"""
        i = self.index_of(number)
        if i is not None:
            block = self.blocks[i]
            if block['occupied']:
                return None
            return block['first'], block['last']
        if self.blocks and number > self.last_number:
            return self.blocks[-1]['last'], None
        if self.blocks and number < self.blocks[0]['start']:
            return None, self.blocks[0]['first']
        return None, None

    def recyclable(self, value):
        "The lowest free number whose window holds value, or None"
        for block in self.blocks:
            if block['occupied']:
                continue
            if _fits(value, block['first'], block['last']):
                return block['start']
        return None

    def occupy(self, number, value):
        "number, free or outside the blocks, becomes occupied with order value"
        new_block = dict(id=None, start=number, end=number, occupied=True, first=value, last=value)
        if not self.blocks or number > self.last_number:
            if self.blocks and number > self.last_number + 1:
                self.blocks.append(dict(id=None, start=self.last_number + 1, end=number - 1, occupied=False,
                                        first=None, last=None))
            self.blocks.append(new_block)
        elif number < self.blocks[0]['start']:
            head = [new_block]
            if number + 1 < self.blocks[0]['start']:
                head.append(dict(id=None, start=number + 1, end=self.blocks[0]['start'] - 1, occupied=False,
                                 first=None, last=None))
            self.blocks[0:0] = head
        else:
            i = self.index_of(number)
            block = self.blocks[i]
            if block['occupied']:
                raise ValueError('number %s is occupied' % number)
            parts = []
            if number > block['start']:
                parts.append(dict(block, end=number - 1))
            parts.append(new_block)
            if number < block['end']:
                parts.append(dict(id=None, start=number + 1, end=block['end'], occupied=False,
                                  first=None, last=None))
            self.blocks[i:i + 1] = parts
        self.normalize()

    def release(self, number, value_of=None):
        """number, occupied, becomes free. value_of(n) gives the order value of an
        occupied number n; it is called only for a new edge of a block split"""
        i = self.index_of(number)
        if i is None or not self.blocks[i]['occupied']:
            raise ValueError('number %s is not occupied' % number)
        block = self.blocks[i]
        parts = []
        if number > block['start']:
            below = number - 1
            last = block['first'] if below == block['start'] else (value_of(below) if value_of else None)
            parts.append(dict(block, end=below, last=last))
        parts.append(dict(id=None, start=number, end=number, occupied=False, first=None, last=None))
        if number < block['end']:
            above = number + 1
            first = block['last'] if above == block['end'] else (value_of(above) if value_of else None)
            parts.append(dict(id=None, start=above, end=block['end'], occupied=True, first=first,
                              last=block['last']))
        self.blocks[i:i + 1] = parts
        self.normalize()

    def normalize(self):
        merged = []
        for block in self.blocks:
            if block['start'] > block['end']:
                continue
            if merged and merged[-1]['occupied'] == block['occupied'] and merged[-1]['end'] + 1 == block['start']:
                previous = merged[-1]
                previous['end'] = block['end']
                if block['occupied']:
                    previous['last'] = block['last']
                continue
            merged.append(dict(block))
        while merged and not merged[-1]['occupied']:
            merged.pop()
        for i, block in enumerate(merged):
            if block['occupied']:
                continue
            block['first'] = merged[i - 1]['last'] if i > 0 else None
            block['last'] = merged[i + 1]['first'] if i + 1 < len(merged) else None
        self.blocks = merged


def _shape(blocks):
    return [(b['start'], b['end'], b['occupied'], b['first'], b['last']) for b in blocks.blocks]


def _fits(value, lower, upper):
    if value is None:
        return lower is None and upper is None
    return (lower is None or lower <= value) and (upper is None or value <= upper)


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('counters_n', pkey='id', name_long='!![en]Counter block',
                        name_plural='!![en]Counter blocks', multi_tenant=True)
        self.sysFields(tbl, ldel=False)
        tbl.column('counter_codekey', size=':80', name_long='!![en]Counter', indexed=True).relation(
            'adm.counter.codekey', relation_name='blocks', mode='foreignkey', onDelete='cascade')
        tbl.column('block_start', 'L', name_long='!![en]First number')
        tbl.column('block_end', 'L', name_long='!![en]Last number')
        tbl.column('occupied', 'B', name_long='!![en]Occupied')
        tbl.column('order_first', name_long='!![en]Order value of the first number')
        tbl.column('order_last', name_long='!![en]Order value of the last number')

    def use_dbstores(self, forced_dbstore=None, env_forced_dbstore=None, **kwargs):
        return True

    # ------------------------------------------------------------------
    # switch
    # ------------------------------------------------------------------

    def isEnabledFor(self, tblobj, field):
        """True when the counter tblobj.field uses this table: the experimental
        switch new_counters/counters is '*' or lists 'pkg.table.field'"""
        application = self.db.application
        listed = application.experimentalValue('new_counters', 'counters') if application else None
        if not listed:
            return False
        if listed == '*':
            return True
        return '%s.%s' % (tblobj.fullname, field) in [k.strip() for k in listed.split(',')]

    # ------------------------------------------------------------------
    # counter parameters and values
    # ------------------------------------------------------------------

    def adm_counter(self):
        return self.db.table('adm.counter')

    def counterPars(self, tblobj, field, record):
        counter_pars = tblobj.getCounterPars(field, record)
        if counter_pars and counter_pars.get('recycle') and not counter_pars.get('order_field'):
            raise self.exception('business_logic',
                                 msg='Counter %s.%s: recycle requires order_field' % (tblobj.fullname, field))
        return counter_pars

    def orderValue(self, tblobj, counter_pars, record):
        "The order_field value of record, as compared: a date for D, the timestamp otherwise"
        order_field = counter_pars.get('order_field')
        if not order_field:
            return None
        value = record[order_field]
        if value is None:
            raise self.exception('business_logic', msg=self.adm_counter()._translate(
                '!!Missing %s. Mandatory for counter %s') % (order_field, tblobj.fullname))
        if tblobj.column(order_field).dtype == 'D' and isinstance(value, datetime):
            value = value.date()
        return value

    def _storedValue(self, value):
        return value.isoformat() if value is not None else None

    def _loadedValue(self, text, dtype):
        if not text:
            return None
        if dtype == 'D':
            return date.fromisoformat(text)
        return datetime.fromisoformat(text)

    def sequenceNumber(self, counter_pars, sequence):
        """The number of a formatted sequence, or None when the text does not hold one"""
        N_start, N_end = self.adm_counter()._getBoundaries(**counter_pars)['N']
        if N_start is None or not sequence:
            return None
        digits = sequence[N_start:N_end]
        base = counter_pars.get('base')
        if base:
            base = BASE[0:base] if isinstance(base, int) else base
            if not digits or any(c not in base for c in digits):
                return None
            number = 0
            for c in digits:
                number = number * len(base) + base.index(c)
            return number
        return int(digits) if digits.isdigit() else None

    def formatSequence(self, tblobj, field, record, number):
        return self.adm_counter().formatSequence(tblobj=tblobj, field=field, record=record, counter=number)

    # ------------------------------------------------------------------
    # blocks of a series
    # ------------------------------------------------------------------

    def loadBlocks(self, codekey, dtype=None):
        rows = self.query(columns='$id,$block_start,$block_end,$occupied,$order_first,$order_last',
                          where='$counter_codekey=:codekey', codekey=codekey,
                          order_by='$block_start', addPkeyColumn=False).fetch()
        return NumberBlocks([dict(id=r['id'], start=r['block_start'], end=r['block_end'],
                                  occupied=bool(r['occupied']),
                                  first=self._loadedValue(r['order_first'], dtype),
                                  last=self._loadedValue(r['order_last'], dtype)) for r in rows])

    def storeBlocks(self, codekey, blocks, stored):
        """Write blocks against stored ({id: shape} as loaded): update the changed
        ones, insert the new ones, delete the ones gone"""
        kept = set()
        for block in blocks.blocks:
            shape = (block['start'], block['end'], block['occupied'], block['first'], block['last'])
            values = dict(counter_codekey=codekey, block_start=block['start'], block_end=block['end'],
                          occupied=block['occupied'], order_first=self._storedValue(block['first']),
                          order_last=self._storedValue(block['last']))
            if block['id'] in stored:
                kept.add(block['id'])
                if stored[block['id']] != shape:
                    with self.recordToUpdate(block['id']) as record:
                        record.update(values)
            else:
                self.insert(values)
                block['id'] = values['id']
        for pkey in set(stored) - kept:
            self.delete(pkey)

    def _series(self, tblobj, field, record, counter_pars):
        """(codekey, order dtype) of the series of record; its adm.counter record is created when missing"""
        counter_tbl = self.adm_counter()
        codekey = counter_tbl.getCounterPkey(tblobj=tblobj, field=field, record=record)
        if not counter_tbl.existsRecord(codekey):
            counter_record = counter_tbl.newCounterRecord(tblobj=tblobj, field=field, record=record)
            counter_record['counter'] = counter_pars.get('starting_value') or 0
            counter_tbl.insert(counter_record)
        order_field = counter_pars.get('order_field')
        dtype = tblobj.column(order_field).dtype if order_field else None
        return codekey, dtype

    def _withSeries(self, tblobj, field, record, counter_pars, handler):
        """Run handler(blocks) under the lock of the series, then store the blocks"""
        codekey, dtype = self._series(tblobj, field, record, counter_pars)
        with self.adm_counter().recordToUpdate(codekey, mode='record') as counter_record:
            blocks = self.loadBlocks(codekey, dtype)
            stored = dict(zip([b['id'] for b in blocks.blocks], _shape(blocks)))
            result = handler(blocks)
            self.storeBlocks(codekey, blocks, stored)
            counter_record['counter'] = blocks.last_number or (counter_pars.get('starting_value') or 0)
        return result

    def _rootstore(self, counter_pars):
        return self.db.tempEnv(storename=self.db.rootstore) if counter_pars.get('rootstore') else nullcontext()

    # ------------------------------------------------------------------
    # the counter API, as adm.counter
    # ------------------------------------------------------------------

    def assignCounter(self, tblobj=None, field=None, record=None, old_record=None):
        """Assign, claim or change the number of record.

        - a number set in the record (insert, or changed on update) is claimed:
          it must be free or beyond the blocks, and inside its window;
        - a number changed or cleared on update releases the old one, for a
          recycling counter;
        - a record without number gets the lowest recyclable number, or the
          next one."""
        counter_pars = self.counterPars(tblobj, field, record)
        if not counter_pars:
            return
        value = record.get(field)
        old_value = old_record.get(field) if old_record else None
        with self._rootstore(counter_pars):
            if old_value and old_value != value and counter_pars.get('recycle'):
                # the old number belongs to the series of the stored record
                held = dict(old_record)
                self.releaseCounter(tblobj=tblobj, field=field, record=held)
            if value:
                if old_record is None or value != old_value:
                    self.claimSequence(tblobj, field, record, counter_pars)
                return
            if tblobj.isDraft(record) and not counter_pars.get('assignIfDraft'):
                return
            record[field] = self._assignNew(tblobj, field, record, counter_pars)
        if counter_pars.get('onAssigned'):
            counter_pars['onAssigned'](record=record, field=field)

    def _assignNew(self, tblobj, field, record, counter_pars):
        order_value = self.orderValue(tblobj, counter_pars, record)

        def handler(blocks):
            number = blocks.recyclable(order_value) if counter_pars.get('recycle') else None
            if number is None:
                number = (blocks.last_number or (counter_pars.get('starting_value') or 0)) + 1
                self._checkWindow(tblobj, field, counter_pars, blocks, number, order_value)
            blocks.occupy(number, order_value)
            return number

        number = self._withSeries(tblobj, field, record, counter_pars, handler)
        return self.formatSequence(tblobj, field, record, number)

    def claimSequence(self, tblobj, field, record, counter_pars):
        """A number of the series set by hand becomes occupied; a value that is
        not a number of this series is left alone"""
        sequence = record[field]
        number = self.sequenceNumber(counter_pars, sequence)
        if number is None or self.formatSequence(tblobj, field, record, number) != sequence:
            return
        order_value = self.orderValue(tblobj, counter_pars, record)

        def handler(blocks):
            if blocks.is_occupied(number):
                raise self.exception('business_logic', msg=self.adm_counter()._translate(
                    '!![en]%(sequence)s is already in use') % dict(sequence=sequence))
            self._checkWindow(tblobj, field, counter_pars, blocks, number, order_value)
            blocks.occupy(number, order_value)

        self._withSeries(tblobj, field, record, counter_pars, handler)

    def _checkWindow(self, tblobj, field, counter_pars, blocks, number, order_value):
        if not counter_pars.get('order_field'):
            return
        lower, upper = blocks.window(number)
        if _fits(order_value, lower, upper):
            return
        msgTpl = counter_pars.get('message_dateError', '!!Incompatible date assigning %(fieldname)s counter')
        fieldname = self.adm_counter()._translate(tblobj.column(field).name_long or field)
        raise self.exception('business_logic', msg=self.adm_counter()._translate(msgTpl) % dict(
            fieldname=fieldname, last_used=lower))

    def releaseCounter(self, tblobj=None, field=None, record=None):
        """The number of record becomes free; record[field] is cleared"""
        counter_pars = self.counterPars(tblobj, field, record)
        sequence = record.get(field)
        number = self.sequenceNumber(counter_pars, sequence) if counter_pars else None
        if number is None:
            return
        codekey = self.adm_counter().getCounterPkey(tblobj=tblobj, field=field, record=record)
        if not self.adm_counter().existsRecord(codekey):
            return
        order_field = counter_pars.get('order_field')

        def value_of(n):
            if not order_field:
                return None
            rows = tblobj.query(columns='$%s' % order_field, where='$%s=:sequence' % field,
                                sequence=self.formatSequence(tblobj, field, record, n),
                                excludeDraft=False, excludeLogicalDeleted=False, subtable='*',
                                addPkeyColumn=False).fetch()
            if not rows:
                raise self.exception('business_logic', msg='Counter %s.%s: number %s is in the blocks but not in the table'
                                     % (tblobj.fullname, field, n))
            return self.orderValue(tblobj, counter_pars, rows[0])

        def handler(blocks):
            if blocks.is_occupied(number):
                blocks.release(number, value_of=value_of)

        with self._rootstore(counter_pars):
            self._withSeries(tblobj, field, record, counter_pars, handler)
        record[field] = None
        if counter_pars.get('onReleased'):
            counter_pars['onReleased'](record=record, field=field)

    def guessNextSequence(self, tblobj=None, field=None, record=None):
        """(sequence, info) of the number assignCounter would give record now,
        without writing; info['recycled'] is True for a recycled number"""
        counter_pars = self.counterPars(tblobj, field, record)
        with self._rootstore(counter_pars):
            codekey = self.adm_counter().getCounterPkey(tblobj=tblobj, field=field, record=record)
            order_field = counter_pars.get('order_field')
            dtype = tblobj.column(order_field).dtype if order_field else None
            blocks = self.loadBlocks(codekey, dtype)
            number = None
            if counter_pars.get('recycle'):
                number = blocks.recyclable(self.orderValue(tblobj, counter_pars, record))
            info = dict(recycled=number is not None)
            if number is None:
                number = (blocks.last_number or (counter_pars.get('starting_value') or 0)) + 1
        return self.formatSequence(tblobj, field, record, number), info

    @public_method
    def freeSequences(self, table=None, field=None, record=None, limit=500):
        """The free numbers of the series of record, lowest first, each with its
        window: a list of dict(sequence, number, order_from, order_to)"""
        tblobj = self.db.table(table)
        counter_pars = self.counterPars(tblobj, field, record)
        codekey = self.adm_counter().getCounterPkey(tblobj=tblobj, field=field, record=record)
        order_field = counter_pars.get('order_field')
        blocks = self.loadBlocks(codekey, tblobj.column(order_field).dtype if order_field else None)
        result = []
        for block in blocks.blocks:
            if block['occupied']:
                continue
            for number in range(block['start'], block['end'] + 1):
                if len(result) >= limit:
                    return result
                result.append(dict(number=number, sequence=self.formatSequence(tblobj, field, record, number),
                                   order_from=block['first'], order_to=block['last']))
        return result

    # ------------------------------------------------------------------
    # analysis, load and check of the series of a counter
    # ------------------------------------------------------------------

    def collectSeries(self, tblobj, field):
        """The numbers in use of every series of tblobj.field, read from the table:
        {codekey: dict(numbers=[(number, order value, pkey)], errors=[...], record=a record of the series)}"""
        result = {}
        rows = tblobj.query(columns='*', where='$%s IS NOT NULL' % field, excludeDraft=False,
                            excludeLogicalDeleted=False, subtable='*', bagFields=False).fetch()
        for row in rows:
            record = dict(row)
            counter_pars = tblobj.getCounterPars(field, record)
            if not counter_pars:
                continue
            codekey = self.adm_counter().getCounterPkey(tblobj=tblobj, field=field, record=record)
            series = result.setdefault(codekey, dict(numbers=[], errors=[], record=record,
                                                     counter_pars=counter_pars))
            sequence = record[field]
            number = self.sequenceNumber(counter_pars, sequence)
            if number is None or self.formatSequence(tblobj, field, record, number) != sequence:
                series['errors'].append(dict(kind='not_a_number', sequence=sequence, pkey=record[tblobj.pkey]))
                continue
            order_field = counter_pars.get('order_field')
            if order_field and record.get(order_field) is None:
                series['errors'].append(dict(kind='missing_order_value', sequence=sequence,
                                             pkey=record[tblobj.pkey]))
                continue
            order_value = self.orderValue(tblobj, counter_pars, record) if order_field else None
            series['numbers'].append((number, order_value, record[tblobj.pkey]))
        for series in result.values():
            series['numbers'].sort(key=lambda n: n[0])
            previous = None
            for number, order_value, pkey in series['numbers']:
                if previous and previous[0] == number:
                    series['errors'].append(dict(kind='duplicate', number=number, pkey=pkey))
                elif previous and order_value is not None and previous[1] is not None and order_value < previous[1]:
                    series['errors'].append(dict(kind='wrong_order', number=number, pkey=pkey))
                previous = (number, order_value)
        return result

    def expectedBlocks(self, numbers, starting_value=0):
        """The blocks of a series from its numbers in use, sorted: (number, order value, pkey)"""
        blocks = NumberBlocks()
        if numbers and numbers[0][0] > starting_value + 1:
            blocks.blocks.append(dict(id=None, start=starting_value + 1, end=numbers[0][0] - 1,
                                      occupied=False, first=None, last=None))
        for number, order_value, pkey in numbers:
            if blocks.blocks and blocks.blocks[-1]['occupied'] and blocks.blocks[-1]['end'] + 1 == number:
                blocks.blocks[-1]['end'] = number
                blocks.blocks[-1]['last'] = order_value
                continue
            if blocks.blocks and blocks.blocks[-1]['end'] + 1 < number:
                blocks.blocks.append(dict(id=None, start=blocks.blocks[-1]['end'] + 1, end=number - 1,
                                          occupied=False, first=None, last=None))
            blocks.blocks.append(dict(id=None, start=number, end=number, occupied=True,
                                      first=order_value, last=order_value))
        blocks.normalize()
        return blocks

    @public_method
    def analyzeCounter(self, table=None, field=None):
        """Read-only report of every series of table.field: number count and errors
        (not_a_number, missing_order_value, duplicate, wrong_order)"""
        tblobj = self.db.table(table)
        return {codekey: dict(count=len(series['numbers']), errors=series['errors'])
                for codekey, series in self.collectSeries(tblobj, field).items()}

    @public_method
    def loadCounter(self, table=None, field=None):
        """Build the blocks of every clean series of table.field from the table; a
        series with errors is skipped. Returns {codekey: 'loaded' | errors}"""
        tblobj = self.db.table(table)
        report = {}
        for codekey, series in self.collectSeries(tblobj, field).items():
            if series['errors']:
                report[codekey] = series['errors']
                continue
            counter_pars = series['counter_pars']
            self._series(tblobj, field, series['record'], counter_pars)
            starting_value = counter_pars.get('starting_value') or 0
            with self.adm_counter().recordToUpdate(codekey, mode='record') as counter_record:
                stored = {r['id']: None for r in self.query(columns='$id', where='$counter_codekey=:c',
                                                            c=codekey, addPkeyColumn=False).fetch()}
                blocks = self.expectedBlocks(series['numbers'], starting_value)
                self.storeBlocks(codekey, blocks, stored)
                counter_record['counter'] = blocks.last_number or starting_value
            report[codekey] = 'loaded'
        return report

    @public_method
    def checkCounter(self, table=None, field=None):
        """Read-only comparison of the stored blocks with the table: {codekey: problems}
        for every series whose blocks differ from the numbers in use"""
        tblobj = self.db.table(table)
        report = {}
        for codekey, series in self.collectSeries(tblobj, field).items():
            if series['errors']:
                report[codekey] = series['errors']
                continue
            counter_pars = series['counter_pars']
            order_field = counter_pars.get('order_field')
            dtype = tblobj.column(order_field).dtype if order_field else None
            expected = self.expectedBlocks(series['numbers'], counter_pars.get('starting_value') or 0)
            stored = self.loadBlocks(codekey, dtype)
            if _shape(expected) != _shape(stored):
                report[codekey] = [dict(kind='blocks_differ', expected=_shape(expected), stored=_shape(stored))]
        return report

