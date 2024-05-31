#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  webtools to handle deeplinks/universal links support
#  for android and ios
#
#  Copyright (c) 2024 Softwell. All rights reserved.
#

import json

from gnr.web.gnrbaseclasses import BaseWebtool
from gnr.core.gnrdecorator import metadata

class DeepLink(BaseWebtool):
    def __call__(self, *args, **kwargs):
        apps_config = self.site.gnrapp.config.get(self.config_item, None)
        if not apps_config:
            raise Exception(f"{self.config_item} deeplinking support is not configured for this instance")
        return self.get_content(apps_config)

class DeepLinkIOS(DeepLink):
    config_item = "ios_apps"
    content_type = "text/plain"
    def get_content(self, apps_config):
        file_template = {
            "applinks": {
                "apps": [],
                "details": [
                    {
                        "appIDs": [],
                        "components": [
                            {
                                "/": "/*",
                                "comment": "match all URLs"
                            }
                        ]
                    }
                ]
            },
            "webcredentials": {
                "apps": [] #"{apple_app_id.{apple_app_bundle}", "{apple_team_id}.{apple_app_bundle}"]
            }
        }
        for a in apps_config:
            file_template['applinks']['details'][0]['appIDs'].append("{apple_app_id}.{apple_bundle_id}".format(**a.attr))
            file_template['applinks']['details'][0]['appIDs'].append("{apple_team_id}.{apple_bundle_id}".format(**a.attr))
            file_template['webcredentials']['apps'].append("{apple_app_id}.{apple_bundle_id}".format(**a.attr))
            file_template['webcredentials']['apps'].append("{apple_team_id}.{apple_bundle_id}".format(**a.attr))
        return json.dumps(file_template)
    
    @metadata(alias_url="/.well-known/apple-app-site-association")
    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)

class DeepLinkAndroid(DeepLink):
    content_type = "application/json"
    config_item = "android_apps"

    def get_content(self, apps_config):
        file_template = []
        for a in apps_config:
            app_template = {
                "relation": [
                    "delegate_permission/common.handle_all_urls"
                ],
                "target": {
                    "namespace": "android_app",
                    "package_name": "",
                    "sha256_cert_fingerprints": []
                }
            }

            app_template['target']['package_name'] = f"{a.attr['bundle_id']}"
            app_template['target']['sha256_cert_fingerprints'].append(f"{a.attr['key_fingerprint']}")
            file_template.append(app_template)
        return json.dumps(file_template)

    @metadata(alias_url="/.well-known/assetlinks.json")
    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)
