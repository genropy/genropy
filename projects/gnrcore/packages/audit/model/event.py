# encoding: utf-8
import datetime
import json
from decimal import Decimal

from gnr.core.gnrbag import Bag

BATCH_LOCK = "hashtext('audit.batch')"


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('event', pkey='event_id', name_long='!!Audit event',
                        name_plural='!!Audit events')
        tbl.column('event_id', dtype='serial', name_long='!!Event id')
        tbl.column('queue_id', dtype='L', indexed=True, name_long='!!Queue id')
        tbl.column('ts', dtype='DHZ', name_long='!!Timestamp')
        tbl.column('txid', dtype='L', name_long='!!Transaction id')
        tbl.column('tbl', name_long='!!Table')
        tbl.column('record_pkey', name_long='!!Record pkey')
        tbl.column('op', size='1', name_long='!!Operation')
        tbl.column('version', dtype='L', name_long='!!Version')
        tbl.column('expected_version', dtype='L', name_long='!!Expected version')
        tbl.column('username', name_long='!!User')
        tbl.column('caller', name_long='!!Caller')
        tbl.column('sqlcommand', name_long='!!Sql command')
        tbl.column('data', dtype='X', name_long='!!Data')
        tbl.index('tbl,record_pkey')
        tbl.sqlCode(text='ALTER TABLE {sqlfullname} ALTER COLUMN data SET COMPRESSION lz4;')

    def batch(self, block_size=1000):
        """Turn the rows of ``audit.queue`` into events.

        One run at a time: a run that finds the advisory lock taken returns
        None. A run takes only the rows up to the ``max(queue_id)`` read at
        its start, in blocks ordered by ``queue_id``; each block deletes its
        queue rows, writes the events and the last state of the records in
        one transaction. A failure rolls the block back and leaves its rows
        in the queue.

        :param block_size: queue rows per block
        :returns: the events written with a version gap, as dicts with
                  ``tbl``, ``record_pkey``, ``version``, ``expected_version``
        """
        db = self.db
        if not db.execute(f'SELECT pg_try_advisory_lock({BATCH_LOCK})').fetchone()[0]:
            return None
        queue = db.table('audit.queue').model.sqlfullname
        gaps = []
        try:
            max_queue_id = db.execute(f'SELECT max(queue_id) FROM {queue}').fetchone()[0]
            sql = (f'DELETE FROM {queue} WHERE queue_id IN '
                   f'(SELECT queue_id FROM {queue} WHERE queue_id <= :max_queue_id '
                   'ORDER BY queue_id LIMIT :block_size) '
                   'RETURNING queue_id, ts, txid, tbl, record_pkey, op, version, username, '
                   'caller, sqlcommand, data::text AS data, old_full::text AS old_full')
            while max_queue_id is not None:
                rows = db.execute(sql, dict(max_queue_id=max_queue_id,
                                            block_size=block_size)).fetchall()
                if not rows:
                    break
                try:
                    for row in sorted(rows, key=lambda r: r['queue_id']):
                        gaps.extend(self.eventsFromQueueRow(dict(row)))
                except Exception:
                    db.rollback()
                    raise
                db.commit()
        finally:
            db.rollback()
            db.execute(f'SELECT pg_advisory_unlock({BATCH_LOCK})')
            db.commit()
        return gaps

    def eventsFromQueueRow(self, row):
        """Write the events of one queue row and the new last state of its record.

        A row with ``old_full`` first writes an A event with version 0.

        :returns: the events written with a version gap
        """
        db = self.db
        state_table = db.table('audit.record_state').model.sqlfullname
        key = dict(tbl=row['tbl'], record_pkey=row['record_pkey'])
        state = db.execute(f'SELECT version, data::text AS data FROM {state_table} '
                           'WHERE tbl = :tbl AND record_pkey = :record_pkey', key).fetchone()
        state_version = state['version'] if state else None
        state_values = json.loads(state['data'], parse_float=Decimal) if state else None
        gaps = []
        upsert = (f'INSERT INTO {state_table} (tbl, record_pkey, version, data) '
                  'VALUES (:tbl, :record_pkey, :version, CAST(:data AS jsonb)) '
                  'ON CONFLICT (tbl, record_pkey) DO UPDATE SET version = EXCLUDED.version, '
                  '{data}')
        replace_upsert = upsert.format(data='data = EXCLUDED.data')
        if row['old_full']:
            gaps.extend(self.writeEvent(row, 'A', 0, json.loads(row['old_full'], parse_float=Decimal),
                                        expected_version=0))
            db.execute(replace_upsert, dict(key, version=0, data=row['old_full']))
            state_version = 0
            state_values = json.loads(row['old_full'], parse_float=Decimal)
            if row['op'] == 'U' and row['version'] == 0:
                return gaps
        values = json.loads(row['data'], parse_float=Decimal)
        op = row['op']
        if op == 'I':
            expected_version = 0
        else:
            expected_version = 0 if state_version is None else state_version + 1
        if op == 'U':
            values = self.updatedValues(row['tbl'], state_values or {}, values)
        gaps.extend(self.writeEvent(row, op, row['version'], values,
                                    expected_version=expected_version))
        if op == 'I':
            db.execute(replace_upsert, dict(key, version=row['version'], data=row['data']))
        elif op == 'U':
            db.execute(upsert.format(data=f'data = {state_table}.data || EXCLUDED.data'),
                       dict(key, version=row['version'], data=row['data']))
        else:
            db.execute(f'DELETE FROM {state_table} WHERE tbl = :tbl AND record_pkey = :record_pkey',
                       key)
        return gaps

    def updatedValues(self, tbl, old_values, new_values):
        """The values of an update event: the Bag diff for X columns, the new value otherwise."""
        tblobj = self.db.table(tbl)
        result = {}
        for name, value in new_values.items():
            column = tblobj.column(name)
            if column is not None and column.dtype == 'X':
                old_bag = typedValue(old_values.get(name), 'X')
                new_bag = typedValue(value, 'X')
                if isinstance(old_bag, Bag) and isinstance(new_bag, Bag):
                    result[name] = bagDiff(old_bag, new_bag)
                    continue
            result[name] = value
        return result

    def writeEvent(self, row, op, version, values, expected_version=None):
        """Insert one event; return it as a gap when its version is not the expected one."""
        tblobj = self.db.table(row['tbl'])
        data = Bag()
        for name, value in values.items():
            column = tblobj.column(name)
            data[name] = typedValue(value, column.dtype if column is not None else None)
        gap = expected_version is not None and version != expected_version
        event = dict(queue_id=row['queue_id'], ts=row['ts'], txid=row['txid'], tbl=row['tbl'],
                     record_pkey=row['record_pkey'], op=op, version=version,
                     expected_version=expected_version if gap else None,
                     username=row['username'], caller=row['caller'],
                     sqlcommand=row['sqlcommand'], data=data.toXml() if data else None)
        columns = list(event)
        self.db.execute(f'INSERT INTO {self.model.sqlfullname} ({", ".join(columns)}) '
                        f'VALUES ({", ".join(":" + c for c in columns)})', event)
        if gap:
            return [dict(tbl=row['tbl'], record_pkey=row['record_pkey'], version=version,
                         expected_version=expected_version)]
        return []

    def recordHistory(self, tbl, record_pkey):
        """The history of a record, rebuilt from its events.

        :returns: one dict per event, in version order: the event columns
                  plus ``state``, the whole record after the event as a Bag
                  (None after a D event)
        """
        events = self.query(columns='*,$data', where='$tbl = :tbl AND $record_pkey = :record_pkey',
                            tbl=tbl, record_pkey=record_pkey, order_by='$event_id').fetch()
        history = []
        state = None
        for event in events:
            event = dict(event)
            data = typedValue(event['data'], 'X') or Bag()
            if event['op'] in ('I', 'A'):
                state = data.deepcopy()
            elif event['op'] == 'U':
                state = state.deepcopy() if state is not None else Bag()
                for node in data.nodes:
                    current = state.getNode(node.label)
                    if current is not None and isinstance(current.value, Bag) \
                            and isinstance(node.value, Bag):
                        applyBagDiff(current.value, node.value)
                    else:
                        state[node.label] = copyValue(node.value)
            else:
                state = None
            event['data'] = data
            event['state'] = state
            history.append(event)
        return history

    def displayHiddenColumns(self, tbl):
        """The columns of ``tbl`` left out of the history display: system fields and pkey."""
        tblobj = self.db.table(tbl)
        return set(name for name, column in tblobj.columns.items()
                   if column.attributes.get('_sysfield')) | {tblobj.pkey}

    def changedPaths(self, tbl, data, hidden=None):
        """The changed paths of an update event, Bag columns path by path.

        :param hidden: the columns left out, as from ``displayHiddenColumns``"""
        if hidden is None:
            hidden = self.displayHiddenColumns(tbl)
        paths = []

        def walk(bag, prefix):
            for node in bag.nodes:
                if not prefix and node.label in hidden:
                    continue
                label = '%s.%s' % (prefix, node.label) if prefix else node.label
                if isinstance(node.value, Bag) and node.value and not node.attr.get('_deleted'):
                    walk(node.value, label)
                else:
                    paths.append(label)
        walk(typedValue(data, 'X') or Bag(), None)
        return paths

    def recordCaptions(self, tbl, pkeys):
        """The caption of each record: from the table, or from its delete event when deleted."""
        tblobj = self.db.table(tbl)
        caption_field = tblobj.attributes.get('caption_field')
        pkeys = set(pkeys)
        if not caption_field or not pkeys:
            return {}
        rows = tblobj.query(columns='$%s,$%s' % (tblobj.pkey, caption_field),
                            where='$%s IN :pkeys' % tblobj.pkey, pkeys=list(pkeys),
                            excludeLogicalDeleted=False, excludeDraft=False).fetch()
        captions = dict((row[tblobj.pkey], row[caption_field]) for row in rows)
        deleted = list(pkeys - set(captions))
        if deleted:
            events = self.query(columns='$record_pkey,$data',
                                where="$tbl = :tbl AND $op = 'D' AND $record_pkey IN :pkeys",
                                tbl=tbl, pkeys=deleted, order_by='$event_id').fetch()
            for event in events:
                captions[event['record_pkey']] = (typedValue(event['data'], 'X') or Bag())[caption_field]
        return captions


