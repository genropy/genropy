# -*- coding: utf-8 -*-

from gnr.core.cli import GnrCliArgParse
from gnr.web.gnrwsgisite import GnrWsgiSite
from gnr.dev.mobilechecks import MobileAppChecks
from gnr.dev import logger

description = "Verify deployment and configuration status for mobile apps"

def main():
    p = GnrCliArgParse(
        description=description
    )
    p.add_argument('site_name',
                   help="Name of the site to analyze")
    p.add_argument('base_url',
                   help="Base URL for deployed app")

    options = p.parse_args()

    site = GnrWsgiSite(options.site_name)
    mc = MobileAppChecks(site, options.base_url)
    result = mc.run()

    {'test_android_config': {'test': "'mobile_app.android' path presence in instance configuration ", 'result': False, 'description': 'Path configuration is missing'}, 'test_android_deeplinking': {'test': 'Verify Android deeplinking deployment', 'result': True, 'description': 'OK'}, 'test_ios_config': {'test': "'mobile_app.ios' path presence in instance configuration ", 'result': True, 'description': 'Path presence confirmed'}, 'test_ios_deeplinking': {'test': 'Verify IOS deeplinking deployment', 'result': True, 'description': 'OK'}, 'test_main_cordova_ios_assets': {'test': 'Verify Cordova IOS assets deployment', 'result': False, 'description': 'Not Found'}, 'test_multisite_cordova_ios_assets': {'test': 'Verify Multi-Site Cordova IOS assets deployment', 'result': False, 'description': 'Not Found'}}
    failed_counter = 0
    for test_name, payload in result.items():
        if not payload['result']:
            logger.error("Test %s failed: %s", test_name, payload['description'])
            failed_counter += 1
            
    if not failed_counter:
        print("All good!")
