#!/usr/bin/python3
# -*- coding: utf-8 -*-

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

    def __init__(self):
        self._register_nodeId = {}

    def checkTablePermission(self, **kwargs):
        return True


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

    Sourced from `AllWidgets._widget_names`, which composes the four
    dialect mixins. 256 entries today. Drift in either direction must
    be intentional.
    """
    assert len(GnrDomSrc_dojo_11.genroNameSpace) == 256


def test_genroNameSpace_samples_per_dialect():
    """Tag values reflect the Python method name in each dialect mixin.
    The client lower-cases tags before dispatching to its handler
    registry, so the casing of the value is informational only — the
    contract is that the *key* is always lowercase."""
    ns = GnrDomSrc_dojo_11.genroNameSpace
    assert ns['div'] == 'div'                          # html
    assert ns['bordercontainer'] == 'borderContainer'  # dojox declares borderContainer
    assert ns['chart'] == 'chart'                      # dojox
    assert ns['dbselect'] == 'DbSelect'                # genro


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
    a GnrDomElem bound to the declared tag.
    """
    root = _make_root()
    elem = root.borderContainer
    assert isinstance(elem, GnrDomElem)
    assert elem.tag == 'borderContainer'


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
