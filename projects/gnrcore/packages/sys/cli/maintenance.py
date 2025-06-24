#!/usr/bin/env python3

from gnr.core.cli import GnrCliArgParse
from gnr.web.cli.gnrmaintenance import toggle_maintenance

description = "Enable/disable site maintenance status"

def main(instance):
    parser = GnrCliArgParse(description=description)
    parser.add_argument("--disable", dest='disable',
                        action="store_false",
                        help="Disable maintenance status")
    parser.add_argument('--allow-user', action='append',
                        default=[],
                        help='Allowed user (can be repeated)')

    options = parser.parse_args()

    toggle_maintenance(instance.instanceName,
                       options.disable,
                       options.allow_user)
