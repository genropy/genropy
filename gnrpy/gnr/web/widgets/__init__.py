"""GenroPy widget declarations.

Each mixin in this package (html, dijit, dojox, genro) lists the widgets
supported by one dialect, marking every method with `@element`. The
mixins are NOT inherited by `GnrDomSrc`; they are introspected by
`GnrDomSrc.__getattr__` through the composed class `AllWidgets`, which
gathers every dialect into a single lookup table.

Method bodies are empty (`...`). The bodies that build the actual DOM
tree live on `GnrDomSrc` and its subclasses. The mixins are pure
declarative catalogs.

The `element` decorator name is preserved from the historical
`genro_bag.builder.element` so that the mixin files do not need to
change beyond the import line.
"""

from typing import Any, Callable


def element(_fn: Callable | None = None, *, name: str | None = None, **metadata: Any):
    """Mark a method as a widget declaration.

    Three forms are accepted:

        @element
        def article(self): ...

        @element()
        def aside(self): ...

        @element(name='del', sub_tags='*')
        def del_(self): ...

    Parameters
    ----------
    name :
        Tag name override. Defaults to the Python function name. Use
        this when the Python function name must differ from the tag —
        typically because the tag clashes with a Python keyword.
    metadata :
        Free-form metadata stored on the method as ``_widget_metadata``.
        Reserved for future use (sub_tags, parent_tags, void elements,
        ...). Not consumed at runtime by the dispatcher in this PR.
    """
    def deco(fn: Callable) -> Callable:
        fn._widget_tag = name if name is not None else fn.__name__
        if metadata:
            fn._widget_metadata = metadata
        return fn

    if _fn is None:
        return deco
    return deco(_fn)


class WidgetMixinBase:
    """Base for every widget-declaration mixin.

    Populates `_widget_names` on subclass creation: a dict mapping
    lowercase widget names to their declared tag. The MRO is walked
    in reverse so that leftmost bases win on collisions — this matches
    the historical merge order of `genroNameSpace` (sequential
    `dict.update`, last-wins) after inverting the dialect order in the
    composed class `AllWidgets`.
    """

    _widget_names: dict[str, str] = {}

    def __init_subclass__(cls, **kw: Any) -> None:
        super().__init_subclass__(**kw)
        collected: dict[str, str] = {}
        for klass in reversed(cls.__mro__):
            for attr_name, member in vars(klass).items():
                tag = getattr(member, '_widget_tag', None)
                if tag is not None:
                    collected[attr_name.lower()] = tag
        cls._widget_names = collected


from gnr.web.widgets.html import HtmlWidgets         # noqa: E402
from gnr.web.widgets.dijit import DijitWidgets       # noqa: E402
from gnr.web.widgets.dojox import DojoxWidgets       # noqa: E402
from gnr.web.widgets.genro import GenroWidgets       # noqa: E402


class AllWidgets(GenroWidgets, DojoxWidgets, DijitWidgets, HtmlWidgets):
    """Composed widget catalog spanning all four dialects.

    Pure introspection target — never instantiated, never inherited by
    `GnrDomSrc`. The dispatcher in `GnrDomSrc.__getattr__` consults
    `AllWidgets._widget_names` to decide whether a name is a valid
    widget.

    The MRO order (Genro > Dojox > Dijit > Html) defines collision
    policy: when the same name is declared in multiple dialects, the
    leftmost wins. This matches the historical merge order of
    `genroNameSpace` (`html → dijit → dojox → gnr` via successive
    `dict.update`, last-wins).
    """
    pass
