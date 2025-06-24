#!/usr/bin/env python3

from gnr.core.cli import GnrCliArgParse
from gnr.web.gnrwsgisite import GnrWsgiSite

description = "Enable/disable site maintenance status"



def toggle_maintenance(instance_name, status, allowed_users=[]):
    site = GnrWsgiSite(instance_name)

    print("{} maintenance state for instance {}".format(
        status and "Enabling" or "Disabling",
        instance_name), end='')

    allowed_users = ','.join(allowed_users)
    
    if allowed_users and status:
        print(f' - Allowed users: {allowed_users}')
    else:
        print('')
        
    site.register.gnrdaemon_proxy.setSiteInMaintenance(sitename=instance_name,
                                                       status=status,
                                                       allowed_users=allowed_users)
    

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('instance_name')
    
    parser.add_argument("--disable", dest='disable',
                        action="store_false",
                        help="Disable maintenance status")
    parser.add_argument('--allow-user', action='append',
                        default=[],
                        help='Allowed user (can be repeated)')

    options = parser.parse_args()
    status = options.disable
    allowed_users = options.allow_user
    
    toggle_maintenance(options.instance_name,
                      options.disable,
                      options.allow_user)
