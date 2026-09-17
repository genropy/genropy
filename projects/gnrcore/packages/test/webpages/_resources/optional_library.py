# -*- coding: utf-8 -*-

"""Guard for a test page whose example needs a library gnrpy does not require

A page importing such a library at module level cannot be rendered at all where
the library is missing: the import raises, the render sweep records a 500 and
the reader gets an error page instead of an example. Those pages import it under
a `try/except ImportError` and open every case that needs it with
`opl_missingLibrary`, which says what to install and tells the case to stop
there, so the page still renders and says why the example is not on it.
"""

from gnr.web.gnrbaseclasses import BaseComponent


class OptionalLibrary(BaseComponent):

    def opl_missingLibrary(self, pane, imported, library):
        """True when the library is missing; then the pane says how to install it

        `imported` is whatever the page's guarded import bound, None when the
        library is absent, and `library` the name to install it by: the module
        and the distribution do not always match (`PIL` ships as Pillow,
        `imdb` as cinemagoer).
        """
        if imported is not None:
            return False
        pane.div('This example needs the %s library, which is not installed here. '
                 'Install it with: pip install %s' % (library, library),
                 padding='6px 10px', margin='4px', border_left='3px solid #ffc107',
                 background='#fff8e1', color='#8a6d3b', font_weight='bold')
        return True
