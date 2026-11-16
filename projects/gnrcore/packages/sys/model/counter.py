# encoding: utf-8
"""Counters of the sys package: the numbers of a series kept as blocks.

A table numbers a field through ``counter_<field>(record)`` as with
adm.counter. When the experimental switch ``new_counters/counters`` enables
the counter, gnrdbo sends it here instead of adm.counter.

- sys.counter: one row per counter (pkg, tbl, fld, code); its row is the
  lock of every operation on the counter.
- sys.counter_block: the blocks of each period of the counter, occupied or
  free, with the order_field value of their first and last number.

order_field sets the order the numbers follow: dates for a D column, the
timestamp for DH/DHZ. Without it the order is the date_field, as with
adm.counter, unless the counter is date_tolerant: then no order is checked.
recycle requires an order.
"""

import calendar
import re
from datetime import datetime, timezone

from gnr.core.gnrdecorator import public_method

BASE = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
LIKE_ESCAPE = '!'


class NumberBlocks(object):
    """The blocks of one period, sorted by number.

    Each block is a dict: ``id`` (None for a block not yet stored), ``start``,
    ``end``, ``occupied``, ``first``, ``last`` (order keys). Every operation
    leaves the sequence normalized: adjacent blocks of the same kind merged,
    no free block at the end, free blocks carrying the keys of their
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
        """(lower, upper) order keys allowed for a free number or one outside the
        blocks: the keys of the occupied numbers around it; None is an open bound"""
        i = self.index_of(number)
        if i is not None:
            return self.blocks[i]['first'], self.blocks[i]['last']
        if self.blocks and number > self.last_number:
            return self.blocks[-1]['last'], None
        if self.blocks and number < self.blocks[0]['start']:
            return None, self.blocks[0]['first']
        return None, None

    def recyclable(self, key):
        "The lowest free number whose window holds key, or None"
        for block in self.blocks:
            if not block['occupied'] and fits(key, block['first'], block['last']):
                return block['start']
        return None

    def occupy(self, number, key):
        "number, free or outside the blocks, becomes occupied with order key"
        new_block = dict(id=None, start=number, end=number, occupied=True, first=key, last=key)
        if not self.blocks or number > self.last_number:
            if self.blocks and number > self.last_number + 1:
                self.blocks.append(_free(self.last_number + 1, number - 1))
            self.blocks.append(new_block)
        elif number < self.blocks[0]['start']:
            head = [new_block]
            if number + 1 < self.blocks[0]['start']:
                head.append(_free(number + 1, self.blocks[0]['start'] - 1))
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
                parts.append(_free(number + 1, block['end']))
            self.blocks[i:i + 1] = parts
        self.normalize()

    def occupy_range(self, start, end, key):
        "start..end, beyond the blocks, become occupied with order key"
        if self.blocks and start <= self.last_number:
            raise ValueError('numbers %s-%s are not beyond the blocks' % (start, end))
        if self.blocks and start > self.last_number + 1:
            self.blocks.append(_free(self.last_number + 1, start - 1))
        self.blocks.append(dict(id=None, start=start, end=end, occupied=True, first=key, last=key))
        self.normalize()

    def release(self, number, key_of=None):
        """number, occupied, becomes free. key_of(n) gives the order key of an
        occupied number n; it is called only for a new edge of a block split"""
        i = self.index_of(number)
        if i is None or not self.blocks[i]['occupied']:
            raise ValueError('number %s is not occupied' % number)
        block = self.blocks[i]
        parts = []
        if number > block['start']:
            below = number - 1
            last = block['first'] if below == block['start'] else (key_of(below) if key_of else None)
            parts.append(dict(block, end=below, last=last))
        parts.append(_free(number, number))
        if number < block['end']:
            above = number + 1
            first = block['last'] if above == block['end'] else (key_of(above) if key_of else None)
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
                merged[-1]['end'] = block['end']
                if block['occupied']:
                    merged[-1]['last'] = block['last']
                continue
            merged.append(dict(block))
        while merged and not merged[-1]['occupied']:
            merged.pop()
        for i, block in enumerate(merged):
            if not block['occupied']:
                block['first'] = merged[i - 1]['last'] if i > 0 else None
                block['last'] = merged[i + 1]['first'] if i + 1 < len(merged) else None
        self.blocks = merged

    def shape(self):
        return [(b['start'], b['end'], b['occupied'], b['first'], b['last']) for b in self.blocks]

    @classmethod
    def from_numbers(cls, numbers, starting_value=0):
        """The blocks of a period from its numbers in use: sorted (number, order key)"""
        blocks = cls()
        previous_end = starting_value
        for number, key in numbers:
            if number > previous_end + 1:
                blocks.blocks.append(_free(previous_end + 1, number - 1))
            blocks.blocks.append(dict(id=None, start=number, end=number, occupied=True, first=key, last=key))
            previous_end = number
        blocks.normalize()
        return blocks


def _free(start, end):
    return dict(id=None, start=start, end=end, occupied=False, first=None, last=None)


def fits(key, lower, upper):
    if key is None:
        return lower is None and upper is None
    return (lower is None or lower <= key) and (upper is None or key <= upper)


def order_key(value, dtype):
    """An order value as an integer that sorts as the value: YYYYMMDD for a
    date (dtype D), milliseconds since the epoch in UTC for a timestamp"""
    if value is None:
        return None
    if dtype == 'D':
        if isinstance(value, datetime):
            value = value.date()
        return value.year * 10000 + value.month * 100 + value.day
    if not isinstance(value, datetime):
        value = datetime(value.year, value.month, value.day)
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc)
    return calendar.timegm(value.timetuple()) * 1000 + value.microsecond // 1000


def _escaped(txt):
    for c in (LIKE_ESCAPE, '%', '_'):
        txt = txt.replace(c, LIKE_ESCAPE + c)
    return txt


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('counter', pkey='codekey', pkey_columns='pkg,tbl,fld,code',
                        name_long='!![en]Counter', name_plural='!![en]Counters', multi_tenant=True)
        self.sysFields(tbl, id=False, ldel=False)
        tbl.column('codekey', size=':80', readOnly=True, name_long='!![en]Codekey', indexed=True)
        tbl.column('pkg', size=':12', readOnly=True, name_long='!![en]Package')
        tbl.column('tbl', size=':30', readOnly=True, name_long='!![en]Table')
        tbl.column('fld', size=':30', readOnly=True, name_long='!![en]Field')
        tbl.column('code', size=':12', readOnly=True, name_long='!![en]Code')

    def use_dbstores(self, forced_dbstore=None, env_forced_dbstore=None, **kwargs):
        return True

    # ------------------------------------------------------------------
    # switch and counter parameters
    # ------------------------------------------------------------------

    def switchValue(self, counters=None):
        """counters when given, else the experimental switch new_counters/counters"""
        if counters is not None:
            return counters
        application = self.db.application
        return application.experimentalValue('new_counters', 'counters') if application else None

    def isEnabledFor(self, tblobj, field, record=None, counters=None):
        """True when tblobj.field is numbered here: the experimental switch
        new_counters/counters (or counters, which replaces it) lists
        'pkg.table.field', or is '*'. With '*' a recycling counter without an
        order (see orderField) stays on adm.counter"""
        listed = self.switchValue(counters)
        if not listed:
            return False
        if listed != '*':
            return '%s.%s' % (tblobj.fullname, field) in [k.strip() for k in listed.split(',')]
        counter_pars = tblobj.getCounterPars(field, record)
        return not (counter_pars and counter_pars.get('recycle') and not self.orderField(counter_pars))

    def counterPars(self, tblobj, field, record):
        counter_pars = tblobj.getCounterPars(field, record)
        if counter_pars and counter_pars.get('recycle') and not self.orderField(counter_pars):
            raise self.exception('business_logic',
                                 msg='Counter %s.%s: recycle requires an order_field' % (tblobj.fullname, field))
        return counter_pars

    def orderField(self, counter_pars):
        """The field whose order the numbers follow: order_field, else the
        date_field unless the counter is date_tolerant, else None"""
        if counter_pars.get('order_field'):
            return counter_pars['order_field']
        if counter_pars.get('date_field') and not counter_pars.get('date_tolerant'):
            return counter_pars['date_field']
        return None

    def orderDtype(self, tblobj, counter_pars):
        order_field = self.orderField(counter_pars)
        return tblobj.column(order_field).dtype if order_field else None

    def orderKey(self, tblobj, counter_pars, record, guess=False):
        """The order key of record. A record not inserted yet (guess) takes now
        for a missing timestamp, and None for a missing date"""
        order_field = self.orderField(counter_pars)
        if not order_field:
            return None
        dtype = self.orderDtype(tblobj, counter_pars)
        value = record.get(order_field) if hasattr(record, 'get') else record[order_field]
        if value is None and guess:
            if dtype == 'D':
                return None
            value = datetime.now(timezone.utc) if dtype == 'DHZ' else datetime.now()
        if value is None:
            raise self.exception('business_logic', msg=self.translate(
                '!!Missing %s. Mandatory for counter %s') % (order_field, tblobj.fullname))
        return order_key(value, dtype)

    def translate(self, txt):
        return self.db.localizer.translate(txt, language=self.db.currentEnv.get('locale'))

    # ------------------------------------------------------------------
    # format of a sequence (as adm.counter)
    # ------------------------------------------------------------------

    def boundaries(self, format=None, code=None, **kwargs):
        format = format.replace('$K', '$%s' % ('K' * len(code)))
        result = dict()
        for k in 'YMDKN':
            f = format
            for n in 'YMDKN'.replace(k, ''):
                f = f.replace('$%s' % n, n)
            s = re.search("(\\$%s+)" % k, f)
            s = s.span() if s else None
            result[k] = (s[0], s[1] - 1) if s else (None, None)
        return result

    def _ymd(self, date_value):
        return (str(date_value.year), str(date_value.month).zfill(2), str(date_value.day).zfill(2))

    def _date(self, tblobj, field, counter_pars, record):
        date_field = counter_pars.get('date_field')
        if not date_field:
            return None
        value = record.get(date_field) if hasattr(record, 'get') else record[date_field]
        if not value:
            raise self.exception('business_logic', msg=self.translate(
                '!!Missing %s. Mandatory for counter %s') % (date_field, field))
        return value

    def periodOf(self, tblobj, field, counter_pars, record):
        "The period of record in its counter: the parts of the date the format holds"
        value = self._date(tblobj, field, counter_pars, record)
        if value is None:
            return ''
        ymd = self._ymd(value)
        format = counter_pars.get('format', '')
        return ''.join(part for marker, part in zip(('$Y', '$M', '$D'), ymd) if marker in format)

    def formatSequence(self, tblobj, field, record, number, counter_pars=None):
        counter_pars = counter_pars or tblobj.getCounterPars(field, record)
        base = counter_pars.get('base')
        if base:
            base = BASE[0:base] if isinstance(base, int) else base
            digits = []
            n = number
            while n:
                digits.insert(0, base[n % len(base)])
                n //= len(base)
            text = ''.join(digits)
        else:
            text = str(number)
        output = counter_pars['format']
        x = '$N%s' % output.split('$N')[1]
        output = output.replace(x, text.zfill(len(x) - 1))
        output = output.replace('$K', counter_pars['code'])
        value = self._date(tblobj, field, counter_pars, record)
        if value:
            ymd = self._ymd(value)
            output = output.replace('$YYYY', ymd[0]).replace('$YY', ymd[0][2:])
            output = output.replace('$MM', ymd[1]).replace('$DD', ymd[2])
        return output

    def sequenceNumber(self, counter_pars, sequence):
        "The number of a formatted sequence, or None when the text does not hold one"
        N_start, N_end = self.boundaries(**counter_pars)['N']
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

    def isSequenceOf(self, tblobj, field, counter_pars, record, sequence):
        "The number of sequence when it is a sequence of the series of record, else None"
        number = self.sequenceNumber(counter_pars, sequence)
        if number is None:
            return None
        if self.formatSequence(tblobj, field, record, number, counter_pars=counter_pars) != sequence:
            return None
        return number

    # ------------------------------------------------------------------
    # counter header and blocks
    # ------------------------------------------------------------------

    def counterKey(self, tblobj, field, counter_pars):
        "The codekey of the counter, created when missing"
        record = dict(pkg=tblobj.pkg.name, tbl=tblobj.name, fld=field, code=counter_pars['code'])
        codekey = self.pkeyValue(record)
        if self.existsRecord(codekey):
            return codekey
        # two first saves of a counter may insert it together. A failed insert
        # would roll back the whole save (db.execute rolls back on error), so the
        # second insert does nothing instead and the row of the first is used
        tsType = self.column('__ins_ts').dtype
        now = datetime.now(timezone.utc) if tsType == 'DHZ' else datetime.now()
        record.update(codekey=codekey, __ins_ts=now, __mod_ts=now)
        sqlnames = self.model.sqlnamemapper
        sql = 'INSERT INTO %s(%s) VALUES (%s) ON CONFLICT (%s) DO NOTHING;' % (
            self.model.sqlfullname, ','.join(sqlnames[k] for k in record),
            ','.join(':%s' % k for k in record), sqlnames['codekey'])
        self.db.execute(sql, record, dbtable=self.fullname)
        return codekey

    def admFloor(self, tblobj, field, counter_pars, record):
        """(counter, last_used) of the adm.counter record of the period of record,
        or None: the numbers adm.counter has given, even those deleted since"""
        if 'adm' not in self.db.packages:
            return None
        adm_counter = self.db.table('adm.counter')
        codekey = adm_counter.getCounterPkey(tblobj=tblobj, field=field, record=record)
        rows = adm_counter.query(columns='$counter,$last_used', where='$codekey=:codekey', codekey=codekey,
                                 addPkeyColumn=False).fetch()
        if not rows or not rows[0]['counter']:
            return None
        return rows[0]['counter'], rows[0]['last_used']

    def rebuildBlocks(self, tblobj, field, counter_pars, record, numbers):
        """The blocks of a period from its numbers in use. For a counter that does
        not recycle, the numbers adm.counter gave above the highest one still in
        the table stay occupied: a deleted number is never given again"""
        starting_value = counter_pars.get('starting_value') or 0
        blocks = NumberBlocks.from_numbers(numbers, starting_value)
        floor = None if counter_pars.get('recycle') else self.admFloor(tblobj, field, counter_pars, record)
        if floor and floor[0] > (blocks.last_number or starting_value):
            key = order_key(floor[1], self.orderDtype(tblobj, counter_pars)) if self.orderField(counter_pars) else None
            blocks.occupy_range(blocks.last_number + 1 if blocks.last_number else starting_value + 1, floor[0], key)
        return blocks

    def loadBlocks(self, codekey, period):
        rows = self.db.table('sys.counter_block').query(
            columns='$id,$block_start,$block_end,$occupied,$order_first,$order_last',
            where='$counter_codekey=:codekey AND $period=:period', codekey=codekey, period=period,
            order_by='$block_start', addPkeyColumn=False).fetch()
        return NumberBlocks([dict(id=r['id'], start=r['block_start'], end=r['block_end'],
                                  occupied=bool(r['occupied']), first=r['order_first'], last=r['order_last'])
                             for r in rows])

    def storeBlocks(self, codekey, period, blocks, stored):
        """Write blocks against stored ({id: shape} as loaded): update the changed
        ones, insert the new ones, delete the ones gone"""
        block_tbl = self.db.table('sys.counter_block')
        kept = set()
        for block in blocks.blocks:
            shape = (block['start'], block['end'], block['occupied'], block['first'], block['last'])
            values = dict(counter_codekey=codekey, period=period, block_start=block['start'],
                          block_end=block['end'], occupied=block['occupied'],
                          order_first=block['first'], order_last=block['last'])
            if block['id'] in stored:
                kept.add(block['id'])
                if stored[block['id']] != shape:
                    with block_tbl.recordToUpdate(block['id']) as row:
                        row.update(values)
            else:
                block_tbl.insert(values)
                block['id'] = values['id']
        for pkey in set(stored) - kept:
            block_tbl.delete(pkey)

    def seriesNumbers(self, tblobj, field, counter_pars, record, exclude_pkey=None):
        """The numbers in use of the series of record, read from the table:
        (sorted [(number, order key)], errors)"""
        N_start, N_end = self.boundaries(**counter_pars)['N']
        sample = self.formatSequence(tblobj, field, record, 0, counter_pars=counter_pars)
        pattern = '%s%s%s' % (_escaped(sample[:N_start]), '_' * (N_end - N_start), _escaped(sample[N_end:]))
        where = ["$%s LIKE :pattern ESCAPE '%s'" % (field, LIKE_ESCAPE)]
        if exclude_pkey is not None:
            where.append('$%s != :exclude_pkey' % tblobj.pkey)
        order_field = self.orderField(counter_pars)
        columns = '$%s,$%s' % (tblobj.pkey, field)
        if order_field:
            columns = '%s,$%s' % (columns, order_field)
        rows = tblobj.query(columns=columns, where=' AND '.join(where), pattern=pattern,
                            exclude_pkey=exclude_pkey, excludeDraft=False, excludeLogicalDeleted=False,
                            subtable='*', addPkeyColumn=False).fetch()
        return self._numbersOf(tblobj, field, counter_pars, record, rows)

    def _numbersOf(self, tblobj, field, counter_pars, record, rows):
        numbers = []
        errors = []
        dtype = self.orderDtype(tblobj, counter_pars)
        order_field = self.orderField(counter_pars)
        for row in rows:
            sequence = row[field]
            number = self.isSequenceOf(tblobj, field, counter_pars, record, sequence)
            if number is None:
                errors.append(dict(kind='not_a_number', sequence=sequence, pkey=row[tblobj.pkey]))
                continue
            key = None
            if order_field:
                if row[order_field] is None:
                    errors.append(dict(kind='missing_order_value', sequence=sequence, pkey=row[tblobj.pkey]))
                    continue
                key = order_key(row[order_field], dtype)
            numbers.append((number, key, row[tblobj.pkey]))
        numbers.sort(key=lambda n: n[0])
        previous = None
        for number, key, pkey in numbers:
            if previous and previous[0] == number:
                errors.append(dict(kind='duplicate', number=number, pkey=pkey))
            elif previous and key is not None and previous[1] is not None and key < previous[1]:
                errors.append(dict(kind='wrong_order', number=number, pkey=pkey))
            previous = (number, key)
        return [(n, k) for n, k, p in numbers], errors

    def _withPeriod(self, tblobj, field, record, counter_pars, handler, exclude_pkey=None):
        """Run handler(blocks) under the lock of the counter, on the blocks of the
        period of record, then store them. A period without blocks is first
        loaded from the numbers already in the table."""
        codekey = self.counterKey(tblobj, field, counter_pars)
        period = self.periodOf(tblobj, field, counter_pars, record)
        with self.recordToUpdate(codekey, mode='record'):
            blocks = self.loadBlocks(codekey, period)
            stored = dict(zip([b['id'] for b in blocks.blocks], blocks.shape()))
            if not blocks.blocks:
                numbers, errors = self.seriesNumbers(tblobj, field, counter_pars, record, exclude_pkey=exclude_pkey)
                if errors:
                    raise self.exception('business_logic', msg='Counter %s.%s, period %s: the numbers in use are '
                                         'not consistent, see analyzeCounter' % (tblobj.fullname, field, period))
                blocks = self.rebuildBlocks(tblobj, field, counter_pars, record, numbers)
            result = handler(blocks)
            self.storeBlocks(codekey, period, blocks, stored)
        return result

    def _rootstore(self, counter_pars):
        if counter_pars.get('rootstore'):
            return self.db.tempEnv(storename=self.db.rootstore)
        return self.db.tempEnv()

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
                self.releaseCounter(tblobj=tblobj, field=field, record=dict(old_record))
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
        key = self.orderKey(tblobj, counter_pars, record)

        def handler(blocks):
            number = blocks.recyclable(key) if counter_pars.get('recycle') else None
            if number is None:
                number = (blocks.last_number or (counter_pars.get('starting_value') or 0)) + 1
                self._checkWindow(tblobj, field, counter_pars, blocks, number, key)
            blocks.occupy(number, key)
            return number

        number = self._withPeriod(tblobj, field, record, counter_pars, handler,
                                  exclude_pkey=record.get(tblobj.pkey))
        return self.formatSequence(tblobj, field, record, number, counter_pars=counter_pars)

    def claimSequence(self, tblobj, field, record, counter_pars):
        """A number of the series set by hand becomes occupied; a value that is
        not a number of this series is left alone"""
        sequence = record[field]
        number = self.isSequenceOf(tblobj, field, counter_pars, record, sequence)
        if number is None:
            return
        key = self.orderKey(tblobj, counter_pars, record)

        def handler(blocks):
            if blocks.is_occupied(number):
                raise self.exception('business_logic', msg=self.translate(
                    '!![en]%(sequence)s is already in use') % dict(sequence=sequence))
            self._checkWindow(tblobj, field, counter_pars, blocks, number, key)
            blocks.occupy(number, key)

        self._withPeriod(tblobj, field, record, counter_pars, handler, exclude_pkey=record.get(tblobj.pkey))

    def _checkWindow(self, tblobj, field, counter_pars, blocks, number, key):
        if not self.orderField(counter_pars):
            return
        lower, upper = blocks.window(number)
        if fits(key, lower, upper):
            return
        msgTpl = counter_pars.get('message_dateError', '!!Incompatible date assigning %(fieldname)s counter')
        fieldname = self.translate(tblobj.column(field).name_long or field)
        raise self.exception('business_logic', msg=self.translate(msgTpl) % dict(fieldname=fieldname,
                                                                                 last_used=lower))

    def releaseCounter(self, tblobj=None, field=None, record=None):
        """The number of record becomes free; record[field] is cleared. A
        neighbour missing from the table (removed outside the triggers) becomes
        an open bound: checkCounter reports the difference"""
        counter_pars = self.counterPars(tblobj, field, record)
        if not counter_pars:
            return
        number = self.isSequenceOf(tblobj, field, counter_pars, record, record.get(field))
        if number is None:
            return
        order_field = self.orderField(counter_pars)
        dtype = self.orderDtype(tblobj, counter_pars)

        def key_of(n):
            if not order_field:
                return None
            rows = tblobj.query(columns='$%s' % order_field, where='$%s=:sequence' % field,
                                sequence=self.formatSequence(tblobj, field, record, n, counter_pars=counter_pars),
                                excludeDraft=False, excludeLogicalDeleted=False, subtable='*',
                                addPkeyColumn=False).fetch()
            return order_key(rows[0][order_field], dtype) if rows and rows[0][order_field] is not None else None

        def handler(blocks):
            if blocks.is_occupied(number):
                blocks.release(number, key_of=key_of)

        with self._rootstore(counter_pars):
            self._withPeriod(tblobj, field, record, counter_pars, handler, exclude_pkey=record.get(tblobj.pkey))
        record[field] = None
        if counter_pars.get('onReleased'):
            counter_pars['onReleased'](record=record, field=field)

    def guessNextSequence(self, tblobj=None, field=None, record=None):
        """(sequence, info) of the number assignCounter would give record now,
        without writing; info['recycled'] is True for a recycled number"""
        counter_pars = self.counterPars(tblobj, field, record)
        with self._rootstore(counter_pars):
            codekey = self.pkeyValue(dict(pkg=tblobj.pkg.name, tbl=tblobj.name, fld=field,
                                          code=counter_pars['code']))
            period = self.periodOf(tblobj, field, counter_pars, record)
            blocks = self.loadBlocks(codekey, period)
            if not blocks.blocks:
                numbers = self.seriesNumbers(tblobj, field, counter_pars, record)[0]
                blocks = self.rebuildBlocks(tblobj, field, counter_pars, record, numbers)
            number = None
            if counter_pars.get('recycle'):
                key = self.orderKey(tblobj, counter_pars, record, guess=True)
                number = blocks.recyclable(key) if key is not None else None
            info = dict(recycled=number is not None)
            if number is None:
                number = (blocks.last_number or (counter_pars.get('starting_value') or 0)) + 1
        return self.formatSequence(tblobj, field, record, number, counter_pars=counter_pars), info

    @public_method
    def freeSequences(self, table=None, field=None, record=None, limit=500):
        """The free numbers of the period of record, lowest first, each with its
        window of order keys: a list of dict(sequence, number, order_from, order_to)"""
        tblobj = self.db.table(table)
        counter_pars = self.counterPars(tblobj, field, record)
        codekey = self.pkeyValue(dict(pkg=tblobj.pkg.name, tbl=tblobj.name, fld=field, code=counter_pars['code']))
        blocks = self.loadBlocks(codekey, self.periodOf(tblobj, field, counter_pars, record))
        result = []
        for block in blocks.blocks:
            if block['occupied']:
                continue
            for number in range(block['start'], block['end'] + 1):
                if len(result) >= limit:
                    return result
                result.append(dict(number=number, order_from=block['first'], order_to=block['last'],
                                   sequence=self.formatSequence(tblobj, field, record, number,
                                                                counter_pars=counter_pars)))
        return result

    # ------------------------------------------------------------------
    # analysis, load and check of every period of a counter
    # ------------------------------------------------------------------

    def collectPeriods(self, tblobj, field):
        """{(codekey, period): dict(numbers, errors, record, counter_pars)} for every
        period of tblobj.field, read from the table"""
        groups = {}
        rows = tblobj.query(columns='*', where='$%s IS NOT NULL' % field, excludeDraft=False,
                            excludeLogicalDeleted=False, subtable='*', bagFields=False).fetch()
        for row in rows:
            record = dict(row)
            counter_pars = tblobj.getCounterPars(field, record)
            if not counter_pars:
                continue
            codekey = self.pkeyValue(dict(pkg=tblobj.pkg.name, tbl=tblobj.name, fld=field,
                                          code=counter_pars['code']))
            group = groups.setdefault((codekey, self.periodOf(tblobj, field, counter_pars, record)),
                                      dict(rows=[], record=record, counter_pars=counter_pars))
            group['rows'].append(record)
        result = {}
        for series, group in groups.items():
            numbers, errors = self._numbersOf(tblobj, field, group['counter_pars'], group['record'], group['rows'])
            result[series] = dict(numbers=numbers, errors=errors, counter_pars=group['counter_pars'],
                                  record=group['record'])
        return result

    @public_method
    def analyzeCounter(self, table=None, field=None):
        """Read-only report of every period of table.field, keyed 'codekey/period':
        number count and errors (not_a_number, missing_order_value, duplicate, wrong_order)"""
        tblobj = self.db.table(table)
        return {'%s/%s' % series: dict(count=len(group['numbers']), errors=group['errors'])
                for series, group in self.collectPeriods(tblobj, field).items()}

    @public_method
    def loadCounter(self, table=None, field=None):
        """Build the blocks of every clean period of table.field from the table,
        replacing the stored ones; a period with errors is skipped.
        Returns {'codekey/period': 'loaded' | errors}"""
        tblobj = self.db.table(table)
        report = {}
        for (codekey, period), group in self.collectPeriods(tblobj, field).items():
            if group['errors']:
                report['%s/%s' % (codekey, period)] = group['errors']
                continue
            self._loadPeriod(tblobj, field, codekey, period, group)
            report['%s/%s' % (codekey, period)] = 'loaded'
        return report

    def _loadPeriod(self, tblobj, field, codekey, period, group):
        counter_pars = group['counter_pars']
        self.counterKey(tblobj, field, counter_pars)
        with self.recordToUpdate(codekey, mode='record'):
            stored = {b['id']: None for b in self.loadBlocks(codekey, period).blocks}
            blocks = self.rebuildBlocks(tblobj, field, counter_pars, group['record'], group['numbers'])
            self.storeBlocks(codekey, period, blocks, stored)

    @public_method
    def checkCounter(self, table=None, field=None):
        """Read-only comparison of the stored blocks with the table:
        {'codekey/period': problems}.

        - not_loaded: the period has no blocks yet (it is loaded at its first use);
        - a recycling counter: blocks_differ when the blocks differ from the ones
          rebuilt from the table;
        - a counter that does not recycle keeps deleted numbers occupied, so only
          numbers in the table missing from the blocks are reported
          (missing_from_blocks)"""
        tblobj = self.db.table(table)
        report = {}
        for (codekey, period), group in self.collectPeriods(tblobj, field).items():
            problems = group['errors'] or self._checkPeriod(tblobj, field, codekey, period, group)
            if problems:
                report['%s/%s' % (codekey, period)] = problems
        return report

    def _checkPeriod(self, tblobj, field, codekey, period, group):
        """The problems of the stored blocks of a clean period, [] when none"""
        stored = self.loadBlocks(codekey, period)
        if not stored.blocks:
            return [dict(kind='not_loaded')]
        counter_pars = group['counter_pars']
        if counter_pars.get('recycle'):
            expected = self.rebuildBlocks(tblobj, field, counter_pars, group['record'], group['numbers'])
            if expected.shape() != stored.shape():
                return [dict(kind='blocks_differ', expected=expected.shape(), stored=stored.shape())]
            return []
        missing = [number for number, key in group['numbers'] if not stored.is_occupied(number)]
        return [dict(kind='missing_from_blocks', numbers=missing)] if missing else []

    # ------------------------------------------------------------------
    # moving an instance from adm.counter
    # ------------------------------------------------------------------

    def countersToMigrate(self, counters=None, tables=None):
        """[(tblobj, field)] of the counters the switch new_counters/counters (or
        counters, which replaces it) names: every counter of the db for '*'.
        tables, a list of pkg.table, restricts them"""
        listed = self.switchValue(counters)
        if not listed:
            return []
        if listed == '*':
            result = [(tblobj, field) for pkg in self.db.packages.values()
                      for tblobj in [t.dbtable for t in (pkg['tables'] or {}).values()]
                      for field in (tblobj.counterColumns() or [])]
        else:
            result = []
            for key in listed.split(','):
                table, field = key.strip().rsplit('.', 1)
                result.append((self.db.table(table), field))
        if tables:
            result = [(tblobj, field) for tblobj, field in result if tblobj.fullname in tables]
        return result

    def migrateCounters(self, counters=None, tables=None, load=False):
        """Report, and with load build, the blocks of every period of the counters
        countersToMigrate names; a period '*' leaves on adm.counter is skipped.
        Only periods without blocks are loaded: the others are checked.

        A list of dict(table, field, period, count, status, problems). status:
        'ok', 'loaded', 'not_loaded' (no load asked), 'errors' (numbers in the
        table that are not consistent, or a recycling counter without an order:
        fix them first), 'blocks_differ' or 'missing_from_blocks' (see checkCounter)."""
        report = []
        for tblobj, field in self.countersToMigrate(counters, tables):
            for (codekey, period), group in sorted(self.collectPeriods(tblobj, field).items()):
                if not self.isEnabledFor(tblobj, field, record=group['record'], counters=counters):
                    continue
                problems = list(group['errors'])
                if group['counter_pars'].get('recycle') and not self.orderField(group['counter_pars']):
                    problems.append(dict(kind='recycle_without_order'))
                loaded = False
                if problems:
                    status = 'errors'
                else:
                    problems = self._checkPeriod(tblobj, field, codekey, period, group)
                    if load and problems == [dict(kind='not_loaded')]:
                        self._loadPeriod(tblobj, field, codekey, period, group)
                        loaded = True
                        problems = self._checkPeriod(tblobj, field, codekey, period, group)
                    status = problems[0]['kind'] if problems else ('loaded' if loaded else 'ok')
                report.append(dict(table=tblobj.fullname, field=field, period=period,
                                   count=len(group['numbers']), status=status, problems=problems))
        return report

