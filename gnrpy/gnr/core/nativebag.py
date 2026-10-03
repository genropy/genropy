"""Install a bounded native-backed ``gnr.core.gnrbag`` module.

Activation is intentionally process local. It must run before any public
``gnr.core.gnrbag`` import so GenroPy consumers capture the native classes when
their modules are first created.
"""

from __future__ import annotations

import sys
from importlib.abc import Loader, MetaPathFinder
from importlib.util import spec_from_loader
from types import ModuleType

_PUBLIC_MODULE = "gnr.core.gnrbag"


class ActivationError(RuntimeError):
    """Raised when process-local activation cannot preserve class identity."""


class _NativeBagModule(ModuleType):
    """Prevent ordinary assignments from replacing the selected public classes."""

    def __setattr__(self, name, value):
        if name in self.__dict__.get('__native_genro_bag_exports__', ()):
            if self.__dict__.get(name) is not value:
                raise ActivationError(f'genro-bag {name} export was replaced after activation')
        if name == '__native_genro_bag_exports__' and name in self.__dict__:
            raise ActivationError('genro-bag exports are fixed for this process')
        super().__setattr__(name, value)

    def __delattr__(self, name):
        if name in self.__dict__.get('__native_genro_bag_exports__', ()) or name == '__native_genro_bag_exports__':
            raise ActivationError(f'genro-bag {name} export cannot be deleted after activation')
        super().__delattr__(name)


class _NativeBagImporter(MetaPathFinder, Loader):
    """Keep reload and cache-miss imports on the same process-local facade."""

    def __init__(self, module):
        self.module = module

    def find_spec(self, fullname, path=None, target=None):
        if fullname == _PUBLIC_MODULE:
            return spec_from_loader(fullname, self, origin=__file__)
        return None

    def create_module(self, spec):
        return self.module

    def exec_module(self, module):
        if module is not self.module:
            raise ActivationError('Cannot replace the process-local Bag facade')


class BagAsXml:
    """Legacy marker for XML fragments already serialized by a producer."""

    def __init__(self, value):
        self.value = value


def activate() -> ModuleType:
    """Activate native Bag exports before any GenroPy consumer import."""
    from gnr._bag_mode import selected_bag_mode

    if selected_bag_mode() != 'genro-bag':
        raise ActivationError('Bag implementation is fixed at startup; restart with genro-bag enabled')
    existing = sys.modules.get(_PUBLIC_MODULE)
    if existing is not None:
        if getattr(existing, "__native_genro_bag__", False):
            return existing
        raise ActivationError(
            "gnr.core.gnrbag was imported before genro-bag activation; restart the "
            "process and call gnr.core.nativebag.activate() first"
        )

    from genro_bag import Bag, BagException, BagNode, BagNodeException, BagResolver
    from genro_bag.resolver import BagCbResolver
    from genro_bag.resolvers import DirectoryResolver
    from gnr.core.nativebag_helpers import (NetBag, TraceBackResolver, to_genropy_js,
                                            install_resolver_serialization_bridge, legacy_walk)

    # GenroPy owns this compatibility surface while retaining the native Bag
    # class identity required by consumers and the TYTX registry.
    Bag.to_genropy_js = to_genropy_js
    Bag.walk = legacy_walk
    install_resolver_serialization_bridge()

    class BagDeprecatedCall(BagException):
        def __init__(self, errcode, message):
            self.errcode = errcode
            self.message = message

    BagAsXml.__module__ = _PUBLIC_MODULE
    BagDeprecatedCall.__module__ = _PUBLIC_MODULE
    TraceBackResolver.__module__ = _PUBLIC_MODULE
    NetBag.__module__ = _PUBLIC_MODULE

    public = _NativeBagModule(_PUBLIC_MODULE)
    public.__file__ = __file__
    public.__package__ = "gnr.core"
    public.__doc__ = __doc__
    public.Bag = Bag
    public.BagNode = BagNode
    public.BagResolver = BagResolver
    public.BagException = BagException
    public.BagNodeException = BagNodeException
    public.BagAsXml = BagAsXml
    public.BagCbResolver = BagCbResolver
    public.DirectoryResolver = DirectoryResolver
    public.BagDeprecatedCall = BagDeprecatedCall
    public.TraceBackResolver = TraceBackResolver
    public.NetBag = NetBag
    public.__native_genro_bag__ = True
    public.__native_genro_bag_exports__ = (
        "Bag",
        "BagNode",
        "BagResolver",
        "BagException",
        "BagNodeException",
        "BagAsXml",
        "BagCbResolver",
        "DirectoryResolver",
        "BagDeprecatedCall",
        "TraceBackResolver",
        "NetBag",
    )

    importer = _NativeBagImporter(public)
    public.__spec__ = importer.find_spec(_PUBLIC_MODULE)
    public.__loader__ = importer
    sys.meta_path.insert(0, importer)
    sys.modules[_PUBLIC_MODULE] = public
    import gnr.core as core_package

    core_package.gnrbag = public
    return public