def typedValue(value, dtype):
    """A value read from the queue jsonb, converted to the dtype of its column."""
    if value is None or isinstance(value, Bag):
        return value
    if dtype == 'X':
        return Bag(value) if value else Bag()
    if dtype == 'D':
        return datetime.date.fromisoformat(value)
    if dtype in ('DH', 'DHZ'):
        return datetime.datetime.fromisoformat(value)
    if dtype == 'H':
        return datetime.time.fromisoformat(value)
    if dtype == 'N':
        return Decimal(value)
    if dtype in ('R', 'F'):
        return float(value)
    return value


def copyValue(value):
    return value.deepcopy() if isinstance(value, Bag) else value


def bagDiff(old, new):
    """The changed paths from ``old`` to ``new``.

    A node whose value is a Bag on both sides appears when something inside
    it or its attributes changed, with its current attributes; a node with a
    changed value or changed attributes appears with its new value and
    attributes; a removed node appears with value None and ``_deleted=True``.
    """
    result = Bag()
    for node in new.nodes:
        old_node = old.getNode(node.label)
        if old_node is None:
            result.setItem(node.label, copyValue(node.value), _attributes=dict(node.attr))
        elif isinstance(node.value, Bag) and isinstance(old_node.value, Bag):
            inner = bagDiff(old_node.value, node.value)
            if inner or node.attr != old_node.attr:
                result.setItem(node.label, inner, _attributes=dict(node.attr))
        elif node.value != old_node.value or node.attr != old_node.attr:
            result.setItem(node.label, copyValue(node.value), _attributes=dict(node.attr))
    for old_node in old.nodes:
        if new.getNode(old_node.label) is None:
            result.setItem(old_node.label, None, _deleted=True)
    return result


def applyBagDiff(state, diff):
    """Apply a diff made by ``bagDiff`` to ``state``, in place."""
    for node in diff.nodes:
        if node.attr.get('_deleted'):
            state.pop(node.label)
            continue
        current = state.getNode(node.label)
        if current is None:
            state.setItem(node.label, copyValue(node.value), _attributes=dict(node.attr))
            continue
        if isinstance(current.value, Bag) and isinstance(node.value, Bag):
            applyBagDiff(current.value, node.value)
        else:
            current.value = copyValue(node.value)
        current.attr.clear()
        current.attr.update(node.attr)
