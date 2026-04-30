# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package         : GenroPy web - see LICENSE for details
# module          : template lookup for struct-based page templates
# --------------------------------------------------------------------------

"""Lookup utility for struct-based page templates.

Templates live as ``.py`` files in resource directories that the page
already knows about (``page.tpldirectories``). A package can override a
system template by providing its own file with the same name in the
package's ``resources/tpl/`` folder.

Each template module exposes a ``PageTemplate`` class (convention). The
lookup function imports the first match and returns the class.
"""

import importlib.util
import os


def lookup_template_class(tpldirectories, name, symbol='PageTemplate'):
    """Find a struct page template class by *name* in *tpldirectories*.

    :param tpldirectories: ordered list of directories to search (same
        list used by the Mako lookup, so override semantics match).
    :param name: template name without extension (e.g. ``'standard'``).
    :param symbol: the class name exported by the template module
        (default ``'PageTemplate'``). Sub-templates such as
        ``gnr_header`` use a different symbol (``HeaderTemplate``).
    :return: the requested class from the first match, or ``None`` if
        no ``<name>.py`` is found, or it does not export *symbol*.
    """
    for directory in tpldirectories:
        candidate = os.path.join(directory, '%s.py' % name)
        if os.path.isfile(candidate):
            return _load_template_class(candidate, name, symbol)
    return None


def _load_template_class(filepath, name, symbol):
    """Import *filepath* as a module and return its *symbol* class."""
    module_name = 'gnr_template_%s_%d' % (name, abs(hash(filepath)))
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, symbol, None)
