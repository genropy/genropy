"""The ``--xpr`` option of ``gnr web serve``: experimental features from the command line.

``experimentalConfig`` turns the option string into an ``<experimental>`` Bag,
and ``GnrApp`` applies it through ``custom_config`` on top of
``instanceconfig.xml``. The application cases build a real ``GnrApp`` on a
temporary instance folder with its own ``instanceconfig.xml`` and a sqlite
database.
"""

import pytest

from gnr.app.gnrapp import GnrApp, experimentalConfig


INSTANCECONFIG = """<?xml version="1.0" ?>
<GenRoBag>
    <db implementation="sqlite" dbname="{dbname}"/>
    <packages>
        <gnrcore_sys pkgcode="gnrcore:sys"/>
        <gnrcore_adm pkgcode="gnrcore:adm"/>
    </packages>
    <experimental>
        <page no_mako="False" page_class_cache="True"/>
    </experimental>
</GenRoBag>
"""


@pytest.fixture
def instance_folder(tmp_path):
    (tmp_path / 'instanceconfig.xml').write_text(
        INSTANCECONFIG.format(dbname=tmp_path / 'xpr'))
    return str(tmp_path)


# ---------------------------------------------------------------------------
#  The option string
# ---------------------------------------------------------------------------

def test_switch_without_value_is_on():
    result = experimentalConfig('page.no_mako')
    assert result.getAttr('experimental.page') == {'no_mako': 'True'}


def test_switch_with_value():
    result = experimentalConfig('page.dojo_xhr_patch=fetch')
    assert result.getAttr('experimental.page') == {'dojo_xhr_patch': 'fetch'}


def test_several_groups_and_switches():
    result = experimentalConfig('page.no_mako,db.next_sql_compiler,page.page_class_cache')
    assert result.getAttr('experimental.page') == {'no_mako': 'True',
                                                   'page_class_cache': 'True'}
    assert result.getAttr('experimental.db') == {'next_sql_compiler': 'True'}


def test_brackets_and_spaces():
    result = experimentalConfig(' [page.no_mako, db.next_sql_compiler = True] ')
    assert result.getAttr('experimental.page') == {'no_mako': 'True'}
    assert result.getAttr('experimental.db') == {'next_sql_compiler': 'True'}


@pytest.mark.parametrize('xpr', ['no_mako', '.no_mako', 'page.', 'page.no_mako,,db.x', ''])
def test_item_without_group_and_name_raises(xpr):
    with pytest.raises(ValueError, match='group.name'):
        experimentalConfig(xpr)


# ---------------------------------------------------------------------------
#  The application
# ---------------------------------------------------------------------------

def test_instanceconfig_alone(instance_folder):
    app = GnrApp(instance_folder)
    assert app.experimentalFlag('page', 'no_mako') is False
    assert app.experimentalFlag('page', 'page_class_cache') is True
    assert app.experimentalFlag('db', 'next_sql_compiler') is False


def test_command_line_is_read_by_the_accessors(instance_folder):
    app = GnrApp(instance_folder, custom_config=experimentalConfig(
        'db.next_sql_compiler,page.dojo_xhr_patch=fetch'))
    assert app.experimentalFlag('db', 'next_sql_compiler') is True
    assert app.experimentalValue('page', 'dojo_xhr_patch') == 'fetch'


def test_command_line_wins_and_keeps_the_rest(instance_folder):
    """``no_mako`` is False in the file and True on the command line; the
    ``page_class_cache`` of the file is left as it is."""
    app = GnrApp(instance_folder, custom_config=experimentalConfig('page.no_mako'))
    assert app.experimentalFlag('page', 'no_mako') is True
    assert app.experimentalFlag('page', 'page_class_cache') is True
