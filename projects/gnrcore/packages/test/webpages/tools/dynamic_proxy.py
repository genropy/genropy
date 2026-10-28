# -*- coding: utf-8 -*-

"""@page_proxy: mixing a component in under a name of your own

A plain `py_requires` copies a component's methods straight onto the page, where
they can collide with the page's own. A class decorated with `@page_proxy` is
mixed into a proxy object instead, reachable under the name the `AS` clause
gives it: `test_proxy:Leonard AS leo` puts every method of `Leonard` under
`self.leo`. `Leonard` is itself declared
`@page_proxy(inherites='test_proxy:BigBangProxy')`, which folds that class into
the SAME proxy - `fakeLaugh` below comes from there, not from `Leonard`.
"""


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                    test_proxy:Leonard AS leo
                """

    def test_0_simple(self, pane):
        """`makeBox` draws the box; `fakeLaugh`, inherited through the proxy, prints on the server console"""
        self.leo.makeBox(pane)
        self.leo.fakeLaugh()
