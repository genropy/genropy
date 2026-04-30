# -*- coding: utf-8 -*-
"""Base class for struct-based page templates.

A ``PageTemplate`` is a Python class that produces the HTML of a GenroPy
rootPage using :class:`GnrHtmlSrc` and ``toXml``, replacing the Mako
``.tpl`` rendering path.

Activation is opt-in via the ``experimental.no_mako`` preference.
"""

from gnr.core.gnrhtml import GnrHtmlSrc

XHTML_DOCTYPE = (
    '<?xml version="1.0" encoding="%(charset)s"?>\n'
    '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" '
    '"DTD/xhtml1-strict.dtd">\n'
)

SELF_CLOSED_TAGS = ['meta', 'br', 'img', 'link']


class PageBuilder(object):
    """Lightweight HTML builder backed by :class:`GnrHtmlSrc`.

    Unlike :class:`GnrHtmlBuilder`, this skips all print-oriented
    defaults (margin, no_print styles, Content-Type meta). The
    ``head`` and ``body`` attributes are :class:`GnrHtmlSrc` nodes.
    """

    def __init__(self):
        self.root = GnrHtmlSrc.makeRoot(parentWrapper=self)
        self.root.builder = self
        self._html = self.root.html(xmlns='http://www.w3.org/1999/xhtml')
        self.head = self._html.head()
        self.body = self._html.body()

    def toHtml(self, charset='utf-8'):
        return self.root.toXml(
            omitRoot=True,
            autocreate=True,
            forcedTagAttr='tag',
            addBagTypeAttr=False,
            typeattrs=False,
            self_closed_tags=SELF_CLOSED_TAGS,
            docHeader=XHTML_DOCTYPE % dict(charset=charset),
            pretty=True,
        )


class BasePageTemplate(object):
    """Base class for struct-based page templates."""

    def __init__(self, page):
        self.page = page

    @property
    def site(self):
        return self.page.site

    @property
    def frontend(self):
        return self.page.frontend

    def check_access(self):
        """Override to restrict who can render this template."""
        return True

    def make_builder(self):
        return PageBuilder()

    def render(self, arg_dict):
        builder = self.make_builder()
        self.build(builder, arg_dict)
        return builder.toHtml(charset=arg_dict.get('charset', 'utf-8'))

    def render_bytes(self, arg_dict):
        return self.render(arg_dict).encode('utf-8')

    def build(self, builder, arg_dict):
        """Populate ``builder.head`` and ``builder.body``. Override in subclasses."""
        pass
