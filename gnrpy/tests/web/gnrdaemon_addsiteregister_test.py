"""Regression test for #1031.

``GnrDaemon.addSiteRegister`` raised ``UnboundLocalError`` on the
"site already registered" path, because ``sitename`` was derived only
inside the ``if`` branch while being referenced in the ``else`` branch.

A real ``GnrDaemon`` instance is not used here: its ``__init__`` starts a
``multiprocessing.Manager`` and the "already registered" branch touches
no other daemon state, so the method is exercised unbound against a
minimal fake, the same technique used in
``gnrwsgisite_folder_cleanup_test.py``.
"""

import logging

from gnr.web.daemon.handler import GnrDaemon


class _FakeDaemon:
    """Bag of attributes accessed by the "already registered" branch."""

    def __init__(self, siteregisters):
        self.siteregisters = siteregisters


def test_addsiteregister_already_registered_does_not_raise(caplog):
    fake = _FakeDaemon(siteregisters={'asp4': {}})

    with caplog.at_level(logging.INFO, logger='gnr.web'):
        GnrDaemon.addSiteRegister(fake, 'asp4')

    assert any('Site asp4 already existing' in r.getMessage()
               for r in caplog.records)


def test_addsiteregister_already_registered_with_domain_suffix(caplog):
    """domainIdentifier can carry a '|domain' suffix; the logged
    sitename must be the part before the pipe."""
    fake = _FakeDaemon(siteregisters={'asp4|example.com': {}})

    with caplog.at_level(logging.INFO, logger='gnr.web'):
        GnrDaemon.addSiteRegister(fake, 'asp4|example.com')

    assert any('Site asp4 already existing' in r.getMessage()
               for r in caplog.records)
