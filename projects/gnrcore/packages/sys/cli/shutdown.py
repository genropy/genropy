#!/usr/bin/env python3
"""Announce an imminent shutdown to every connected user, or cancel it.

    gnr @<instance> sys shutdown init --time 5m --reason "Upgrading the application"
    gnr @<instance> sys shutdown cancel

Every open page shows the reason and a countdown from its next ping; a cancel
removes them and tells the users once. The gnrdaemon of the instance must be
running.
"""

import argparse
import sys

from gnr.app import pkglog as logger
from gnr.core.cli import GnrCliArgParse
from gnr.web.gnrshutdown import announce_shutdown, cancel_shutdown, parse_delay
from gnr.web.gnrwsgisite import GnrWsgiSite

description = "announce an imminent shutdown to the connected users, or cancel it"


def _delay(text):
    try:
        return parse_delay(text)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e))


def main(instance):
    parser = GnrCliArgParse(description=description)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init', help='announce the shutdown')
    init.add_argument('--time', required=True, type=_delay, dest='seconds',
                      help='time left before the shutdown: N or Ns seconds, Nm minutes, Nh hours')
    init.add_argument('--reason', required=True, help='the reason shown to the users')
    commands.add_parser('cancel', help='withdraw the announcement')
    options = parser.parse_args()

    try:
        store = GnrWsgiSite(instance.instanceName).main_register.globalStore()
        if options.command == 'init':
            deadline = announce_shutdown(store, options.seconds, options.reason)
        else:
            pending = cancel_shutdown(store)
    except Exception as e:
        logger.error('Unable to reach the gnrdaemon of %s: %s', instance.instanceName, e)
        sys.exit(2)
    if options.command == 'init':
        logger.warning('Shutdown announced for %s', deadline.strftime('%Y-%m-%d %H:%M:%S'))
    elif pending:
        logger.warning('Shutdown cancelled')
    else:
        logger.warning('No shutdown was pending')
