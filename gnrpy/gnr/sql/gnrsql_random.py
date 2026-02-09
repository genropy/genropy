# -*- coding: utf-8 -*-
#
# gnrsql_random.py
# Random record generation for GnrSqlTable.
#
# Extracted from resources/common/tables/_default/action/_common/random_records.py
# to make the logic available without web dependencies.

from datetime import datetime, time, date
import string
import random

from gnr.core.gnrdict import dictExtract
from gnr.core.gnrnumber import decimalRound


class RandomRecordGenerator:

    def __init__(self, tblobj, config=None):
        self.tblobj = tblobj
        self.db = tblobj.db
        self.config = config or dict()

    def generate(self, how_many, fields=None, seed=None, batch_prefix='RND'):
        if seed is not None:
            random.seed(seed)
        if fields is None:
            fields = self._buildFieldsConfig()
        self._preProcessValues(how_many, fields)
        for i in range(how_many):
            record = dict()
            for field, field_pars in list(fields.items()):
                condition_field = field_pars.get('_if')
                null_perc = field_pars.get('null_perc')
                if not condition_field or self._checkCondition(record, condition_field):
                    if not null_perc or random.randint(1, 100) > null_perc:
                        if field not in record:
                            self._setRecordField(record, field, field_pars, i,
                                                 batch_prefix=batch_prefix)
            self.tblobj.insert(record)
        self.db.commit()

    def _buildFieldsConfig(self):
        fields = dict()
        random_values_dict = dict()
        if hasattr(self.tblobj, 'randomValues'):
            random_values_dict = self.tblobj.randomValues()
        for col_name, col_config in self.config.items():
            if isinstance(col_config, dict):
                random_values_dict.setdefault(col_name, dict()).update(col_config)
            else:
                random_values_dict[col_name] = col_config
        for col_name, col in list(self.tblobj.columns.items()):
            attr = col.attributes
            dtype = attr.get('dtype')
            if col_name not in random_values_dict and (attr.get('_sysfield') or dtype == 'X'):
                continue
            col_rules = random_values_dict.get(col_name, dict())
            if col_rules is False:
                continue
            col_rules = dict(col_rules) if isinstance(col_rules, dict) else dict()
            if attr.get('size'):
                col_rules['size'] = attr.get('size')
            col_rules['dtype'] = dtype
            fields[col_name] = col_rules
        return fields

    def _checkCondition(self, r, condition_field):
        if condition_field.startswith('!'):
            return not r.get(condition_field[1:])
        else:
            return r.get(condition_field)

    def _setRecordField(self, r, field, field_pars, i, batch_prefix='RND'):
        if 'equal_to' in field_pars:
            r[field] = r[field_pars['equal_to']]
            return

        if field_pars.get('values'):
            r[field] = field_pars['values'][i]
            if 'copied_values' in field_pars:
                copied_values = field_pars['copied_values'][r[field]]
                for k, v in copied_values:
                    r[k] = v
            return

        if field_pars.get('allowed_records'):
            based_on_key = r[field_pars['based_on']]
            if based_on_key in field_pars['allowed_records']:
                allowed_records = field_pars['allowed_records'][based_on_key]
                rnd_record = random.choice(allowed_records)
                r[field] = rnd_record[field_pars['from_column']]
                if 'copy_columns' in field_pars:
                    for k in list(field_pars.get('copy_columns').keys()):
                        r[k] = rnd_record.get(k)
            return

        if not self.tblobj.columns[field].relatedTable():
            dtype = field_pars.get('dtype')

            if dtype == 'B':
                r[field] = random.randint(1, 100) <= field_pars.get('true_value', 50)
                return

            if dtype in ('T', 'A'):
                value = None
                if field_pars.get('default_value'):
                    value = field_pars['default_value']
                    if '#P' in value:
                        value = value.replace('#P', batch_prefix)
                    if '#N' in value:
                        value = value.replace('#N', str(i + 1))
                if field_pars.get('random_value'):
                    value = self._randomTextValue(
                        n_words=field_pars.get('n_words'),
                        w_length=field_pars.get('w_length'))
                if value and field_pars.get('size'):
                    size_str = field_pars['size']
                    if ':' in size_str:
                        l_max = int(size_str.split(':')[1])
                    else:
                        l_max = int(size_str)
                    if len(value) > l_max:
                        value = value[:l_max]
                r[field] = value
                return

            if 'range' in field_pars:
                r[field] = self._getValueFromRange(r, field_pars, dtype)
                return

            min_value = field_pars.get('min_value') if 'greater_than' not in field_pars else r[field_pars['greater_than']]
            max_value = field_pars.get('max_value') if 'less_than' not in field_pars else r[field_pars['less_than']]
            if min_value is not None and max_value is not None:
                rnd_value = self._randomValue(
                    self._convertToNumber(min_value, dtype),
                    self._convertToNumber(max_value, dtype),
                    dtype)
                r[field] = self._convertFromNumber(rnd_value, dtype)

    def _convertToNumber(self, v, dtype):
        if dtype == 'H':
            return v.hour * 60 + v.minute
        elif dtype == 'D':
            return v.toordinal()
        elif dtype == 'DH':
            return int(v.strftime('%s')) // 60
        elif dtype == 'N':
            return float(v)
        return v

    def _convertFromNumber(self, v, dtype):
        if dtype == 'H':
            return time(int(v / 60), v % 60)
        if dtype == 'D':
            return date.fromordinal(v)
        if dtype == 'DH':
            return datetime.fromtimestamp(v * 60.0)
        if dtype == 'N':
            return decimalRound(v, 2)
        return v

    def _randomValue(self, v_min, v_max, dtype):
        if dtype in ('I', 'L', 'H', 'D', 'DH'):
            return random.randint(int(min(v_min, v_max)), int(max(v_min, v_max)))
        else:
            return random.uniform(min(v_min, v_max), max(v_min, v_max))

    def _randomTextValue(self, n_words=None, w_length=None):
        n_words = n_words or '2:5'
        w_length = w_length or '4:12'
        min_wlen, max_wlen = w_length.split(':')
        min_wlen = int(min_wlen.strip())
        max_wlen = int(max_wlen.strip())
        if ':' in str(n_words):
            words_min, words_max = str(n_words).split(':')
            words_min = int(words_min.strip())
            words_max = int(words_max.strip())
            n_words = random.randint(words_min, words_max)
        else:
            n_words = int(str(n_words).strip())
        words_list = []
        for x in range(n_words):
            wd = ''.join(random.choice(string.ascii_lowercase)
                         for _ in range(random.randint(min_wlen, max_wlen)))
            words_list.append(wd)
        words_list[0] = words_list[0].capitalize()
        return ' '.join(words_list)

    def _getValueFromRange(self, record, field_pars, dtype):
        if field_pars.get('greater_than'):
            sign = 1
            v_base = record[field_pars['greater_than']]
        else:
            sign = -1
            v_base = record[field_pars['less_than']]
        v_base = self._convertToNumber(v_base, dtype)
        range_str = field_pars['range']
        if ':' in range_str:
            r_min, r_max = range_str.split(':')
        else:
            r_min, r_max = '0', range_str
        if '%' in r_min:
            v_min = v_base * (float(r_min.replace('%', '')) / 100)
        else:
            v_min = float(r_min)
        if '%' in r_max:
            v_max = v_base * (float(r_max.replace('%', '')) / 100)
        else:
            v_max = float(r_max)
        rnd_value = v_base + sign * self._randomValue(v_min, v_max, dtype)
        return self._convertFromNumber(rnd_value, dtype)

    def _getDatesList(self, how_many, dtype, min_value, max_value):
        v_min = self._convertToNumber(min_value, dtype)
        v_max = self._convertToNumber(max_value, dtype)
        return [self._convertFromNumber(self._randomValue(v_min, v_max, dtype), dtype)
                for x in range(how_many)]

    def _getNumbersList(self, how_many, dtype, min_value, max_value):
        return [self._randomValue(min_value, max_value, dtype)
                for x in range(how_many)]

    def _preProcessValues(self, how_many, fields):
        for field, field_pars in list(fields.items()):
            if 'equal_to' in field_pars:
                continue

            dtype = field_pars.get('dtype')
            if dtype in ('D', 'DH'):
                if 'greater_than' in field_pars or 'less_than' in field_pars:
                    continue
                min_val = field_pars.get('min_value')
                max_val = field_pars.get('max_value')
                if min_val and max_val:
                    field_pars['values'] = self._getDatesList(how_many, dtype, min_val, max_val)
                    if field_pars.get('sorted'):
                        field_pars['values'].sort()
                continue

            if dtype in ('I', 'L', 'N') and field_pars.get('sorted'):
                min_val = field_pars.get('min_value')
                max_val = field_pars.get('max_value')
                if min_val is not None and max_val is not None:
                    values = self._getNumbersList(how_many, dtype, min_val, max_val)
                    values.sort()
                    field_pars['values'] = values
                continue

            related_tbl = self.tblobj.columns[field].relatedTable()
            if not related_tbl:
                continue

            related_tbl = related_tbl.dbtable

            if 'based_on' in field_pars:
                based_on_field = field_pars['based_on']
                based_on_pkeys = fields[based_on_field]['distinct_pkeys']
                from_table = field_pars.get('from_table')
                from_tbl_obj = self.db.table(field_pars['from_table']) if from_table else related_tbl
                from_column = field_pars.get('from_column') or from_tbl_obj.pkey
                field_pars['from_column'] = from_column
                where = '$%s IN :based_on_pkeys' % based_on_field
                if 'condition' in field_pars:
                    where = '%s AND %s' % (where, field_pars['condition'])
                columns = '*'
                query = from_tbl_obj.query(columns=columns, where=where,
                                           based_on_pkeys=based_on_pkeys)
                field_pars['allowed_records'] = query.fetchGrouped(key=based_on_field)
                field_pars['distinct_pkeys'] = set(query.fetchPkeys())
                continue

            where_pars = dictExtract(field_pars, 'condition_')
            where = field_pars.get('condition')
            pkeys_str = field_pars.get('pkeys')
            if not pkeys_str:
                pkeys = related_tbl.query(
                    columns='$%s' % related_tbl.pkey,
                    where=where, **where_pars).fetchPkeys()
            else:
                pkeys = pkeys_str.split(',')
            if pkeys:
                field_pars['values'] = [random.choice(pkeys) for x in range(how_many)]
                field_pars['distinct_pkeys'] = set(field_pars['values'])
                if 'copy_columns' in field_pars:
                    columns_list = ['%s AS %s' % (v, k)
                                    for k, v in list(field_pars.get('copy_columns').items())]
                    field_pars['copied_values'] = related_tbl.query(
                        columns='.'.join(columns_list),
                        where='$%s IN :pkeys' % related_tbl.pkey,
                        pkeys=field_pars['distinct_pkeys']).fetchAsDict(key=related_tbl.pkey)
