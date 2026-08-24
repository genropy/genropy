#!/usr/bin/python3
# -*- coding: utf-8 -*-

import re

import pytest

from gnr.web.gnrwebstruct import (
    GnrDomSrc,
    GnrDomSrc_dojo_11,
    GnrDomElem,
    StructMethodError,
    struct_method,
)


class _AppStub(object):
    def checkResourcePermission(self, *args, **kwargs):
        return True

    def allowedByPreference(self, *args, **kwargs):
        return True


class _PageStub(object):
    filepath = '/tmp/fake_page.py'
    application = _AppStub()
    maintable = None
    pageOptions = {}

    def __init__(self):
        self._register_nodeId = {}

    def checkTablePermission(self, **kwargs):
        return True

    def getPreference(self, *args, **kwargs):
        return None


def _make_root(page=None):
    return GnrDomSrc_dojo_11.makeRoot(page or _PageStub())


def _attached_node(root):
    """Return a node that is properly attached to the tree (has a
    `_parentNode`), required to exercise the `autoslots` and `subtag`
    branches of `__getattr__` without crashing.
    """
    return root.child('div', childname='inner')


@pytest.fixture(autouse=True)
def _isolate_external_methods():
    """Save and restore `GnrDomSrc._external_methods` around each test.

    The `@struct_method` decorator mutates a class-level dict. Without
    this fixture, every test that decorates a function leaves a
    permanent entry behind, leaking state across tests and across
    pytest sessions.
    """
    saved = GnrDomSrc._external_methods.copy()
    try:
        yield
    finally:
        GnrDomSrc._external_methods.clear()
        GnrDomSrc._external_methods.update(saved)


# ---------------------------------------------------------------------------
# @struct_method registration (pre-existing tests, kept verbatim)
# ---------------------------------------------------------------------------

def test_register_without_name_without_underscore():
    @struct_method
    def foo():
        pass

    assert GnrDomSrc._external_methods['foo'] == 'foo'


def test_register_without_name_with_underscore():
    @struct_method
    def a_quuz():
        pass

    assert GnrDomSrc._external_methods['quuz'] == 'a_quuz'


def test_register_with_name():
    @struct_method('bar')
    def anotherFoo():
        pass

    assert GnrDomSrc._external_methods['bar'] == 'anotherFoo'


def test_valid_override_methods():
    @struct_method
    def foo1():
        pass

    @struct_method
    def foo1():  # noqa: F811
        pass


def test_invalid_override_methods():
    with pytest.raises(StructMethodError):
        @struct_method
        def foo1():
            pass

        @struct_method('foo1')
        def bar1():
            pass


# ---------------------------------------------------------------------------
# genroNameSpace snapshot
# ---------------------------------------------------------------------------

def test_genroNameSpace_total_count():
    """Freeze the cardinality of the public widget namespace.

    Lowercased dedup of htmlNS + dijitNS + dojoxNS + gnrNS yields 257
    entries today. Drift in either direction must be intentional.
    """
    assert len(GnrDomSrc_dojo_11.genroNameSpace) == 257


def test_genroNameSpace_samples_per_dialect():
    ns = GnrDomSrc_dojo_11.genroNameSpace
    assert ns['div'] == 'div'                          # html
    assert ns['bordercontainer'] == 'BorderContainer'  # dijit
    assert ns['chart'] == 'Chart'                      # dojox
    assert ns['dbselect'] == 'DbSelect'                # gnr


def test_genroNameSpace_is_lowercase_keyed():
    ns = GnrDomSrc_dojo_11.genroNameSpace
    assert all(k == k.lower() for k in ns), \
        'All keys in genroNameSpace must be lowercase'


def test_namespace_covers_all_four_dialects():
    """Defensive check: at least one representative from each of the
    four source lists must survive the lowercase dedup merge.
    """
    ns = GnrDomSrc_dojo_11.genroNameSpace
    assert 'abbr' in ns          # htmlNS (no explicit method)
    assert 'combobox' in ns      # dijitNS
    assert 'floatingpane' in ns  # dojoxNS
    assert 'dbselect' in ns      # gnrNS


# ---------------------------------------------------------------------------
# __getattr__ fallback ladder
# ---------------------------------------------------------------------------

def test_getattr_namespace_hit_returns_GnrDomElem():
    """A widget name that is in genroNameSpace but has no explicit
    method on the class is dispatched through __getattr__ and yields
    a GnrDomElem bound to the CamelCase tag.
    """
    root = _make_root()
    elem = root.borderContainer
    assert isinstance(elem, GnrDomElem)
    assert elem.tag == 'BorderContainer'


