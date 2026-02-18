# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrdecorator : decorator utilities
# Copyright (c) : 2004 - 2007 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
# --------------------------------------------------------------------------
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
"""Decorator utilities for Genro framework.

This module provides decorators for common patterns in Genro applications:
- Marking methods as public RPC endpoints
- Extracting kwargs into sub-dictionaries
- Type casting for method parameters
- Deprecation warnings
- Customization hooks

Example:
    >>> from gnr.core.gnrdecorator import public_method, extract_kwargs
    >>>
    >>> class MyPage:
    ...     @public_method
    ...     def getData(self, param):
    ...         return {'result': param}
    ...
    ...     @extract_kwargs(style=True)
    ...     def buildUI(self, pane, style_kwargs=None, **kwargs):
    ...         # style_kwargs contains all style_* parameters
    ...         pass
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from gnr.core.gnrdict import dictExtract

if TYPE_CHECKING:
    from typing import Any, Callable


def metadata(**kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to attach metadata attributes to a function.

    Adds keyword arguments as attributes on the decorated function.
    Optionally prefixes attribute names.

    Args:
        **kwargs: Attributes to set on the function.
            Special key 'prefix' adds a prefix to all attribute names.

    Returns:
        Decorator function.

    Example:
        >>> @metadata(author='John', version='1.0')
        ... def myFunc():
        ...     pass
        >>> myFunc.author
        'John'
    """

    def decore(func: Callable[..., Any]) -> Callable[..., Any]:
        prefix = kwargs.pop("prefix", None)
        for k, v in list(kwargs.items()):
            setattr(func, "%s_%s" % (prefix, k) if prefix else k, v)
        return func

    return decore


