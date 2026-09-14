"""Install a bounded native-backed ``gnr.core.gnrbag`` module.

Activation is intentionally process local. It must run before any public
``gnr.core.gnrbag`` import so GenroPy consumers capture the native classes when
their modules are first created.
"""

from __future__ import annotations

import sys
from types import ModuleType

_PUBLIC_MODULE = "gnr.core.gnrbag"


class ActivationError(RuntimeError):
    """Raised when process-local activation cannot preserve class identity."""


class BagAsXml:
    """Legacy marker for XML fragments already serialized by a producer."""

    def __init__(self, value):
        self.value = value


def activate() -> ModuleType:
    """Activate native Bag exports before any GenroPy consumer import."""
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
    from gnr.core.nativebag_helpers import NetBag, TraceBackResolver

    class BagValidationError(BagException):
        pass

    class BagDeprecatedCall(BagException):
        def __init__(self, errcode, message):
            self.errcode = errcode
            self.message = message

    BagAsXml.__module__ = _PUBLIC_MODULE
    BagValidationError.__module__ = _PUBLIC_MODULE
    BagDeprecatedCall.__module__ = _PUBLIC_MODULE
    TraceBackResolver.__module__ = _PUBLIC_MODULE
    NetBag.__module__ = _PUBLIC_MODULE

    public = ModuleType(_PUBLIC_MODULE)
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
    public.BagValidationError = BagValidationError
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
        "BagValidationError",
        "BagDeprecatedCall",
        "TraceBackResolver",
        "NetBag",
    )

    sys.modules[_PUBLIC_MODULE] = public
    import gnr.core as core_package

    core_package.gnrbag = public
    return public


def validate_mixin_bindings(source):
    """Reject historical Bag classes carried into an opted-in native mixin.

    Checks class ancestry and class references used by copied functions,
    including closures and wrapped functions. It does not prohibit application
    overrides or attempt to certify arbitrary dynamically computed imports.
    """
    from types import FunctionType, MethodType

    from genro_bag import Bag, BagNode, BagResolver

    native_types = (Bag, BagNode, BagResolver)
    public = sys.modules.get(_PUBLIC_MODULE)
    for cls in native_types:
        if public is None or getattr(public, cls.__name__, None) is not cls:
            raise ActivationError(f'genro-bag {cls.__name__} export was replaced after activation')
    seen = set()

    def check_class(cls):
        for base in cls.__mro__:
            if base in native_types or base.__name__ not in {'Bag', 'BagNode', 'BagResolver'}:
                continue
            initializer = base.__dict__.get('__init__')
            code = getattr(initializer, '__code__', None)
            if code and code.co_filename.replace('\\', '/').endswith('/gnrbag.py'):
                raise ActivationError(
                    f'Historical {base.__name__} from {code.co_filename} reached a genro-bag mixin'
                )

    def check(value):
        if id(value) in seen:
            return
        seen.add(id(value))
        if isinstance(value, type):
            check_class(value)
            # Inspect methods without invoking dynamic __getattr__ or properties.
            for base in value.__mro__:
                if base is object:
                    continue
                for member in vars(base).values():
                    if isinstance(member, (FunctionType, MethodType, staticmethod, classmethod)):
                        check(member)
                    elif isinstance(member, property):
                        check(member.fget)
                        check(member.fset)
        elif isinstance(value, (staticmethod, classmethod, MethodType)):
            check(value.__func__)
        elif isinstance(value, FunctionType):
            for name in value.__code__.co_names:
                bound = value.__globals__.get(name)
                if isinstance(bound, type):
                    check_class(bound)
                elif isinstance(bound, ModuleType):
                    for classname in ('Bag', 'BagNode', 'BagResolver'):
                        cls = vars(bound).get(classname)
                        if isinstance(cls, type):
                            check_class(cls)
            for cell in value.__closure__ or ():
                try:
                    bound = cell.cell_contents
                except ValueError:
                    continue
                if isinstance(bound, type):
                    check_class(bound)
                elif isinstance(bound, FunctionType):
                    check(bound)
            check(getattr(value, '__wrapped__', None))

    if isinstance(source, type):
        check(source)
    else:
        check(type(source))
        for value in getattr(source, '__dict__', {}).values():
            if isinstance(value, (FunctionType, MethodType)):
                check(value)
