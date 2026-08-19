import importlib.util
import os

from gnr.sql.gnrsql_exceptions import GnrSqlMissingColumn

TH_VIEW_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..',
                            'resources', 'common', 'th', 'th_view.py')


def load_th_view():
    spec = importlib.util.spec_from_file_location('th_view_under_test',
                                                  os.path.abspath(TH_VIEW_PATH))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeColumn:
    def __init__(self, required_columns=None):
        self.attributes = {}
        if required_columns:
            self.attributes['required_columns'] = required_columns


class FakeModel:
    """Mimics ModelTable.column(): resolves plain and @rel.col names,
    raises GnrSqlMissingColumn for unknown relation paths."""

    def __init__(self, columns=None, related=None):
        self.columns = columns or {}
        self.related = related or {}

    def column(self, name):
        if name.startswith('@'):
            if name in self.related:
                return self.related[name]
            raise GnrSqlMissingColumn(
                'relation %s does not exist in table fake' % name)
        return self.columns.get(name)


class FakeTable:
    def __init__(self, model):
        self.model = model


class TestThAddRequiredColumns:
    @classmethod
    def setup_class(cls):
        module = load_th_view()
        cls.view = module.TableHandlerView.__new__(module.TableHandlerView)

    def add_required(self, tblobj, hiddencolumns):
        return self.view._th_addRequiredColumns(tblobj, hiddencolumns)

    def test_empty_passthrough(self):
        tblobj = FakeTable(FakeModel())
        assert self.add_required(tblobj, None) is None
        assert self.add_required(tblobj, '') == ''

    def test_plain_columns_untouched(self):
        tblobj = FakeTable(FakeModel(columns={'id': FakeColumn(),
                                              'name': FakeColumn()}))
        assert self.add_required(tblobj, '$id, $name') == '$id,$name'

    def test_bare_name_untouched(self):
        tblobj = FakeTable(FakeModel())
        assert self.add_required(tblobj, '_h_count') == '_h_count'

    def test_required_columns_appended(self):
        model = FakeModel(columns={
            'id': FakeColumn(),
            'score': FakeColumn(required_columns='$account_name,$email')})
        assert self.add_required(FakeTable(model), '$id, $score') == \
            '$id,$score,$account_name,$email'

    def test_required_columns_deduplicated(self):
        model = FakeModel(columns={
            'score': FakeColumn(required_columns='$email'),
            'email': FakeColumn()})
        assert self.add_required(FakeTable(model), '$score, $email') == \
            '$score,$email'

    def test_alias_on_plain_column(self):
        model = FakeModel(columns={
            'score': FakeColumn(required_columns='$email')})
        assert self.add_required(FakeTable(model), '$score as sc') == \
            '$score as sc,$email'

    def test_relation_with_alias_does_not_raise(self):
        # the exact case of issue #702
        model = FakeModel(related={'@account_id.account_name': FakeColumn()})
        hidden = '$id, @account_id.account_name as account_name'
        assert self.add_required(FakeTable(model), hidden) == \
            '$id,@account_id.account_name as account_name'

    def test_relation_required_columns_rerooted(self):
        model = FakeModel(related={
            '@customer_id.score': FakeColumn(
                required_columns='$account_name,$email')})
        assert self.add_required(FakeTable(model), '@customer_id.score') == \
            '@customer_id.score,@customer_id.account_name,@customer_id.email'

    def test_unknown_relation_swallowed(self):
        model = FakeModel()
        hidden = '@nope.foo as bar, $id'
        assert self.add_required(FakeTable(model), hidden) == \
            '@nope.foo as bar,$id'

    def test_unknown_column_skipped(self):
        tblobj = FakeTable(FakeModel())
        assert self.add_required(tblobj, '$ghost') == '$ghost'
