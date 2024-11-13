import os.environ
import os.path
from gnr.app import gnrutils as gu
import pytest

class TestGnrAppInsights(object):
    def test_dataset(self):
        g = gu.GnrAppInsightDataset("baba")
        assert g.app == "baba"
        assert not g.retrieve()

    def test_project_composition(self):
        c = gu.GnrAppInsightProjectComposition("gnrdevelop")

        # test ignore files
        count = c._count_lines_in_file("pippo.gz")
        assert count == 0

        # test over a predefined file length
        test_folder = os.path.join(os.path.dirname(__file__), "data")
        count = c._count_lines_in_file(os.path.join(test_folder, "test1.css"))
        assert count == 132


        test_folder = os.path.join(os.path.dirname(__file__), "data")
        count = c._count_lines_in_directory(test_folder)
        assert count == 264

    def test_app_insights(self):
        # FIXME: this can't be tested on github actions
        # due to missing GNR environment
        if "GITHUB_WORKFLOW" in os.environ:
            return
        
        # test an internal app        
        c = gu.GnrAppInsights("gnrdevelop")
        data = c.retrieve()
        assert data
        assert 'project_composition' in data
        for x in ['framework', 'extra_packages', 'project_packages']:
            assert x in data['project_composition']

        # non-existing insight
        with pytest.raises(Exception):
            gu.GnrAppInsights("gnrdevelop", "something")


        # existing insight
        c = gu.GnrAppInsights("gnrdevelop", "project_composition")
        data = c.retrieve()
        assert data

        # as bag
        b = c.retrieve(as_bag=True)
        assert "project_composition" in b

        
