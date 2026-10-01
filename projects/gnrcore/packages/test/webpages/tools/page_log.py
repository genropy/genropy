# -*- coding: utf-8 -*-

"""The durable trace of the site registers: connections and served pages

The site register lives in memory and dies with the daemon; `adm.connection` and
`adm.served_page` are what survives it - one row per browser connection, one per
page served inside it, each closed with an `end_ts` and an `end_reason` when it
goes. Each case embeds the standard table handler of one of them, so the log can
be read without leaving the test page.

Both tables carry `checkpref='adm.dev.connection_log_enabled'`: set the adm
preference `Connection log` to `Connection and pages` (`Connection Only` leaves
`adm.served_page` empty) and restart the site, which reads it once. While it is
off the tables are neither written nor served, and each iframe shows the error
`Table adm.connection not allowed by preference` (or `adm.served_page`) instead
of a grid - a setup matter, not a broken page.
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_1_conn(self, pane):
        """Connections: one row per browser connection, with its user, ip and user agent"""
        pane.iframe(src='/sys/thpage/adm/connection', height='500px', width='900px',
                    border='1px solid silver')

    def test_2_sp(self, pane):
        """Served pages: one row per page opened inside a connection"""
        pane.iframe(src='/sys/thpage/adm/served_page', height='500px', width='900px',
                    border='1px solid silver')
