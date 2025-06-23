#!/usr/bin/env python3

from gnr.core.cli import GnrCliArgParse
from gnr.web.gnrwsgisite import GnrWsgiSite

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
    site = GnrWsgiSite(instance.instanceName)
    status = options.disable

    allowed_users = ','.join(options.allow_user)
    
    print("{} maintenance state for instance {}".format(
        status and "Enabling" or "Disabling",
        instance.instanceName), end='')

    if allowed_users and options.disable:
        print(f' - Allowed users: {allowed_users}')
    else:
        print('')
    site.register.gnrdaemon_proxy.setSiteInMaintenance(sitename=instance.instanceName,
                                                       status=status,
                                                       allowed_users=','.join(options.allow_user)
                                                       )
