#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Surface tests for SqlSelection public API.
Tests output modes, sort, filter, apply, insert, append, sum, extend,
len, iter, newRow, getByKey, allColumns, keyDict properties.
"""

from gnr.sql.gnrsql import GnrSqlDb
from gnr.core.gnrbag import Bag
from gnr.sql.gnrsql_exceptions import SelectionExecutionError

import pytest

from .common import BaseGnrSqlTest, configureDb


class BaseSelectionSurface(BaseGnrSqlTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.init()
        cls.db.createDb(cls.dbname)
        configureDb(cls.db)
        cls.db.startup()
        cls.db.checkDb(applyChanges=True)
        cls.db.importXmlData(cls.SAMPLE_XMLDATA)
        cls.db.commit()

    @classmethod
    def teardown_class(cls):
        cls.db.closeConnection()
        cls.db.dropDb(cls.dbname)

    def _make_sel(self, **kwargs):
        defaults = dict(
            columns='$id,$title,$year,$nationality',
            order_by='$id',
        )
        defaults.update(kwargs)
        return self.db.query('video.movie', **defaults).selection()

    # --- output modes ---

    def test_output_list(self):
        sel = self._make_sel()
        result = sel.output('list')
        assert isinstance(result, list)
        assert isinstance(result[0], list)

    def test_output_dictlist(self):
        sel = self._make_sel()
        result = sel.output('dictlist')
        assert isinstance(result, list)
        assert isinstance(result[0], dict)
        assert 'title' in result[0]

    def test_output_pkeylist(self):
        sel = self._make_sel()
        result = sel.output('pkeylist')
        assert isinstance(result, list)
        assert len(result) == 11

    def test_output_json(self):
        sel = self._make_sel()
        result = sel.output('json')
        assert isinstance(result, str)
        import json
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert isinstance(parsed[0], dict)

    def test_output_bag(self):
        sel = self._make_sel()
        result = sel.output('bag')
        assert isinstance(result, Bag)
        assert 'headers' in result
        assert 'rows' in result

    def test_output_selection(self):
        sel = self._make_sel()
        result = sel.output('selection')
        assert isinstance(result, Bag)

    def test_output_grid(self):
        sel = self._make_sel()
        result = sel.output('grid')
        assert isinstance(result, Bag)

    def test_output_count(self):
        sel = self._make_sel()
        result = sel.output('count')
        assert result == 11

    def test_output_distinct(self):
        sel = self._make_sel(columns='$nationality')
        result = sel.output('distinct')
        assert isinstance(result, set)

    def test_output_data(self):
        sel = self._make_sel()
        result = sel.output('data')
        assert isinstance(result, list)

    def test_output_template(self):
        sel = self._make_sel(columns='$title', where='$id=:id', sqlparams={'id': 0})
        result = sel.output('template', rowtemplate='Film: $title')
        assert 'Match point' in result

    def test_output_invalid_mode(self):
        sel = self._make_sel()
        with pytest.raises(SelectionExecutionError):
            sel.output('nonexistent_mode')

    def test_output_with_offset_limit(self):
        sel = self._make_sel()
        result = sel.output('list', offset=2, limit=3)
        assert len(result) == 3

    def test_output_with_filterCb(self):
        sel = self._make_sel()
        result = sel.output('dictlist', filterCb=lambda r: r['year'] == 2005)
        assert all(r['year'] == 2005 for r in result)

    def test_output_with_columns_subset(self):
        sel = self._make_sel()
        result = sel.output('dictlist', columns='title,year')
        assert 'title' in result[0]
        assert 'nationality' not in result[0]

    # --- len / iter ---

    def test_len(self):
        sel = self._make_sel()
        assert len(sel) == 11

    def test_iter(self):
        sel = self._make_sel()
        items = list(sel)
        assert len(items) == 11

    # --- allColumns / keyDict / getByKey ---

    def test_allColumns(self):
        sel = self._make_sel()
        cols = sel.allColumns
        assert 'title' in cols
        assert 'year' in cols

    def test_keyDict(self):
        sel = self._make_sel()
        kd = sel.keyDict
        assert isinstance(kd, dict)
        assert len(kd) == 11

    def test_getByKey(self):
        sel = self._make_sel()
        pkeys = sel.output('pkeylist')
        row = sel.getByKey(pkeys[0])
        assert row['title'] is not None

    # --- sort ---

    def test_sort_ascending(self):
        sel = self._make_sel()
        sel.sort('year')
        result = sel.output('dictlist')
        years = [r['year'] for r in result]
        assert years == sorted(years)

    def test_sort_descending(self):
        sel = self._make_sel()
        sel.sort('year:d')
        result = sel.output('dictlist')
        years = [r['year'] for r in result]
        assert years == sorted(years, reverse=True)

    def test_sort_multiple(self):
        sel = self._make_sel()
        sel.sort('nationality', 'year')
        result = sel.output('dictlist')
        assert len(result) == 11

    # --- filter ---

    def test_filter_apply_and_clear(self):
        sel = self._make_sel()
        sel.filter(lambda r: r['year'] == 2005)
        assert len(sel) == 2
        sel.filter()
        assert len(sel) == 11

    # --- newRow / insert / append ---

    def test_newRow(self):
        sel = self._make_sel()
        row = sel.newRow({'title': 'Test Film', 'year': 2020})
        assert row['title'] == 'Test Film'

    def test_append(self):
        sel = self._make_sel()
        original_len = len(sel)
        sel.append({'title': 'New Film', 'year': 2025, 'id': 9999})
        assert len(sel) == original_len + 1

    def test_insert(self):
        sel = self._make_sel()
        original_len = len(sel)
        sel.insert(0, {'title': 'First Film', 'year': 1900, 'id': 9998})
        assert len(sel) == original_len + 1
        result = sel.output('dictlist')
        assert result[0]['title'] == 'First Film'

    # --- apply ---

    def test_apply_update(self):
        sel = self._make_sel(where='$id=:id', sqlparams={'id': 0})
        sel.apply(lambda r: {'year': 9999})
        result = sel.output('dictlist')
        assert result[0]['year'] == 9999

    # --- sum ---

    def test_sum_columns(self):
        sel = self._make_sel()
        result = sel.sum(columns='year')
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] > 0

    def test_sum_empty(self):
        sel = self._make_sel()
        result = sel.sum(columns=None)
        assert result == []

    # --- extend ---

    def test_extend(self):
        sel1 = self._make_sel(where='$year=:y', sqlparams={'y': 2005})
        sel2 = self._make_sel(where='$year=:y', sqlparams={'y': 2006})
        len1 = len(sel1)
        len2 = len(sel2)
        sel1.extend(sel2)
        assert len(sel1) == len1 + len2

    # --- output recordlist ---

    def test_output_recordlist(self):
        sel = self._make_sel(where='$id=:id', sqlparams={'id': 0})
        result = sel.output('recordlist')
        assert isinstance(result, Bag)
        assert len(result) >= 1

    # --- output baglist ---

    def test_output_baglist(self):
        sel = self._make_sel(where='$id=:id', sqlparams={'id': 0})
        result = sel.output('baglist')
        assert isinstance(result, Bag)
        assert len(result) >= 1

    def test_output_baglist_labelIsPkey(self):
        sel = self._make_sel(where='$id=:id', sqlparams={'id': 0})
        result = sel.output('baglist', labelIsPkey=True)
        assert isinstance(result, Bag)

    # --- output fullgrid ---

    def test_output_fullgrid(self):
        sel = self._make_sel()
        result = sel.output('fullgrid')
        assert isinstance(result, Bag)
        assert 'structure' in result
        assert 'data' in result

    # --- output bag with recordResolver ---

    def test_output_bag_with_recordResolver(self):
        sel = self._make_sel(where='$id=:id', sqlparams={'id': 0})
        result = sel.output('bag', recordResolver=True)
        assert isinstance(result, Bag)
        assert 'rows' in result

    # --- output distinctColumns ---

    def test_output_distinctColumns(self):
        sel = self._make_sel(columns='$nationality')
        result = sel.output('distinctColumns')
        assert isinstance(result, list)

    # --- output generator ---

    def test_output_generator(self):
        sel = self._make_sel()
        result = sel.output('generator')
        items = list(result)
        assert len(items) == 11

    # --- output listItems ---

    def test_output_listItems(self):
        sel = self._make_sel()
        result = sel.output('listItems')
        items = list(result)
        assert len(items) == 11

    # --- iter modes ---

    def test_iter_data(self):
        sel = self._make_sel()
        result = sel.output('data')
        assert isinstance(result, list)

    def test_iter_dictlist(self):
        sel = self._make_sel()
        gen = sel.output('dictlist', asIterator=True)
        items = list(gen)
        assert len(items) == 11
        assert isinstance(items[0], dict)

    def test_iter_pkeylist(self):
        sel = self._make_sel()
        gen = sel.output('pkeylist', asIterator=True)
        items = list(gen)
        assert len(items) == 11

    def test_iter_records(self):
        sel = self._make_sel(where='$id=:id', sqlparams={'id': 0})
        gen = sel.output('records', asIterator=True)
        items = list(gen)
        assert len(items) == 1

    # --- output records ---

    def test_output_records(self):
        sel = self._make_sel(where='$id=:id', sqlparams={'id': 0})
        result = sel.output('records')
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], Bag)

    # --- freeze / frozenSelection ---

    def test_freeze_and_thaw(self):
        import os
        import tempfile
        sel = self._make_sel()
        freeze_dir = tempfile.mkdtemp(prefix='gnr_test_freeze_')
        freeze_path = os.path.join(freeze_dir, 'test_sel')
        sel.freeze(freeze_path)
        assert os.path.exists(freeze_path + '.pik')

        thawed = self.db.table('video.movie').frozenSelection(freeze_path)
        assert len(thawed) == len(sel)
        assert thawed.output('pkeylist') == sel.output('pkeylist')

        # cleanup
        for f in os.listdir(freeze_dir):
            os.remove(os.path.join(freeze_dir, f))
        os.rmdir(freeze_dir)

    def test_freeze_with_autocreate(self):
        import os
        import tempfile
        sel = self._make_sel()
        base_dir = tempfile.mkdtemp(prefix='gnr_test_freeze_')
        freeze_path = os.path.join(base_dir, 'subdir', 'test_sel')
        sel.freeze(freeze_path, autocreate=True)
        assert os.path.exists(freeze_path + '.pik')

        # cleanup
        parent = os.path.dirname(freeze_path)
        for f in os.listdir(parent):
            os.remove(os.path.join(parent, f))
        os.rmdir(parent)
        os.rmdir(base_dir)

    def test_freeze_with_pkeys(self):
        import os
        import tempfile
        sel = self._make_sel()
        freeze_dir = tempfile.mkdtemp(prefix='gnr_test_freeze_')
        freeze_path = os.path.join(freeze_dir, 'test_sel')
        sel.freeze(freeze_path, freezePkeys=True)
        assert os.path.exists(freeze_path + '_pkeys.pik')

        # cleanup
        for f in os.listdir(freeze_dir):
            os.remove(os.path.join(freeze_dir, f))
        os.rmdir(freeze_dir)

    def test_freezeUpdate(self):
        import os
        import tempfile
        sel = self._make_sel()
        freeze_dir = tempfile.mkdtemp(prefix='gnr_test_freeze_')
        freeze_path = os.path.join(freeze_dir, 'test_sel')
        sel.freeze(freeze_path)

        sel.apply(lambda r: {'year': 9999})
        sel.freezeUpdate()

        thawed = self.db.table('video.movie').frozenSelection(freeze_path)
        result = thawed.output('dictlist')
        assert all(r['year'] == 9999 for r in result)

        # cleanup
        for f in os.listdir(freeze_dir):
            os.remove(os.path.join(freeze_dir, f))
        os.rmdir(freeze_dir)

    # --- totalize ---

    def test_totalize(self):
        sel = self._make_sel()
        result = sel.totalize(group_by=['nationality'], sum=['year'])
        assert isinstance(result, Bag)

    def test_totalize_clear(self):
        sel = self._make_sel()
        sel.totalize(group_by=['nationality'], sum=['year'])
        result = sel.totalize(group_by=None)
        assert result is None

    def test_totalizer(self):
        sel = self._make_sel()
        sel.totalize(group_by=['nationality'], sum=['year'])
        result = sel.totalizer()
        assert isinstance(result, Bag)

    def test_totalizer_with_path(self):
        sel = self._make_sel()
        sel.totalize(group_by=['nationality'], sum=['year'])
        result = sel.totalizer()
        assert isinstance(result, Bag)
        assert len(result) > 0

    # --- toTextGen ---

    def test_output_with_formats(self):
        sel = self._make_sel(columns='$title,$year',
                             where='$id=:id', sqlparams={'id': 0})
        result = sel.output('list', formats={'title': '%s'})
        assert isinstance(result, list)

    # --- apply with removal ---

    def test_apply_remove(self):
        sel = self._make_sel()
        original_len = len(sel)
        sel.apply(lambda r: None if r['id'] == 0 else {'id': r['id']})
        assert len(sel) == original_len - 1

    # --- sort with comma-separated string ---

    def test_sort_comma_separated(self):
        sel = self._make_sel()
        sel.sort('nationality,year')
        result = sel.output('dictlist')
        assert len(result) == 11

    # --- sum with multiple columns ---

    def test_sum_multiple_columns(self):
        sel = self._make_sel()
        result = sel.sum(columns='year,id')
        assert isinstance(result, list)
        assert len(result) == 2

    # --- output selection with caption ---

    def test_output_selection_with_caption(self):
        sel = self._make_sel()
        result = sel.output('selection', caption=True)
        assert isinstance(result, Bag)

    # --- db property ---

    def test_db_property(self):
        sel = self._make_sel()
        assert sel.db is self.db


class TestSelectionSurface_sqlite(BaseSelectionSurface):
    @classmethod
    def init(cls):
        cls.name = 'sqlite'
        cls.dbname = cls.CONFIG['db.sqlite?filename']
        cls.db = GnrSqlDb(dbname=cls.dbname)


class TestSelectionSurface_postgres(BaseSelectionSurface):
    @classmethod
    def init(cls):
        cls.name = 'postgres'
        cls.dbname = 'test_sel_surface'
        cls.db = GnrSqlDb(implementation='postgres',
                          host=cls.pg_conf.get("host"),
                          port=cls.pg_conf.get("port"),
                          dbname=cls.dbname,
                          user=cls.pg_conf.get("user"),
                          password=cls.pg_conf.get("password"))