def test_getattr_namespace_hit_lowercase_only_tag():
    """A pure-lowercase HTML tag (e.g. 'abbr') routes through the
    namespace and produces a GnrDomElem with the tag as-is.
    """
    root = _make_root()
    elem = root.abbr
    assert isinstance(elem, GnrDomElem)
    assert elem.tag == 'abbr'


def test_getattr_case_insensitive_retry_to_explicit_method():
    """When a name is requested in a different case (e.g. 'Div')
    and a lowercase method 'div' exists on the class, __getattr__
    delegates to the lowercase explicit method.
    """
    root = _make_root()
    assert root.Div.__func__ is root.div.__func__


def test_getattr_external_method_hit():
    """A @struct_method registered widget is dispatched to a bound
    handler on the page when the page exposes the underlying function.
    """
    @struct_method('myExternalWidget')
    def my_external_widget_impl(struct, *args, **kwargs):  # noqa: F841
        pass

    page = _PageStub()

    def handler(struct, *args, **kwargs):
        return ('bound', args, kwargs)

    page.my_external_widget_impl = handler
    root = _make_root(page=page)
    bound = root.myExternalWidget
    assert callable(bound)
    assert bound('x', y=1) == ('bound', ('x',), {'y': 1})


def test_getattr_external_method_missing_handler_raises():
    """When a struct_method is registered but the page lacks the
    corresponding handler attribute, __getattr__ raises AttributeError
    citing the resolved internal method name and the page filepath.
    """
    @struct_method('orphanWidget')
    def _orphan_impl(struct):
        pass

    page = _PageStub()  # no _orphan_impl attribute
    root = _make_root(page=page)
    with pytest.raises(AttributeError) as excinfo:
        _ = root.orphanWidget
    msg = str(excinfo.value)
    assert '_orphan_impl' in msg
    assert 'fake_page.py' in msg


def test_getattr_unknown_name_raises_with_page_name():
    """Unknown widget on an attached node raises AttributeError citing
    the missing name and the page filepath.
    """
    root = _make_root()
    node = _attached_node(root)
    with pytest.raises(AttributeError) as excinfo:
        _ = node.this_widget_does_not_exist
    msg = str(excinfo.value)
    assert 'this_widget_does_not_exist' in msg
    assert 'fake_page.py' in msg


# ---------------------------------------------------------------------------
# Smoke: GnrDomSrc_dojo_11 instantiation and wiring
# ---------------------------------------------------------------------------

def test_makeRoot_returns_dojo_11_instance():
    root = _make_root()
    assert isinstance(root, GnrDomSrc_dojo_11)
    # _page wiring round-trips through the .page property
    assert root.page is root._page


def test_child_creates_attached_node():
    root = _make_root()
    node = root.child('div', childname='greeting')
    assert isinstance(node, GnrDomSrc_dojo_11)
    fetched = root.getNode('greeting')
    assert fetched is not None
    assert fetched._value is node


# ---------------------------------------------------------------------------
# formlet responsive modes (wrap / min_width)
# ---------------------------------------------------------------------------

def _formlet_attr(**kwargs):
    """Build a formlet on a fresh root and return the gridbox node's
    attributes. formlet() returns the gridbox *value* node; its attributes
    live on the parent node. `table` is passed so the _PageStub (which has
    no maintable) never has to resolve one."""
    node = _make_root().formlet(table='dummy.tbl', **kwargs)
    return node.parentNode.attr


def test_formlet_plain_is_grid_without_wrap():
    attrs = _formlet_attr()
    assert 'formlet' in attrs.get('_class', '')
    assert 'formlet_wrap' not in attrs.get('_class', '')
    assert attrs.get('columns') is None


def test_formlet_wrap_adds_wrap_class():
    attrs = _formlet_attr(wrap=True)
    assert 'formlet_wrap' in attrs.get('_class', '')
    # wrap is the flex mode: it must not build a grid-columns template
    assert attrs.get('columns') is None


def test_formlet_col_min_width_builds_autofit_columns():
    attrs = _formlet_attr(col_min_width='14em')
    assert attrs.get('columns') == 'repeat(auto-fit, minmax(14em, 1fr))'
    # col_min_width is the responsive-grid mode, NOT the flex wrap mode
    assert 'formlet_wrap' not in attrs.get('_class', '')


def test_formlet_col_min_width_drops_cols():
    # col_min_width owns the columns template; a stray `cols` must not survive
    # to fight it at the gridbox level
    attrs = _formlet_attr(col_min_width='14em', cols=3)
    assert attrs.get('columns') == 'repeat(auto-fit, minmax(14em, 1fr))'
    assert 'cols' not in attrs


