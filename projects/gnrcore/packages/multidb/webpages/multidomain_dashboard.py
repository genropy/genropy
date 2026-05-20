#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#  Created by Francesco Porcari
#
"""Superadmin dashboard to push content from the rootstore (primary) to a
chosen secondary dbstore, with two tabs:

- Tables: pick any propagable table, see rootstore vs secondary side by side,
  drag rows across, or propagate the selected primary row to ALL secondaries.
- User Objects: same UX, fixed on adm.userobject, with extra filters by tbl
  and objtype.

Row coloring: 'toprop' = only on primary (ready to push), 'localonly' = only
on secondary, 'diff' = present on both sides but different.
"""

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = 'public:Public,th/th:TableHandler,th/th_dynamic:DynamicTableHandler'
    auth_main = 'superadmin'
    pageOptions = {'openMenu': False, 'enableZoom': False}

    USEROBJECT_TABLE = 'adm.userobject'

    def main(self, root, **kwargs):
        frame = root.rootContentPane(datapath='main', design='sidebar',
                                     title='!!Multidomain dashboard')
        frame = frame.center.framePane()
        self._injectStyles(frame)
        frame.top.slotToolbar('5,stackButtons,*', height='28px')
        sc = frame.center.stackContainer(margin='2px')
        self._buildTablesTab(sc.borderContainer(title='!!Tables',
                                                datapath='.tables'))
        self._buildUserObjectsTab(sc.borderContainer(title='!!User Objects',
                                                     datapath='.userobjects'))

    def _injectStyles(self, frame):
        frame.css("._common_d11 .toprop .dojoxGrid-cell",
                  "background: rgba(120, 170, 255, 0.22) !important;")
        frame.css("._common_d11 .localonly .dojoxGrid-cell",
                  "background: rgba(180, 180, 180, 0.15) !important; color:#999;")
        frame.css("._common_d11 .diff", "color:#c0392b !important;")

    def _storeOptions(self):
        return ','.join(sorted(self.db.stores_handler.dbstores.keys()))

    # ------------------------------------------------------------------
    # Tab "Tables"
    # ------------------------------------------------------------------

    def _buildTablesTab(self, bc):
        # Toolbar: pick secondary store + table
        bar = bc.contentPane(region='top').slotToolbar('5,sel,*', height='34px')
        fb = bar.sel.formbuilder(cols=4, border_spacing='3px')
        fb.filteringSelect(value='^.store_secondary', lbl='Secondary',
                           width='12em', values=self._storeOptions())
        fb.remoteSelect(value='^.sync_table', lbl='Table', width='22em',
                        method=self.getPropagableTables, hasDownArrow=True)
        bc.dataRpc(
            '.sync_done', self.setSyncInfo,
            insync_table='^.sync_table',
            instore_secondary='^.store_secondary',
            instate='tables',
            _if='insync_table && instore_secondary',
            _onResult='FIRE .build_th; FIRE .load_th;')

        body = bc.borderContainer(region='center')

        # Primary pane (rootstore)
        primary = body.framePane(margin='3px', border='1px solid silver',
                                 rounded=6, region='left', width='50%')
        primary.top.slotToolbar('5,store_lbl,*', height='23px') \
            .store_lbl.div('Primary (rootstore)',
                           font_weight='bold', color='#666')
        primary.center.contentPane(margin='5px', overflow='hidden') \
            .dynamicTableHandler(
                table='=main.tables.sync_table',
                datapath='main.dbroot_primary',
                th_wdg='plain',
                th_viewResource='View',
                th_configurable=True,
                th_view_store_applymethod='checksync_primary',
                th_view_store_state='tables',
                th_view_store_onStart=True,
                th_grid_onDrag="dragValues['tbl_from_primary']=dragValues.gridrow.rowset;",
                th_grid_dropTarget_grid='tbl_from_secondary',
                th_grid_onDrop_tbl_from_secondary='genro.publish("tbl_drop_primary",{data:data});',
                th_grid_selectedId='main.tables.selected_pkey_primary',
                th_view_store__fired='^main.tables.load_th',
                nodeId='tables_primary_th',
                _fired='^main.tables.build_th')
        primary.bottom.slotToolbar('*,prop_btn,5', height='28px') \
            .prop_btn.button('!!Propagate to all stores',
                             publish='tables_propagate_all',
                             disabled='^main.tables.selected_pkey_primary?=!#v')

        # Secondary pane (chosen secondary store)
        sec_store = '=main.tables.store_secondary'
        secondary = body.framePane(margin='3px', border='1px solid silver',
                                   rounded=6, region='center')
        secondary.top.slotToolbar('5,store_lbl,*', height='23px') \
            .store_lbl.div("==s||'(no secondary store)'",
                           s='^main.tables.store_secondary',
                           font_weight='bold', color='#666')
        secondary.center.contentPane(margin='5px', overflow='hidden') \
            .dynamicTableHandler(
                table='=main.tables.sync_table',
                datapath='main.dbroot_secondary',
                th_wdg='plain',
                th_viewResource='View',
                th_configurable=True,
                th_view_store_applymethod='checksync_secondary',
                th_view_store_state='tables',
                th_view_store_currentDbstore=sec_store,
                th_view_store_forced_dbstore=True,
                th_dbstore=sec_store,
                th_view_store_onStart=True,
                th_grid_onDrag="dragValues['tbl_from_secondary']=dragValues.gridrow.rowset;",
                th_grid_dropTarget_grid='tbl_from_primary',
                th_grid_onDrop_tbl_from_primary='genro.publish("tbl_drop_secondary",{data:data});',
                th_view_store__fired='^main.tables.load_th',
                nodeId='tables_secondary_th',
                _fired='^main.tables.build_th')

        # Propagate-to-all RPC (button is in primary.bottom toolbar)
        body.dataRpc(
            'dummy', self.propagateToAllStores,
            subscribe_tables_propagate_all=True,
            table='=main.tables.sync_table',
            pkey='=main.tables.selected_pkey_primary',
            _if='table && pkey',
            _onResult='FIRE main.tables.load_th; '
                      'genro.dlg.alert("Done","Propagated to all stores");',
            _lockScreen=True, timeout=0,
            _ask=dict(title='!!Propagate to all stores',
                      fields=[dict(name='update_existing', tag='checkbox',
                                   label='!!Update if row already exists '
                                         '(unchecked = only add where missing)',
                                   value=False)]))

        # Drop RPCs: rows dropped on primary came from secondary, and vice-versa
        oncalling = ("var pkeys = [];"
                     "data.forEach(function(n){pkeys.push(n._pkey);});"
                     "if(!pkeys.length){return false;}"
                     "kwargs['pkeys'] = pkeys.join(',');"
                     "objectPop(kwargs,'data');")
        body.dataRpc(
            'dummy', self.copyRows,
            subscribe_tbl_drop_primary=True,
            store_from='=main.tables.store_secondary', store_to=False,
            table='=main.tables.sync_table',
            _onCalling=oncalling,
            _onResult='FIRE main.tables.load_th;',
            _lockScreen=True, timeout=0)
        body.dataRpc(
            'dummy', self.copyRows,
            subscribe_tbl_drop_secondary=True,
            store_from=False, store_to='=main.tables.store_secondary',
            table='=main.tables.sync_table',
            _onCalling=oncalling,
            _onResult='FIRE main.tables.load_th;',
            _lockScreen=True, timeout=0)

    # ------------------------------------------------------------------
    # Tab "User Objects"
    # ------------------------------------------------------------------

    def _buildUserObjectsTab(self, bc):
        # Toolbar: pick secondary store + table filter + objtype filter
        bar = bc.contentPane(region='top').slotToolbar('5,sel,*', height='34px')
        fb = bar.sel.formbuilder(cols=4, border_spacing='3px')
        fb.filteringSelect(value='^.store_secondary', lbl='Secondary',
                           width='12em', values=self._storeOptions())
        fb.remoteSelect(value='^.uo_tbl', lbl='Table', width='18em',
                        method=self.getUserObjectTables, hasDownArrow=True)
        fb.remoteSelect(value='^.uo_objtype', lbl='Type', width='12em',
                        method=self.getUserObjectTypes,
                        condition_uo_tbl='=.uo_tbl',
                        hasDownArrow=True)
        bc.dataController('SET .uo_objtype = null;', _trigger='^.uo_tbl')
        bc.dataRpc(
            '.sync_done', self.setSyncInfo,
            insync_table=self.USEROBJECT_TABLE,
            instore_secondary='^.store_secondary',
            where='$tbl=:c_tbl AND ($objtype=:c_objtype OR :c_objtype IS NULL)',
            c_tbl='^.uo_tbl',
            c_objtype='^.uo_objtype',
            instate='userobjects',
            _if='instore_secondary && c_tbl',
            _onResult='FIRE .load_th;')

        body = bc.borderContainer(region='center')
        condition = '$tbl=:c_tbl AND ($objtype=:c_objtype OR :c_objtype IS NULL)'

        # Primary pane (rootstore)
        primary = body.framePane(margin='3px', border='1px solid silver',
                                 rounded=6, region='left', width='50%')
        primary.top.slotToolbar('5,store_lbl,*', height='23px') \
            .store_lbl.div('Primary (rootstore)',
                           font_weight='bold', color='#666')
        primary.center.contentPane(margin='5px', overflow='hidden') \
            .plainTableHandler(
                table=self.USEROBJECT_TABLE,
                viewResource='ViewMultidomain',
                configurable=True,
                condition=condition,
                condition_c_tbl='^main.userobjects.uo_tbl',
                condition_c_objtype='^main.userobjects.uo_objtype',
                view_store_applymethod='checksync_primary',
                view_store_state='userobjects',
                view_store_onStart=True,
                view_store__fired='^main.userobjects.load_th',
                grid_onDrag="dragValues['uo_from_primary']=dragValues.gridrow.rowset;",
                grid_dropTarget_grid='uo_from_secondary',
                grid_onDrop_uo_from_secondary='genro.publish("uo_drop_primary",{data:data});',
                nodeId='userobjects_primary_th')
        primary.bottom.slotToolbar('*,prop_btn,5', height='28px') \
            .prop_btn.button('!!Propagate to all stores',
                             publish='userobjects_propagate_all',
                             disabled='^#userobjects_primary_th.view.grid.selectedId?=!#v')

        # Secondary pane (chosen secondary store)
        sec_store = '=main.userobjects.store_secondary'
        secondary = body.framePane(margin='3px', border='1px solid silver',
                                   rounded=6, region='center')
        secondary.top.slotToolbar('5,store_lbl,*', height='23px') \
            .store_lbl.div("==s||'(no secondary store)'",
                           s='^main.userobjects.store_secondary',
                           font_weight='bold', color='#666')
        secondary.center.contentPane(margin='5px', overflow='hidden') \
            .plainTableHandler(
                table=self.USEROBJECT_TABLE,
                viewResource='ViewMultidomain',
                configurable=True,
                condition=condition,
                condition_c_tbl='^main.userobjects.uo_tbl',
                condition_c_objtype='^main.userobjects.uo_objtype',
                view_store_applymethod='checksync_secondary',
                view_store_state='userobjects',
                view_store_currentDbstore=sec_store,
                view_store_forced_dbstore=True,
                dbstore=sec_store,
                view_store_onStart=True,
                view_store__fired='^main.userobjects.load_th',
                grid_onDrag="dragValues['uo_from_secondary']=dragValues.gridrow.rowset;",
                grid_dropTarget_grid='uo_from_primary',
                grid_onDrop_uo_from_primary='genro.publish("uo_drop_secondary",{data:data});',
                nodeId='userobjects_secondary_th')

        # Propagate-to-all RPC (button is in primary.bottom toolbar)
        body.dataRpc(
            'dummy', self.propagateToAllStores,
            subscribe_userobjects_propagate_all=True,
            table=self.USEROBJECT_TABLE,
            pkey='=#userobjects_primary_th.view.grid.selectedId',
            _if='pkey',
            _onResult='FIRE main.userobjects.load_th; '
                      'genro.dlg.alert("Done","Propagated to all stores");',
            _lockScreen=True, timeout=0,
            _ask=dict(title='!!Propagate to all stores',
                      fields=[dict(name='update_existing', tag='checkbox',
                                   label='!!Update if row already exists '
                                         '(unchecked = only add where missing)',
                                   value=False)]))

        # Drop RPCs
        oncalling = ("var pkeys = [];"
                     "data.forEach(function(n){pkeys.push(n._pkey);});"
                     "if(!pkeys.length){return false;}"
                     "kwargs['pkeys'] = pkeys.join(',');"
                     "objectPop(kwargs,'data');")
        body.dataRpc(
            'dummy', self.copyRows,
            subscribe_uo_drop_primary=True,
            store_from='=main.userobjects.store_secondary', store_to=False,
            table=self.USEROBJECT_TABLE,
            _onCalling=oncalling,
            _onResult='FIRE main.userobjects.load_th;',
            _lockScreen=True, timeout=0)
        body.dataRpc(
            'dummy', self.copyRows,
            subscribe_uo_drop_secondary=True,
            store_from=False, store_to='=main.userobjects.store_secondary',
            table=self.USEROBJECT_TABLE,
            _onCalling=oncalling,
            _onResult='FIRE main.userobjects.load_th;',
            _lockScreen=True, timeout=0)

    # ------------------------------------------------------------------
    # RPCs: selectors
    # ------------------------------------------------------------------

    @public_method
    def getPropagableTables(self, _querystring=None, _id=None, **kwargs):
        meta = dict(columns='tablename', headers='Table')
        result = Bag()
        if _id:
            result.setItem(_id.replace('.', '_'), None,
                           caption=_id, tablename=_id, _pkey=_id)
            return result, meta
        q = (_querystring or '').replace('*', '')
        whitelist = []
        storetable = self.db.storetable
        if storetable:
            storetbl = self.db.table(storetable)
            if hasattr(storetbl, 'multidb_setStartupData_whitelist'):
                whitelist = storetbl.multidb_setStartupData_whitelist() or []
        for pkgobj in self.db.packages.values():
            for tableobj in pkgobj.tables.values():
                tablename = tableobj.fullname
                if q and q not in tablename:
                    continue
                tbl = self.db.table(tablename)
                if not (tableobj.attributes.get('multidb') == '*'
                        or tbl.isInStartupData()
                        or tablename in whitelist):
                    continue
                result.setItem(tablename.replace('.', '_'), None,
                               caption=tablename, tablename=tablename,
                               _pkey=tablename)
        return result, meta

    @public_method
    def getUserObjectTables(self, _querystring=None, _id=None, **kwargs):
        return self._distinctUserObjectColumn('tbl', _querystring, _id)

    @public_method
    def getUserObjectTypes(self, _querystring=None, _id=None,
                           uo_tbl=None, **kwargs):
        return self._distinctUserObjectColumn(
            'objtype', _querystring, _id,
            where='$tbl=:t' if uo_tbl else None, t=uo_tbl)

    def _distinctUserObjectColumn(self, column, querystring, _id,
                                  where=None, **whereargs):
        result = Bag()
        with self.db.tempEnv(storename=False):
            q = self.db.table(self.USEROBJECT_TABLE).query(
                columns='$%s' % column, distinct=True,
                where=where, order_by='$%s' % column, **whereargs)
            values = [r[column] for r in q.fetch() if r[column]]
        qs = (querystring or '').replace('*', '')
        for v in values:
            if _id and v != _id:
                continue
            if qs and qs not in v:
                continue
            result.setItem(v.replace('.', '_'), None,
                           caption=v, _pkey=v, **{column: v})
        return result, dict(columns=column, headers=column.title())

    # ------------------------------------------------------------------
    # RPCs: diff / sync state
    # ------------------------------------------------------------------

    @public_method
    def checksync_primary(self, selection=None, state=None, **kwargs):
        self._applyDiff(selection, 'primary', state)

    @public_method
    def checksync_secondary(self, selection=None, state=None, **kwargs):
        self._applyDiff(selection, 'secondary', state)

    def _applyDiff(self, selection, side, state):
        diff = self.pageStore().getItem('diff_%s' % (state or 'default')) or {}

        def cb(row):
            v = diff.get(row['pkey'])
            if not v or v == 'equal':
                return dict()
            if side == 'primary':
                if v == 'onlymain':
                    return dict(_customClasses='toprop')
                if v == 'diff':
                    return dict(_customClasses='diff')
                return dict()
            if v == 'onlystore':
                return dict(_customClasses='localonly')
            if v == 'diff':
                return dict(_customClasses='diff')
            return dict()

        selection.apply(cb)
        selection.sort('pkey')

    @public_method
    def setSyncInfo(self, insync_table=None, instore_secondary=None,
                    where=None, instate=None, **whereargs):
        tbl = self.db.table(insync_table)
        pkey = tbl.pkey
        qa = dict(addPkeyColumn=False, bagFields=True,
                  excludeLogicalDeleted=False)
        if tbl.attributes.get('hierarchical'):
            qa.setdefault('order_by', '$hierarchical_pkey')
        if where:
            qa['where'] = where
            qa.update({k: v for k, v in whereargs.items()
                       if not k.startswith('_')})

        with self.db.tempEnv(storename=False):
            primary_f = tbl.query(**qa).fetchAsDict()
        with self.db.tempEnv(storename=instore_secondary):
            secondary_f = tbl.query(**qa).fetch()

        diff = self._buildDiff(secondary_f, primary_f, pkey)
        with self.pageStore() as store:
            store.setItem('diff_%s' % (instate or 'default'), diff)
        return True

    def _buildDiff(self, dest_rows, source_dict, pkey):
        result = {}
        for r in dest_rows:
            r = self._stripMeta(r)
            mr = source_dict.pop(r[pkey], None)
            if mr is None:
                result[r[pkey]] = 'onlystore'
                continue
            result[r[pkey]] = 'equal' if self._stripMeta(mr) == r else 'diff'
        for k in source_dict:
            result[k] = 'onlymain'
        return result

    @staticmethod
    def _stripMeta(record):
        out = dict(record)
        for k in ('__ins_ts', '__mod_ts', '__version', '__del_ts',
                  '__moved_related'):
            out.pop(k, None)
        return out

    # ------------------------------------------------------------------
    # RPCs: row movement
    # ------------------------------------------------------------------

    @public_method
    def copyRows(self, table=None, store_from=None, store_to=None,
                 pkeys=None, **kwargs):
        pkey_list = (pkeys.split(',') if isinstance(pkeys, str)
                     else list(pkeys or []))
        if not (table and pkey_list) or store_from == store_to:
            return
        tbl = self.db.table(table)
        pkey = tbl.pkey
        with self.db.tempEnv(storename=store_from):
            rows = tbl.query(addPkeyColumn=False, bagFields=True,
                             excludeLogicalDeleted=False,
                             where='$%s IN :pk' % pkey, pk=pkey_list).fetch()
        if not rows:
            return
        with self.db.tempEnv(storename=store_to):
            for r in rows:
                tbl.insertOrUpdate(dict(r))
            self.db.commit()

    @public_method
    def propagateToAllStores(self, table=None, pkey=None,
                             update_existing=True, **kwargs):
        if not (table and pkey):
            return
        tbl = self.db.table(table)
        with self.db.tempEnv(storename=False):
            rows = tbl.query(addPkeyColumn=False, bagFields=True,
                             excludeLogicalDeleted=False,
                             where='$%s=:pk' % tbl.pkey, pk=pkey).fetch()
        if not rows:
            return
        record = dict(rows[0])
        for storename in self.db.stores_handler.dbstores.keys():
            with self.db.tempEnv(storename=storename):
                self._propagateOne(tbl, record, update_existing)

    def _propagateOne(self, tbl, record, update_existing):
        existing = tbl.query(addPkeyColumn=False, bagFields=True,
                             excludeLogicalDeleted=False,
                             where='$%s=:pk' % tbl.pkey,
                             pk=record[tbl.pkey]).fetch()
        if not existing:
            tbl.raw_insert(dict(record))
        elif update_existing:
            tbl.raw_update(record=dict(record), old_record=dict(existing[0]))
        self.db.commit()
