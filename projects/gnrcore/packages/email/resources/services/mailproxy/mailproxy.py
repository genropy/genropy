#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  Created by Saverio Porcari on 2013-04-06.
#  Copyright (c) 2013 Softwell. All rights reserved.

from gnr.lib.services import GnrBaseService
from gnr.core.gnrbag import Bag
from typing import Optional, List, Dict, Any, Union, Tuple
import requests
from requests import RequestException
from gnr.web.gnrbaseclasses import BaseComponent


class Main(GnrBaseService):
    def __init__(self, parent=None, proxy_url=None, proxy_token=None, db_max_waiting=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.proxy_url = proxy_url
        self.proxy_token = proxy_token
        self.db_max_waiting = db_max_waiting

    # Command helpers
    def run_now(self):
        """Trigger an immediate fetch/send cycle."""
        return self._post("/commands/run-now")

    def suspend(self):
        """Suspend the remote scheduler."""
        return self._post("/commands/suspend")

    def activate(self):
        """Activate the remote scheduler."""
        return self._post("/commands/activate")

    def schedule(self, rules=None, active: Optional[bool] = None):
        """Replace the full scheduler configuration."""
        payload: Dict[str, Any] = {}
        if rules is not None:
            payload["rules"] = rules
        if active is not None:
            payload["active"] = bool(active)
        return self._post("/commands/rules", json=payload)

    def add_account(self, account: Union[dict, str, None]):
        """Register or update an SMTP account on the proxy."""
        payload, _account_id = self._resolve_account_payload(account)
        return self._post("/account", json=payload or {})

    def list_accounts(self):
        """Return the accounts known by the proxy."""
        return self._get("/accounts")

    def delete_account(self, account_id: str):
        """Remove an account from the proxy."""
        if not account_id:
            raise ValueError("account_id is required")
        return self._delete(f"/account/{account_id}")

    def pending_messages(self):
        """Fetch the pending message list from the proxy."""
        return self._get("/pending")

    def list_deferred(self):
        """Fetch messages currently deferred by the proxy."""
        return self._get("/deferred")

    def send_message(self, message: dict):
        """Send a single message immediately."""
        if not isinstance(message, dict):
            raise ValueError("message must be a dictionary")
        return self._post("/commands/send-message", json=message)

    def add_messages(self, messages: List[Dict[str, Any]], default_priority: Optional[int] = None):
        """Queue a batch of messages for the scheduler."""
        if not isinstance(messages, list):
            raise ValueError("messages must be a list")
        payload: dict[str, object] = {"messages": messages}
        if default_priority is not None:
            payload["default_priority"] = default_priority
        return self._post("/commands/add-messages", json=payload)

    def add_rule(self, rule: dict):
        """Add a scheduler rule."""
        if not isinstance(rule, dict):
            raise ValueError("rule must be a dictionary")
        return self._post("/commands/rules", json=rule)

    def delete_rule(self, rule_id: int):
        """Delete a scheduler rule."""
        if rule_id is None:
            raise ValueError("rule_id is required")
        return self._delete(f"/commands/rules/{rule_id}")

    def list_rules(self):
        """List scheduler rules."""
        return self._get("/commands/rules")

    def set_rule_enabled(self, rule_id: int, enabled: bool):
        """Enable or disable a scheduler rule."""
        if rule_id is None:
            raise ValueError("rule_id is required")
        return self._patch(f"/commands/rules/{rule_id}", json={"enabled": bool(enabled)})

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------
    def _request(self, method: str, path: str, *, json: Optional[Dict[str, Any]] = None,
                 params: Optional[Dict[str, Any]] = None, timeout: float = 10.0):
        self._ensure_configuration()
        if not self.proxy_url:
            raise RuntimeError("Proxy URL is not configured")
        url = f"{self.proxy_url.rstrip('/')}{path}"
        headers = {}
        if self.proxy_token:
            headers["X-API-Token"] = self.proxy_token
        try:
            response = requests.request(method, url, json=json, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
        except RequestException as exc:
            raise RuntimeError(f"Mail proxy request failed: {exc}") from exc
        if response.status_code == 204 or not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError("Mail proxy returned a non-JSON response") from exc

    def _get(self, path: str, **kwargs):
        return self._request("GET", path, **kwargs)

    def _post(self, path: str, **kwargs):
        return self._request("POST", path, **kwargs)

    def _patch(self, path: str, **kwargs):
        return self._request("PATCH", path, **kwargs)

    def _delete(self, path: str, **kwargs):
        return self._request("DELETE", path, **kwargs)

    def _ensure_configuration(self):
        if self.proxy_url:
            return
        if not hasattr(self.parent, 'db'):
            return
        service_tbl = self.parent.db.table('sys.service') if 'sys' in self.parent.gnrapp.packages else None
        if not service_tbl:
            return
        record = service_tbl.record(service_type=getattr(self, 'service_type', None),
                                    service_name=getattr(self, 'service_name', None),
                                    ignoreMissing=True)
        if not record:
            return
        params = Bag(record['parameters'] or {})
        self.proxy_url = params.getItem('proxy_url') or self.proxy_url
        self.proxy_token = params.getItem('proxy_token') or self.proxy_token
        self.db_max_waiting = params.getItem('db_max_waiting') or self.db_max_waiting

    def _resolve_account_payload(self, account: Union[dict, str, None]) -> Tuple[Dict[str, Any], Optional[str]]:
        if isinstance(account, dict):
            account_dict = account
            account_id = account_dict.get('id') or account_dict.get('account_id')
        elif account:
            account_tbl = self.parent.db.table('email.account')
            record = account_tbl.record(account, ignoreMissing=True)
            if not record:
                raise ValueError(f"Account '{account}' not found")
            account_dict = record.output('dict')
            account_id = account_dict.get('id')
        else:
            raise ValueError("Account definition is required")

        payload = {
            "id": account_dict.get("id"),
            "account_name": account_dict.get("account_name"),
            "host": account_dict.get("smtp_host"),
            "port": self._safe_int(account_dict.get("smtp_port")),
            "user": account_dict.get("smtp_username"),
            "password": account_dict.get("smtp_password"),
            "use_tls": self._safe_bool(account_dict.get("smtp_tls")),
            "use_ssl": self._safe_bool(account_dict.get("smtp_ssl")),
            "from_address": account_dict.get("smtp_from_address"),
            "system_bcc": account_dict.get("system_bcc"),
            "debug_address": account_dict.get("debug_address"),
            "system_debug_address": account_dict.get("debug_address"),
        }
        send_limit = account_dict.get("send_limit")
        if send_limit:
            payload["limit_per_day"] = self._safe_int(send_limit)
        timeout = account_dict.get("smtp_timeout")
        if timeout:
            payload["timeout"] = self._safe_int(timeout)
        clean_payload = {k: v for k, v in payload.items() if v not in (None, "")}
        return clean_payload, account_id

    def _safe_int(self, value):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _safe_bool(self, value):
        if value is None:
            return None
        return bool(value)
    
class ServiceParameters(BaseComponent):
    def service_parameters(self,pane,datapath=None,service_name=None,**kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.textbox('^.proxy_url', lbl='!![en]Proxy url',width='30em')
        fb.PasswordTextBox('^.proxy_token', lbl='!![en]Token',width='30em')
        fb.numberTextbox('^.db_max_waiting',lbl='Db max waiting')
