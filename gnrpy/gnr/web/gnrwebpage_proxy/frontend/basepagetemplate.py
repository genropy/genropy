# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package         : GenroPy web - see LICENSE for details
# module template : struct-based rootPage rendering
# --------------------------------------------------------------------------

"""Base class for struct-based page templates.

A ``PageTemplate`` is a Python class that produces the HTML of a GenroPy
rootPage by populating a :class:`GnrHtmlBuilder` instead of rendering a
Mako ``.tpl`` file. Subclasses live in ``resources/<pkg>/tpl/<name>.py``
and are looked up by name through the resource system, which means any
package can override a system template by providing its own.

Activation is opt-in via the ``experimental.no_mako`` preference. The
URL parameter ``?_tpl=<name>`` selects a specific template at runtime.
"""

from gnr.core.gnrhtml import GnrHtmlBuilder


class BasePageTemplate(object):
    """Base class for struct-based page templates.

    Subclasses live in ``resources/<pkg>/tpl/<name>.py`` and expose a
    class named ``PageTemplate`` (convention).
    """

    def __init__(self, page):
        self.page = page

    @property
    def site(self):
        return self.page.site

    @property
    def frontend(self):
        return self.page.frontend

    def check_access(self):
        """Override to restrict who can render this template.

        Return ``True`` to allow, ``False`` to deny. Denial raises
        ``GnrUnauthorizedException`` at the dispatch layer.
        """
        return True

    def make_builder(self):
        """Create a non-print HTML builder.

        No page dimensions are passed: ``GnrHtmlBuilder`` skips the
        ``@page`` CSS rule and produces a clean ``<html><head><body>``
        tree suitable for SPAs, emails, and any non-print output.
        """
        builder = GnrHtmlBuilder(srcfactory=self._srcfactory())
        builder.initializeSrc()
        return builder

    def _srcfactory(self):
        """Return the GnrHtmlSrc subclass to use as DOM factory.

        Defaults to the frontend's ``domSrcFactory`` (e.g.
        ``GnrDomSrc_dojo_11`` / ``GnrDomSrc_dojo_20``). Subclasses can
        override to use a different factory.
        """
        return getattr(self.frontend, 'domSrcFactory', None)

    def render(self, arg_dict):
        """Build the HTML and return it as a string.

        Subclasses normally override :meth:`build` instead of this.
        """
        builder = self.make_builder()
        self.build(builder, arg_dict)
        return builder.toHtml()

    def render_bytes(self, arg_dict):
        """Variant of :meth:`render` that returns bytes (UTF-8).

        Provided for back-compat with callers that previously consumed
        Mako's ``output_encoding='utf-8'`` byte output.
        """
        return self.render(arg_dict).encode('utf-8')

    def build(self, builder, arg_dict):
        """Populate ``builder.head`` and ``builder.body`` from *arg_dict*.

        Override in subclasses. Default is a no-op.
        """
        pass
