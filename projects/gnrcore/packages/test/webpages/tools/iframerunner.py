# -*- coding: utf-8 -*-

"""An iframe that re-enters the SAME page through a different entry point

`iframe(main='iframeBody')` loads the current url again inside the frame, but the
server calls the named public method instead of `main()`: the method receives the
frame's root pane and builds its whole content. Every `main_*` attribute on the
iframe travels to it as a keyword argument, which is how one page can serve
several parameterized frames without a page of its own for each.
"""

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_1_firsttest(self, pane):
        """The frame is built by `iframeBody`, which receives main_foo as its `foo`"""
        pane = pane.contentPane(height='300px')
        pane.iframe(main='iframeBody', main_foo=36)

    @public_method
    def iframeBody(self, root, foo=None, **kwargs):
        root.div(foo)