def autocast(**cast_kwargs: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to automatically cast string arguments to specified types.

    Uses GnrClassCatalog to convert string values to their target types.
    Useful for RPC methods that receive string parameters from HTTP requests.

    Args:
        **cast_kwargs: Mapping of parameter names to type codes.
            Type codes: 'I'=integer, 'N'=numeric, 'D'=date, 'B'=boolean, etc.

    Returns:
        Decorator function.

    Example:
        >>> @autocast(count='I', price='N')
        ... def processOrder(count, price):
        ...     # count is now int, price is Decimal
        ...     pass
    """

    def decore(func: Callable[..., Any]) -> Callable[..., Any]:
        from gnr.core.gnrclasses import GnrClassCatalog

        setattr(func, "_autocast", cast_kwargs)

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            converter = GnrClassCatalog.convert()
            for k, v in kwargs.items():
                dtype = cast_kwargs.get(k)
                if dtype:
                    converted = converter.fromText(v, dtype)
                    if isinstance(converted, tuple):
                        converted = converted[0]
                    kwargs[k] = converted
            res = func(*args, **kwargs)
            return res

        wrapper.__name__ = func.__name__
        if hasattr(func, "is_rpc"):
            wrapper.is_rpc = func.is_rpc  # type: ignore[attr-defined]
        return wrapper

    return decore


def public_method(
    *args: Callable[..., Any], **metadata: Any
) -> Callable[..., Any] | Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to mark methods as public RPC endpoints.

    Methods decorated with @public_method can be called via data RPC
    from the client. Can be used with or without arguments.

    Args:
        *args: When used without parentheses, the function to decorate.
        **metadata: Optional metadata attributes to attach to the function.
            Special key 'prefix' adds a prefix to attribute names.

    Returns:
        Decorated function with is_rpc=True attribute.

    Example:
        >>> @public_method
        ... def getData(self):
        ...     return {'data': 'value'}
        ...
        >>> @public_method(tags='admin', cache=True)
        ... def adminData(self):
        ...     return {'admin': 'data'}
    """
    if metadata:

        def decore(func: Callable[..., Any]) -> Callable[..., Any]:
            prefix = metadata.pop("prefix", None)
            func.is_rpc = True  # type: ignore[attr-defined]
            for k, v in list(metadata.items()):
                setattr(func, "%s_%s" % (prefix, k) if prefix else k, v)
            return func

        return decore
    else:
        func = args[0]
        func.is_rpc = True  # type: ignore[attr-defined]
        return func


def websocket_method(
    *args: Callable[..., Any], **metadata: Any
) -> Callable[..., Any] | Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to mark methods as WebSocket RPC endpoints.

    Similar to @public_method but also marks the method for WebSocket access.
    Can be used with or without arguments.

    Args:
        *args: When used without parentheses, the function to decorate.
        **metadata: Optional metadata attributes to attach.
            Special key 'prefix' adds a prefix to attribute names.

    Returns:
        Decorated function with is_rpc=True and is_websocket=True attributes.

    Example:
        >>> @websocket_method
        ... def streamData(self):
        ...     yield {'data': 'chunk'}
    """
    if metadata:

        def decore(func: Callable[..., Any]) -> Callable[..., Any]:
            prefix = metadata.pop("prefix", None)
            func.is_rpc = True  # type: ignore[attr-defined]
            for k, v in list(metadata.items()):
                setattr(func, "%s_%s" % (prefix, k) if prefix else k, v)
            return func

        return decore
    else:
        func = args[0]
        func.is_rpc = True  # type: ignore[attr-defined]
        func.is_websocket = True  # type: ignore[attr-defined]
        return func


def extract_kwargs(
    _adapter: str | None = None,
    _dictkwargs: dict[str, Any] | None = None,
    **extract_kwargs: bool | dict[str, Any],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to extract kwargs into sub-dictionaries by prefix.

    Groups keyword arguments by prefix, creating separate dictionaries
    for each prefix. Useful for passing grouped options to sub-components.

    Args:
        _adapter: Optional attribute name on self that pre-processes kwargs.
        _dictkwargs: Dictionary of extraction specifications.
        **extract_kwargs: Prefix names to extract.
            If True, extracts with default options (pop=True).
            If dict, specifies extraction options:
                - slice_prefix: Remove prefix from keys (default: True)
                - pop: Remove from original kwargs (default: False)
                - is_list: Join multiple values into list

    Returns:
        Decorator function.

    Example:
        >>> @extract_kwargs(palette=True, dialog=True)
        ... def myMethod(self, pane, palette_kwargs=None, dialog_kwargs=None, **kwargs):
        ...     # palette_kwargs contains all palette_* params
        ...     # dialog_kwargs contains all dialog_* params
        ...     pass
        ...
        >>> obj.myMethod(pane, palette_height='200px', dialog_title='Hello')
        # palette_kwargs = {'height': '200px'}
        # dialog_kwargs = {'title': 'Hello'}

    Note:
        The method must accept ``{prefix}_kwargs`` parameters for each
        prefix specified in the decorator.
    """
    if _dictkwargs:
        extract_kwargs = _dictkwargs  # type: ignore[assignment]

    def decore(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            if _adapter:
                adapter = getattr(self, _adapter)
                if adapter:
                    adapter(kwargs)
            for extract_key, extract_value in list(extract_kwargs.items()):
                grp_key = "%s_kwargs" % extract_key
                curr = kwargs.pop(grp_key, dict()) or dict()
                dfltExtract: dict[str, Any] = dict(
                    slice_prefix=True, pop=False, is_list=False
                )
                if extract_value is True:
                    dfltExtract["pop"] = True
                elif isinstance(extract_value, dict):
                    dfltExtract.update(extract_value)
                curr.update(dictExtract(kwargs, "%s_" % extract_key, **dfltExtract))
                kwargs[grp_key] = curr
            return func(self, *args, **kwargs)

        wrapper.__doc__ = func.__doc__
        return wrapper

    return decore


def customizable(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to make a method customizable via hooks.

    Allows other methods to hook into the decorated method's execution
    at two points: before (oncalling) and after (oncalled).

    Hook methods should be named:
        - ``{methodname}_oncalling_{hookname}`` - called before
        - ``{methodname}_oncalled_{hookname}`` - called after

    Hook methods can return False to abort execution.

    Args:
        func: The function to make customizable.

    Returns:
        Wrapped function that executes hooks.

    Example:
        >>> class MyPage:
        ...     @customizable
        ...     def processData(self, data):
        ...         return data.upper()
        ...
        ...     def processData_oncalling_validate(self, data):
        ...         if not data:
        ...             return False  # abort
        ...
        ...     def processData_oncalled_log(self, data, _original_result=None):
        ...         print(f"Processed: {_original_result}")
    """

    def customize(page: Any, name: str, *args: Any, **kwargs: Any) -> bool | None:
        cust_list = [
            (k, getattr(page, k))
            for k in dir(page)
            if k.startswith(name) and not k.endswith("_")
        ]
        for k, handler in sorted(cust_list, key=lambda t: t[1].__order):
            result = handler(*args, **kwargs)
            if result is False:
                return result
        return None

    def wrapper(page: Any, *args: Any, **kwargs: Any) -> Any:
        oncalling_result = customize(
            page, "%s_oncalling_" % func.__name__, *args, **kwargs
        )
        if oncalling_result is False:
            return
        result = func(page, *args, **kwargs)
        kwargs["_original_result"] = result
        customize(page, "%s_oncalled_" % func.__name__, *args, **kwargs)
        return result

    return wrapper


def oncalling(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to mark a method as an 'oncalling' hook.

    Sets the mixin_as attribute for automatic method naming
    when used with customizable methods.

    Args:
        func: The hook function.

    Returns:
        Function with mixin_as attribute set.

    Example:
        >>> @oncalling
        ... def processData(self, data):
        ...     # This becomes processData_oncalling_# when mixed in
        ...     pass
    """
    setattr(func, "mixin_as", "%s_oncalling_#" % (func.__name__))
    return func


def oncalled(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to mark a method as an 'oncalled' hook.

    Sets the mixin_as attribute for automatic method naming
    when used with customizable methods.

    Args:
        func: The hook function.

    Returns:
        Function with mixin_as attribute set.

    Example:
        >>> @oncalled
        ... def processData(self, data, _original_result=None):
        ...     # This becomes processData_oncalled_# when mixed in
        ...     pass
    """
    setattr(func, "mixin_as", "%s_oncalled_#" % (func.__name__))
    return func


def deprecated(
    message: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to mark functions as deprecated.

    Emits a DeprecationWarning when the decorated function is called.

    Args:
        message: Optional message explaining the deprecation or
            suggesting an alternative.

    Returns:
        Decorator function.

    Example:
        >>> @deprecated("Use newFunc() instead")
        ... def oldFunc():
        ...     pass
        ...
        >>> oldFunc()  # Emits: DeprecationWarning: Call to deprecated function oldFunc: Use newFunc() instead
    """
    if message:
        message = ": %s" % message
    else:
        message = ""

    def decore(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            warnings.warn(
                "Call to deprecated function %s%s" % (func.__name__, message),
                category=DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__dict__.update(func.__dict__)
        return wrapper

    return decore
