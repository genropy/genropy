#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""Class-level tests for the widget declaration package.

These tests exercise `gnr.web.widgets` as a pure declarative catalog,
without instantiating `GnrDomSrc` or touching `__getattr__`. They are
the foundation for the registry-driven dispatch wired in a later commit.
"""

from gnr.web.widgets import AllWidgets, WidgetMixinBase, element
from gnr.web.widgets.dijit import DijitWidgets
from gnr.web.widgets.dojox import DojoxWidgets
from gnr.web.widgets.genro import GenroWidgets
from gnr.web.widgets.html import HtmlWidgets


# ---------------------------------------------------------------------------
# @element decorator semantics
# ---------------------------------------------------------------------------

def test_element_bare_form_uses_function_name():
    """`@element` without arguments stores the function name as tag."""
    @element
    def my_widget():
        ...
    assert my_widget._widget_tag == 'my_widget'


def test_element_callform_with_explicit_name_overrides_function_name():
    """`@element(name='X')` stores 'X' as tag regardless of the function name."""
    @element(name='SomeTag')
    def some_func():
        ...
    assert some_func._widget_tag == 'SomeTag'


def test_element_callform_without_name_uses_function_name():
    """`@element()` (empty call form) defaults to function name."""
    @element()
    def article():
        ...
    assert article._widget_tag == 'article'


def test_element_metadata_stored_on_method():
    """Free-form kwargs are stored as `_widget_metadata`."""
    @element(sub_tags='a,b', void=True)
    def something():
        ...
    assert something._widget_metadata == {'sub_tags': 'a,b', 'void': True}


def test_element_no_metadata_no_attribute():
    """When no metadata is provided, `_widget_metadata` is NOT set
    (keeps the decorator footprint minimal)."""
    @element
    def bare():
        ...
    assert not hasattr(bare, '_widget_metadata')


def test_element_name_override_for_python_keyword():
    """The override exists to handle Python keywords."""
    @element(name='del')
    def del_():
        ...
    assert del_._widget_tag == 'del'


# ---------------------------------------------------------------------------
# WidgetMixinBase: _widget_names collection via __init_subclass__
# ---------------------------------------------------------------------------

def test_widget_mixin_base_collects_decorated_methods():
    """A subclass of WidgetMixinBase exposes `_widget_names` populated
    by `__init_subclass__` from its `@element`-decorated methods."""
    class _T(WidgetMixinBase):
        @element
        def alpha(self):
            ...

        @element(name='Beta')
        def beta(self):
            ...

    assert _T._widget_names == {'alpha': 'alpha', 'beta': 'Beta'}


def test_widget_mixin_base_lowercases_keys():
    """Keys in `_widget_names` are always lowercase, regardless of the
    Python method name's casing."""
    class _T(WidgetMixinBase):
        @element
        def Mixed(self):
            ...

    assert 'mixed' in _T._widget_names
    assert _T._widget_names['mixed'] == 'Mixed'


def test_widget_mixin_base_ignores_undecorated_methods():
    """Methods without `@element` do not appear in `_widget_names`."""
    class _T(WidgetMixinBase):
        @element
        def known(self):
            ...

        def helper(self):  # no decorator
            ...

    assert 'known' in _T._widget_names
    assert 'helper' not in _T._widget_names


def test_widget_mixin_base_leftmost_wins_on_collision():
    """When composing mixins, the leftmost wins on collision — this is
    the contract for `AllWidgets` collision resolution."""
    class _A(WidgetMixinBase):
        @element
        def shared(self):
            ...

    class _B(WidgetMixinBase):
        @element(name='SharedFromB')
        def shared(self):
            ...

    class _Composed(_A, _B):
        pass

    assert _Composed._widget_names['shared'] == 'shared'  # _A (leftmost) wins


# ---------------------------------------------------------------------------
# Per-dialect mixin snapshots
# ---------------------------------------------------------------------------

def test_html_widgets_count():
    assert len(HtmlWidgets._widget_names) == 87


def test_dijit_widgets_count():
    assert len(DijitWidgets._widget_names) == 42


def test_dojox_widgets_count():
    assert len(DojoxWidgets._widget_names) == 31


def test_genro_widgets_count():
    assert len(GenroWidgets._widget_names) == 98


def test_html_widgets_sample_entries():
    """Spot-check core HTML elements are registered."""
    ns = HtmlWidgets._widget_names
    for name in ['div', 'span', 'p', 'h1', 'table', 'tr', 'td', 'a', 'img']:
        assert name in ns, f'missing {name!r} in HtmlWidgets'


def test_dijit_widgets_sample_entries():
    ns = DijitWidgets._widget_names
    for name in ['textbox', 'button', 'dialog', 'menu']:
        assert name in ns, f'missing {name!r} in DijitWidgets'


def test_dojox_widgets_sample_entries():
    ns = DojoxWidgets._widget_names
    for name in ['floatingpane', 'dock', 'chart', 'lightbox']:
        assert name in ns, f'missing {name!r} in DojoxWidgets'


def test_genro_widgets_sample_entries():
    ns = GenroWidgets._widget_names
    for name in ['datacontroller', 'datarpc', 'dbselect', 'framepane']:
        assert name in ns, f'missing {name!r} in GenroWidgets'


def test_all_dialect_keys_are_lowercase():
    """Every key in every per-dialect `_widget_names` is lowercase."""
    for mixin in (HtmlWidgets, DijitWidgets, DojoxWidgets, GenroWidgets):
        for key in mixin._widget_names:
            assert key == key.lower(), f'{mixin.__name__}: non-lowercase key {key!r}'


# ---------------------------------------------------------------------------
# AllWidgets: composed catalog
# ---------------------------------------------------------------------------

def test_all_widgets_total_count():
    """The composed catalog spans all four dialects after collision merge."""
    assert len(AllWidgets._widget_names) == 256


def test_all_widgets_includes_every_dialect():
    """Every entry of every per-dialect mixin appears in AllWidgets."""
    union_keys = (
        set(HtmlWidgets._widget_names)
        | set(DijitWidgets._widget_names)
        | set(DojoxWidgets._widget_names)
        | set(GenroWidgets._widget_names)
    )
    assert set(AllWidgets._widget_names) == union_keys


def test_all_widgets_collision_dijit_wins_over_html():
    """`button` and `textarea` are declared in both Html and Dijit. The
    MRO `(Genro, Dojox, Dijit, Html)` makes Dijit win. Today the tag
    value is identical because both forms are lowercase, but the
    collision must resolve through Dijit's declaration.

    Additional collisions (`dialog`, `menu`, `script`) will appear when
    the html mixin is replaced by the W3C HTML5 catalog in a later
    step; that change must update this test."""
    for name in ('button', 'textarea'):
        assert name in DijitWidgets._widget_names
        assert name in HtmlWidgets._widget_names
        assert AllWidgets._widget_names[name] == DijitWidgets._widget_names[name]


def test_all_widgets_keys_lowercase():
    for key in AllWidgets._widget_names:
        assert key == key.lower(), f'non-lowercase key {key!r}'


def test_all_widgets_preserves_camelcase_in_tag_values():
    """Tag values preserve the original casing of the declaring function."""
    # In DojoxWidgets, `def borderContainer` declares the tag as-is.
    assert AllWidgets._widget_names['bordercontainer'] == 'borderContainer'
    # In GenroWidgets, `def DbSelect` declares tag 'DbSelect'.
    assert AllWidgets._widget_names['dbselect'] == 'DbSelect'
