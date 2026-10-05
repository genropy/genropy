# -*- coding: utf-8 -*-

"""Long click and hold: the mouse events the framework adds to the DOM ones

A press released after more than 1500 ms marks the click event with
`_longClick`, and `_clickDuration` carries how long the button stayed down.
Holding the button for 1500 ms publishes a topic to the node under the
pointer before it is released: `clickAndHold` when the press starts within
500 ms of the previous release (click, then press and hold), `longMouseDown`
otherwise.
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_longclick(self, pane):
        """Click the green box short and long; press and hold the pink one, with and without a click just before"""
        pane.div('Click', background='lime',
                 connect_onclick="""this.setRelativeData('.last_click',
                                    ($1._longClick ? 'long ' : 'short ') + $1._clickDuration + ' ms');""")
        pane.div('^.last_click')
        pane.div('Click and hold', background='pink',
                 selfsubscribe_clickAndHold="this.setRelativeData('.last_topic', 'clickAndHold');",
                 selfsubscribe_longMouseDown="this.setRelativeData('.last_topic', 'longMouseDown');")
        pane.div('^.last_topic')
