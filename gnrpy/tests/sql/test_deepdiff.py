import os.path
from deepdiff import DeepDiff
import json


class TestDeepDiff(object):
    def setup_class(self):
        self.from_orm_json_file = os.path.join(os.path.dirname(__file__), "data/deepdiff_from_orm.json")
        self.from_sql_json_file = os.path.join(os.path.dirname(__file__), "data/deepdiff_from_sql.json")
        self.from_orm = json.load(open(self.from_orm_json_file))
        self.from_sql = json.load(open(self.from_sql_json_file))
        
    def test_known_payload(self):
        differ = DeepDiff(self.from_sql.keys(),
                          self.from_orm.keys(),
                          threshold_to_diff_deeper=0.0,
                          ignore_order=True)#, view='tree')

        assert len(differ['iterable_item_added']) == 1
        assert len(differ['iterable_item_removed']) == 7

