#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  webtools to handle deeplinks/universal links support
#  for android and ios
#
#  Copyright (c) 2024 Softwell. All rights reserved.
#
import copy
import json

from gnr.web.gnrbaseclasses import BaseWebtool
from gnr.core.gnrdecorator import metadata

class WKUFile(BaseWebtool):
    def __call__(self, *args, **kwargs):
        apps_config = self.site.gnrapp.config.getNode(self.config_item, None)
        if not apps_config:
            raise Exception(f"{self.config_item} wku support is not configured for this instance")
        return self.get_content([apps_config])

class SecurityTxt(WKUFile):
    config_item = 'wku.security_txt'
    content_type = "text/plain"
    
    def get_content(self, configs):
        payload = []
        for config in configs:
            for item in config.value:
                payload.append([item.tag, item.value])
        return "".join(f"{k.capitalize()}: {v}\n" for k, v in payload)
    
    @metadata(alias_url="/.well-known/security.txt")
    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


class RobotsTxt(WKUFile):
    config_item = 'wku.robots_txt'
    content_type = "text/plain"

    def get_content(self, configs):
        payload = []
        for config in configs:
            for item in config.value:
                if item.tag == "user-agent":
                    agent_name = item.attr.get("name", None)
                    if agent_name:
                        payload.append(f"User-agent: {agent_name}")
                        for action in item.value:
                            payload.append(f"{action.tag.capitalize()}: {action.value}")
                else:
                    payload.append(f"{item.tag.capitalize()}: {item.value}")
                payload.append('')
        return "\n".join(payload)

    @metadata(alias_url="/robots.txt")
    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)

    
class DeepLinkIOS(WKUFile):
    config_item = "mobile_app.ios"
    content_type = "text/plain"
    def get_content(self, apps_config):
        app_template = {
            "appIDs": [],
            "components": [
                {
                    "/": "/*",
                    "comment": "match all URLs"
                }
            ]
        }

        file_template = {
            "applinks": {
                "apps": [],
                "details": [
                ]
            },
            "webcredentials": {
                "apps": [] 
            }
        }
        for a in apps_config:
            t = copy.deepcopy(app_template)
            t['appIDs'].append("{apple_app_id}.{apple_bundle_id}".format(**a.attr))
            t['appIDs'].append("{apple_team_id}.{apple_bundle_id}".format(**a.attr))
            file_template['webcredentials']['apps'].append("{apple_app_id}.{apple_bundle_id}".format(**a.attr))
            file_template['webcredentials']['apps'].append("{apple_team_id}.{apple_bundle_id}".format(**a.attr))
            
            exclusions = a.getValue("excluded_path")
            if exclusions:
                for e in exclusions:
                    new_exclusion = {
                        "/": e.attr["path"],
                        "exclude": True,
                        "comment": e.attr["comment"]
                        }
                    t['components'].insert(0, new_exclusion)

            file_template['applinks']['details'].append(t)
            
        return json.dumps(file_template)
    
    @metadata(alias_url="/.well-known/apple-app-site-association")
    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)

class DeepLinkAndroid(WKUFile):
    content_type = "application/json"
    config_item = "mobile_app.android"

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