# ---------------------------------------------------------------------------
# formbuilder: `hidden` hides the label cell as well
# ---------------------------------------------------------------------------

_GETCHILD_RE = re.compile(r"tdNode\.getChild\('([^']+)'\)")


def _fieldNode(root, value):
    return root.getNodeByAttr('value', value)


def _resolveChildPath(cellNode, path):
    """Resolve a client-side `getChild` path against the built source, the same
    way `gnr.GnrDomSource.getChild` walks it in the browser: every step moves
    into the found node, and `parent` climbs to the bag holding the owner node.
    """
    bag = cellNode.value
    node = None
    for step in path.split('/'):
        node = bag.parentNode.parentNode if step == 'parent' else bag.getNode(step)
        assert node is not None, 'unresolved step %s of %s' % (step, path)
        bag = node.value
    return node


def _hiddenFieldLabelCell(root, value):
    """Label cell targeted by the `hidden` propagation of the given field."""
    fieldNode = _fieldNode(root, value)
    path = _GETCHILD_RE.search(fieldNode.attr['onCreated']).group(1)
    return _resolveChildPath(fieldNode.parentNode, path)


def _hiddenFormbuilder(lblpos=None):
    """Two fields side by side, the first one `hidden`: mobileFormBuilder puts
    the labels on top (lblpos='T'), plain formbuilder keeps them on the left.
    """
    root = _make_root()
    pane = root.child('div', childname='pane')
    fb = pane.mobileFormBuilder(cols=2) if lblpos is None else pane.formbuilder(cols=2, lblpos=lblpos)
    fb.textbox(value='^.alfa', lbl='Alfa', hidden='^.hide_alfa')
    fb.textbox(value='^.beta', lbl='Beta')
    return root


def test_hidden_propagates_to_label_with_labels_on_top():
    root = _hiddenFormbuilder()
    labelCell = _hiddenFieldLabelCell(root, '^.alfa')
    # the label of the hidden field, not the one of the field next to it
    assert labelCell.attr['innerHTML'] == 'Alfa'
    assert labelCell.attr['tag'] == 'td'


def test_hidden_propagates_to_label_with_labels_on_left():
    root = _hiddenFormbuilder(lblpos='L')
    labelCell = _hiddenFieldLabelCell(root, '^.alfa')
    assert labelCell.attr['tag'] == 'td'
    # with labels on the left the cell wraps the label in a div
    assert labelCell.value.getNodes()[0].attr['innerHTML'] == 'Alfa'


def test_hidden_field_keeps_its_own_cell_as_first_target():
    root = _hiddenFormbuilder()
    fieldNode = _fieldNode(root, '^.alfa')
    assert 'this._hiddenTargets.push(tdNode.domNode)' in fieldNode.attr['onCreated']
    # `hidden` is popped at creation time and replayed on the cells once built
    assert "objectPop(arguments[0],'hidden')" in fieldNode.attr['onCreating']


def test_explicit_lbl_hidden_wins_over_propagation():
    root = _make_root()
    fb = root.child('div', childname='pane').mobileFormBuilder(cols=2)
    fb.textbox(value='^.alfa', lbl='Alfa', hidden='^.hide_alfa', lbl_hidden='^.hide_alfa')
    fieldNode = _fieldNode(root, '^.alfa')
    assert 'onCreated' not in fieldNode.attr
    assert fieldNode.attr['hidden'] == '^.hide_alfa'


def test_visible_field_gets_no_hidden_handler():
    root = _hiddenFormbuilder()
    assert 'onCreated' not in _fieldNode(root, '^.beta').attr


def test_hidden_group_member_targets_its_own_label_cell():
    root = _make_root()
    fb = root.child('div', childname='pane').mobileFormBuilder(cols=2)
    fb.textbox(value='^.alfa', lbl='Alfa', hidden='^.hide_alfa', hiddenGroup='alfa')
    fb.textbox(value='^.beta', lbl='Beta')
    fb.textbox(value='^.gamma', lbl='Gamma', hiddenGroup='alfa')
    memberNode = _fieldNode(root, '^.gamma')
    # the group member walks up to its own cell, like the hidden field does
    assert "this.attributeOwnerNode('tag','td')" in memberNode.attr['onCreated']
    labelCell = _hiddenFieldLabelCell(root, '^.gamma')
    assert labelCell.attr['innerHTML'] == 'Gamma'
