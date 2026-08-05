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

    
class DeepLinkMobileApp(BaseWebtool):
    mobile_os = None
    content_type = "application/json"

    def __call__(self, *args, **kwargs):
        app_config = self.site.get_mobile_app_config(self.mobile_os)
        if not app_config:
            raise Exception(f"mobile_app.{self.mobile_os} is not configured")
        return self.get_content(app_config)

class DeepLinkIOS(DeepLinkMobileApp):
    mobile_os = 'ios'

    def get_content(self, app_config):
        t = {
            "appIDs": [
                "{apple_app_id}.{apple_bundle_id}".format(**app_config),
                "{apple_team_id}.{apple_bundle_id}".format(**app_config)
            ],
            "components": [{"/" : "/*", "comment": "match all URLs"}]
        }
        for e in app_config.get('excluded_path', []):
            t['components'].insert(0, {"/": e["path"], "exclude": True, "comment": e["comment"]})

        return json.dumps({
            "applinks": {"apps": [], "details": [t]},
            "webcredentials": {"apps": t['appIDs'][:]}
        })

    @metadata(alias_url="/.well-known/apple-app-site-association")
    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)

class DeepLinkAndroid(DeepLinkMobileApp):
    mobile_os = 'android'

    def get_content(self, app_config):
        fingerprints = app_config['key_fingerprint'].split(',')
        return json.dumps([{
            "relation": [
                "delegate_permission/common.handle_all_urls",
                "delegate_permission/common.get_login_creds"
            ],
            "target": {
                "namespace": "android_app",
                "package_name": app_config['bundle_id'],
                "sha256_cert_fingerprints": fingerprints
            }
        }])

    @metadata(alias_url="/.well-known/assetlinks.json")
    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)
