#!/usr/bin/python
# -*- coding: utf-8 -*-

import html

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrwebstruct import struct_method
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag

EVENT_KINDS = dict(I='!![en]Insertion', U='!![en]Modification', D='!![en]Deletion', A='!![en]Initial state')
EVENT_CODES = dict(I='INS', U='UPD', D='DEL', A='---')


class AuditHistory(BaseComponent):
    py_requires = 'gnrcomponents/framegrid:FrameGrid'
    css_requires = 'audit_components'

    @struct_method
    def audit_historyPalette(self, pane, paletteCode=None, **kwargs):
        """The history of the form record: the events of ``audit.event`` in a grid, the selected one in detail."""
        palette = pane.palettePane(paletteCode=paletteCode, title='!!Record History',
                                   dockButton_iconClass='iconbox audit_history',
                                   width='820px', height='560px', **kwargs)
        bc = palette.borderContainer(_anchor=True)
        bc.dataRpc('.history', self.audit_recordHistory, tbl='=#FORM.controller.table',
                   pkey='=#FORM.pkey', _loaded='^#FORM.controller.loaded',
                   _if='pkey && pkey!="*newrecord*"', _else='SET .history = null;')
        bc.dataController("""var row = selected && history ? history.getItem(selected) : null;
                             SET .detail = row ? row.deepCopy() : null;""",
                          selected='^.selected', history='^.history')
        bc.contentPane(region='left', width='400px', splitter=True).bagGrid(
            frameCode='%s_events' % paletteCode, datapath='.events', storepath='#ANCHOR.history',
            struct=self.audit_eventStruct, grid_selected_key='#ANCHOR.selected',
            slots='5,searchOn,*', addrow=False, delrow=False, batchAssign=False,
            gridEditor=False)
        self.audit_detailPane(bc)

    @struct_method
    def audit_tableHistoryPalette(self, pane, paletteCode=None, table=None, **kwargs):
        """The history of a whole table: a TH on its events of ``audit.event``, the selected one in detail."""
        palette = pane.palettePane(paletteCode=paletteCode, title='!![en]Table History',
                                   dockButton_iconClass='iconbox audit_history',
                                   width='1000px', height='600px', **kwargs)
        bc = palette.borderContainer(_anchor=True)
        thCode = '%s_th' % paletteCode
        bc.contentPane(region='left', width='600px', splitter=True).plainTableHandler(
            table='audit.event', nodeId=thCode, datapath='.th', viewResource='ViewTableHistory',
            condition='$tbl=:tbl', condition_tbl=table, virtualStore=False, configurable=False,
            extendedQuery=True, view_store__onStart=True)
        bc.dataRpc('.detail', self.audit_eventDetail, event_id='^.th.view.grid.selectedId',
                   _if='event_id', _else='SET .detail = null;')
        self.audit_detailPane(bc)

    def audit_detailPane(self, bc):
        detail = bc.contentPane(region='center', datapath='.detail', _class='audit_detail_pane')
        detail.div('^.title', _class='audit_detail_title')
        detail.div('!![en]Deleted record: the state before the deletion', _class='audit_detail_deleted',
                   hidden='^.code?=#v!="DEL"')
        changes = detail.div(hidden='^.changes_html?=!#v')
        changes.div('!![en]Changed fields', _class='audit_detail_section')
        changes.div('^.changes_html', _class='audit_kv')
        detail.div('!![en]Record', _class='audit_detail_section', hidden='^.state_html?=!#v')
        detail.div('^.state_html', _class='audit_kv')

    def audit_eventStruct(self, struct):
        r = struct.view().rows()
        r.cell('version', name='V', dtype='L', width='3em')
        r.cell('ts', name='!![en]Date', dtype='DH', width='9em', filterField=True)
        r.cell('code', name='!![en]Event', width='4em', filterField=True)
        r.cell('username', name='!![en]User', width='8em', filterField=True)
        r.cell('changes', name='!![en]Changes', width='12em', filterField=True, filterField_aggr=', ')
        r.cell('key', hidden=True)

    @public_method
    def audit_recordHistory(self, tbl=None, pkey=None):
        """The events of a record as grid rows, with the detail of each one."""
        hidden = self.db.table('audit.event').displayHiddenColumns(tbl)
        result = Bag()
        previous_state = None
        for event in self.db.table('audit.event').recordHistory(tbl, pkey):
            row = self.audit_eventRow(event, previous_state, hidden)
            result.setItem(row['key'], row)
            previous_state = event['state']
        return result

    @public_method
    def audit_eventDetail(self, event_id=None):
        """The detail of one event, as in the record history."""
        event = self.db.table('audit.event').record(event_id, mode='dict')
        previous_state = None
        for item in self.db.table('audit.event').recordHistory(event['tbl'], event['record_pkey']):
            if item['event_id'] == event['event_id']:
                return self.audit_eventRow(item, previous_state, self.db.table('audit.event').displayHiddenColumns(event['tbl']))
            previous_state = item['state']

    def audit_eventRow(self, event, previous_state, hidden):
        """One event as a grid row with its detail.

        An insert or initial state shows the whole record with nothing
        highlighted; an update lists its changed fields and highlights them
        in the record at that version; a delete shows the record as it was
        before the deletion."""
        ts = event['ts']
        version = event['version']
        version_label = str(version)
        if event['expected_version'] is not None:
            version_label = '%s (expected %s)' % (version, event['expected_version'])
        changes = diffLines(event['data'], hidden) if event['op'] == 'U' else []
        changed = set(label for label, value in changes)
        state = previous_state if event['op'] == 'D' else event['state']
        kind = self._(EVENT_KINDS[event['op']])
        return Bag(dict(
            key='v_%s' % event['event_id'], event_id=event['event_id'], ts=ts,
            code=EVENT_CODES[event['op']], version=version, username=event['username'],
            changes=', '.join(label for label, value in changes),
            title='%s · %s · v%s · %s' % (self.toText(ts, format='d MMMM yyyy HH:mm'), kind,
                                           version_label, event['username'] or ''),
            changes_html=kvHtml(changes),
            state_html=kvHtml(valueLines(state, hidden), changed) if state is not None else ''))


def valueLines(data, hidden, prefix=None):
    """The ``(path, value)`` lines of a Bag of values, Bag columns path by path."""
    lines = []
    for node in data.nodes:
        if not prefix and node.label in hidden:
            continue
        label = '%s.%s' % (prefix, node.label) if prefix else node.label
        if isinstance(node.value, Bag):
            lines.extend(valueLines(node.value, hidden, label))
        else:
            lines.append((label, node.value))
    return lines


def diffLines(diff, hidden, prefix=None):
    """The ``(path, value)`` lines of an update diff; a removed node reads as removed."""
    lines = []
    for node in diff.nodes:
        if not prefix and node.label in hidden:
            continue
        label = '%s.%s' % (prefix, node.label) if prefix else node.label
        if node.attr.get('_deleted'):
            lines.append((label, '(removed)'))
        elif isinstance(node.value, Bag) and node.value:
            lines.extend(diffLines(node.value, hidden, label))
        else:
            lines.append((label, node.value))
    return lines


def kvHtml(lines, highlighted=None):
    highlighted = highlighted or set()
    cells = []
    for label, value in lines:
        value_class = 'audit_kv_value audit_kv_changed' if label in highlighted else 'audit_kv_value'
        cells.append('<div class="audit_kv_label">%s</div><div class="%s">%s</div>'
                     % (html.escape(label), value_class, '' if value is None else html.escape(str(value))))
    return ''.join(cells)
