#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  Created by Saverio Porcari on 2025-01-14.
#  Copyright (c) 2025 Softwell. All rights reserved.

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union, Tuple

from gnr.lib.services import GnrBaseService
from gnr.core.gnrbag import Bag
import requests
from requests import RequestException
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method
import secrets


class Main(GnrBaseService):
    def __init__(self, parent=None, proxy_url=None, proxy_token=None, db_max_waiting=None, batch_size=None,
                 tenant_id=None, tenant_registered=None, disabled=None, client_base_url=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.proxy_url = proxy_url
        self.proxy_token = proxy_token
        self.db_max_waiting = db_max_waiting
        self.batch_size = batch_size
        self.tenant_id = tenant_id or self.parent.site_name
        self.tenant_registered = tenant_registered or False
        self.disabled = disabled or False
        self.client_base_url = client_base_url or self.parent.externalUrl('/email/mailproxy/mp_endpoint')

    # Command helpers
    def run_now(self):
        """Trigger an immediate fetch/send cycle."""
        return self._post("/commands/run-now")

    def suspend(self):
        """Suspend the remote dispatcher."""
        return self._post("/commands/suspend")

    def activate(self):
        """Activate the remote dispatcher."""
        return self._post("/commands/activate")

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

    def list_messages(self):
        """Return the full message queue with payload details."""
        response = self._get("/messages")
        if isinstance(response, dict):
            return response
        if isinstance(response, list):
            return {"ok": True, "messages": response}
        raise RuntimeError("Mail proxy /messages returned an unexpected payload")

    def pending_messages(self):
        """Fetch messages awaiting delivery."""
        response = self.list_messages()
        messages = response.get("messages") or []
        pending: List[Dict[str, Any]] = []
        for entry in messages:
            if entry.get("sent_ts") is not None or entry.get("error_ts") is not None:
                continue
            payload = entry.get("message") or {}
            pending.append(
                {
                    "id": entry.get("id"),
                    "account_id": entry.get("account_id"),
                    "to_addr": self._format_recipients(payload.get("to")),
                    "subject": payload.get("subject"),
                    "started_at": entry.get("created_at"),
                }
            )
        return {"ok": True, "pending": pending}

    def list_deferred(self):
        """Return messages deferred to a later time."""
        response = self.list_messages()
        messages = response.get("messages") or []
        deferred: List[Dict[str, Any]] = []
        for entry in messages:
            deferred_ts = entry.get("deferred_ts")
            if deferred_ts is None or entry.get("sent_ts") is not None:
                continue
            deferred.append(
                {
                    "id": entry.get("id"),
                    "account_id": entry.get("account_id"),
                    "deferred_time": self._format_timestamp(deferred_ts),
                    "retry_count": (entry.get("message") or {}).get("retry_count", 0),
                }
            )
        return {"ok": True, "deferred": deferred}

    def delete_messages(self, message_ids: List[str]):
        """Remove messages from the proxy queue using their identifiers."""
        if not isinstance(message_ids, list):
            raise ValueError("message_ids must be a list")
        return self._post("/commands/delete-messages", json={"ids": message_ids})

    def cleanup_messages(self, older_than_seconds: Optional[int] = None):
        """Manually trigger cleanup of reported messages older than retention period.

        Args:
            older_than_seconds: Remove messages reported more than this many seconds ago.
                              If None, uses the configured retention period (default 7 days).
                              Set to 0 to remove all reported messages immediately.

        Returns:
            dict: Response with 'ok' status and 'removed' count.
        """
        payload = {}
        if older_than_seconds is not None:
            payload["older_than_seconds"] = int(older_than_seconds)
        return self._post("/commands/cleanup-messages", json=payload)

    def get_tenant(self, tenant_id=None):
        """Get tenant information from the mail proxy.

        Args:
            tenant_id: Tenant identifier (defaults to self.tenant_id)

        Returns:
            dict: Tenant info if found, None if not found
        """
        tenant_id = tenant_id or self.tenant_id
        try:
            return self._get(f"/tenant/{tenant_id}")
        except RuntimeError:
            return None

    def register_tenant(self, username=None, password=None):
        """Register or update this genropy instance as a tenant on the mail proxy.

        Uses self.tenant_id and self.client_base_url for identification.

        Args:
            username: Username for Basic Auth
            password: Password for Basic Auth

        Returns:
            dict: Response with 'ok' status from proxy
        """
        payload = {
            "id": self.tenant_id,
            "client_base_url": self.client_base_url,
        }
        payload["client_sync_path"] = '/proxy_sync'
        payload["client_attachment_path"] = '/proxy_get_attachments'
        if username and password:
            payload["client_auth"] = {
                "method": "basic",
                "user": username,
                "password": password
            }
        return self._post("/tenant", json=payload)

    def delete_tenant(self, tenant_id=None):
        """Delete/unregister a tenant from the mail proxy.

        Args:
            tenant_id: Tenant identifier (defaults to self.tenant_id)

        Returns:
            dict: Response with 'ok' status from proxy
        """
        tenant_id = tenant_id or self.tenant_id
        if not tenant_id:
            raise ValueError("tenant_id is required")
        return self._delete(f"/tenant/{tenant_id}")

    def send_message(self, message: dict):
        """Enqueue a single message and immediately trigger a dispatch cycle."""
        if not isinstance(message, dict):
            raise ValueError("message must be a dictionary")
        enqueue_result = self.add_messages([message])
        if enqueue_result.get("ok"):
            try:
                self.run_now()
            except Exception:
                pass
        return enqueue_result

    def add_messages(self, messages: List[Dict[str, Any]], default_priority: Optional[int] = None):
        """Queue a batch of messages for the dispatcher and return the service reply."""
        if not isinstance(messages, list):
            raise ValueError("messages must be a list")
        payload: dict[str, object] = {"messages": messages}
        if default_priority is not None:
            payload["default_priority"] = default_priority
        response = self._post("/commands/add-messages", json=payload)
        if not isinstance(response, dict):
            raise RuntimeError("Mail proxy add-messages returned an unexpected payload")
        return response

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------
    def _request(self, method: str, path: str, *, json: Optional[Dict[str, Any]] = None,
                 params: Optional[Dict[str, Any]] = None, timeout: float = 10.0):
        if not self.proxy_url:
            raise RuntimeError("Proxy URL is not configured")
        url = f"{self.proxy_url.rstrip('/')}{path}"
        headers = {}
        if self.proxy_token:
            headers["X-API-Token"] = self.proxy_token
        try:
            response = requests.request(method, url, json=json, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
        except requests.HTTPError as exc:
            # Try to extract response body - it may contain useful data like rejected messages
            error_body = None
            try:
                error_body = exc.response.json() if exc.response is not None else None
            except (ValueError, AttributeError):
                pass
            # If response contains 'rejected' list, return it for normal processing
            # This allows partial success scenarios (some messages accepted, some rejected)
            if error_body and isinstance(error_body, dict) and 'rejected' in error_body:
                return error_body
            # Otherwise, raise with details if available
            error_detail = None
            if error_body:
                error_detail = error_body.get('detail') or error_body.get('error') or error_body.get('message')
                if not error_detail:
                    error_detail = str(error_body)
            if error_detail:
                raise RuntimeError(f"Mail proxy request failed: {exc.response.status_code} - {error_detail}") from exc
            raise RuntimeError(f"Mail proxy request failed: {exc}") from exc
        except RequestException as exc:
            raise RuntimeError(f"Mail proxy request failed: {exc}") from exc
        if response.status_code == 204 or not response.content:
            return {}
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("Mail proxy returned a non-JSON response") from exc
        if isinstance(data, dict) and 'status' not in data and 'ok' in data:
            data['status'] = 'ok' if data.get('ok') else 'error'
        return data

    def _get(self, path: str, **kwargs):
        return self._request("GET", path, **kwargs)

    def _post(self, path: str, **kwargs):
        return self._request("POST", path, **kwargs)

    def _patch(self, path: str, **kwargs):
        return self._request("PATCH", path, **kwargs)

    def _delete(self, path: str, **kwargs):
        return self._request("DELETE", path, **kwargs)

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
            "tenant_id": self.tenant_id,
            "host": account_dict.get("smtp_host"),
            "port": self._safe_int(account_dict.get("smtp_port")),
            "user": account_dict.get("smtp_username"),
            "password": account_dict.get("smtp_password"),
            "use_tls": self._safe_bool(account_dict.get("smtp_tls")),
            "ttl": self._safe_int(account_dict.get("proxy_ttl")),
            "limit_per_minute": self._safe_int(account_dict.get("proxy_limit_per_minute")),
            "limit_per_hour": self._safe_int(account_dict.get("proxy_limit_per_hour")),
            "limit_per_day": self._safe_int(account_dict.get("proxy_limit_per_day")),
            "limit_behavior": account_dict.get("proxy_limit_behavior"),
            "batch_size": self._safe_int(account_dict.get("proxy_batch_size")),
        }
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

    def _format_recipients(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, (list, tuple, set)):
            addresses = [addr for addr in value if addr]
        else:
            addresses = [value]
        return ", ".join(str(addr) for addr in addresses if addr)

    def _format_timestamp(self, value: Optional[int]) -> Optional[str]:
        if value in (None, ""):
            return None
        try:
            ts = int(value)
        except (TypeError, ValueError):
            return None
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    # -------------------------------------------------------------------------
    # Programmatic activation/deactivation
    # -------------------------------------------------------------------------
    def activateService(self):
        """Programmatically register this service with the mail proxy.

        This method can be called after a service record has been created
        with all required parameters (proxy_url, proxy_token, tenant_id).

        Usage:
            service = site.getService('mailproxy')
            result = service.activateService()

        Returns:
            dict: Result with 'ok', 'message', 'tenant_id', 'synced', 'failed'
        """
        if not self.proxy_url:
            return {'ok': False, 'error': 'Proxy URL not configured'}

        username, password = self._ensure_mailproxy_user()

        try:
            response = self.register_tenant(
                username=username,
                password=password
            )

            if not response.get('ok'):
                raise Exception(response.get('error') or 'Registration failed')

            service_tbl = self.parent.db.table('sys.service')
            with service_tbl.recordToUpdate(service_type=self.service_type,
                                            service_name=self.service_name) as rec:
                params = Bag(rec['parameters'])
                params['tenant_registered'] = True
                rec['parameters'] = params

            synced, failed = self._sync_mailproxy_accounts()

            return {
                'ok': True,
                'message': f'Tenant "{self.tenant_id}" registered',
                'tenant_id': self.tenant_id,
                'synced': synced,
                'failed': failed
            }
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def deactivateService(self):
        """Programmatically unregister this service from the mail proxy.

        Returns:
            dict: Result with 'ok' and 'message'
        """
        if not self.tenant_id:
            return {'ok': False, 'error': 'No tenant_id configured'}

        try:
            self.delete_tenant()
        except Exception:
            pass

        service_tbl = self.parent.db.table('sys.service')
        with service_tbl.recordToUpdate(service_type=self.service_type,
                                        service_name=self.service_name) as rec:
            params = Bag(rec['parameters'])
            params['tenant_registered'] = False
            rec['parameters'] = params

        return {'ok': True, 'message': f'Tenant "{self.tenant_id}" unregistered'}

    def _ensure_mailproxy_user(self):
        """Create or update the mailproxy system user with _MAILPROXY_ tag.

        Returns:
            tuple: (username, password)
        """
        username = 'mailproxy'
        password = secrets.token_urlsafe(32)

        db = self.parent.db
        user_tbl = db.table('adm.user')

        with user_tbl.recordToUpdate(username=username, insertMissing=True) as rec:
            rec['username'] = username
            rec['firstname'] = 'Mail'
            rec['lastname'] = 'Proxy'
            rec['email'] = 'mailproxy@system.local'
            rec['status'] = 'conf'
            rec['md5pwd'] = password
            rec['__syscode'] = username
            rec['id'] = rec['__syscode'].ljust(22,'_')
        user_id = rec['id']
        tag_id = db.table('adm.htag').sysRecord('_MAILPROXY_')['id']
        user_tag_tbl = db.table('adm.user_tag')
        with user_tag_tbl.recordToUpdate(user_id=user_id, tag_id=tag_id, insertMissing=True) as rec:
            rec['user_id'] = user_id
            rec['tag_id'] = tag_id

        db.commit()
        return username, password

    def _sync_mailproxy_accounts(self):
        """Sync all accounts with save_output_message=true to the proxy.

        Returns:
            tuple: (synced_count, failed_count)
        """
        account_tbl = self.parent.db.table('email.account')
        accounts = account_tbl.query(
            where='$save_output_message IS TRUE',
            columns='$id'
        ).fetch()

        synced, failed = 0, 0
        for account in accounts:
            try:
                response = self.add_account(account['id'])
                if response.get('ok'):
                    synced += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

        return synced, failed


class ServiceParameters(BaseComponent):
    def service_parameters(self, pane, datapath=None, service_name=None, **kwargs):
        fb = pane.formlet(datapath=datapath, cols=4)

        # Identifier field (tenant_id) - defaults to site_name if empty
        fb.textbox('^.tenant_id', lbl='!![en]Identifier',
                   placeholder=self.site.site_name,
                   disabled='^.tenant_registered')
        fb.textbox('^.proxy_url', lbl='!![en]Proxy url',
                   disabled='^.tenant_registered')
        fb.PasswordTextBox('^.proxy_token', lbl='!![en]API Token',
                   disabled='^.tenant_registered')

        fb.textbox('^.client_base_url', lbl='Client endpoint url', colspan=2,
                   placeholder=self.externalUrl('/email/mailproxy/mp_endpoint'))

        fb.numberTextbox('^.db_max_waiting', lbl='Db max waiting',
                         disabled='^.tenant_registered')
        fb.numberTextBox('^.batch_size', lbl='Batch size',
                         disabled='^.tenant_registered')

        status_box = fb.div(lbl='!![en]Proxy reachable')
        status_box.div('^#FORM.proxy_status', dtype='B', format='semaphore')
        status_box.dataRpc('#FORM.proxy_status', self.rpc_check_proxy_status,
                           proxy_url='^.proxy_url', _onBuilt=1)

        fb.checkbox('^.disabled', lbl='&nbsp;', label='!![en]Disable mail proxy connection')

        # Register button - solo se NON registrato
        register_btn = fb.button('!![en]Register',
                                 hidden='^.tenant_registered',
                                 lbl='&nbsp;')
        register_btn.dataRpc(self.rpc_register_tenant,
                             service_name=service_name,
                             _onResult="""
                                if(result.getItem('status') === 'ok'){
                                    genro.publish('floating_message', {message: result.getItem('message')});
                                } else {
                                    genro.publish('floating_message', {
                                        message: result.getItem('message'),
                                        messageType: 'error'
                                    });
                                }
                                this.form.reload();
                             """)

        # Unregister button - solo se registrato
        unregister_btn = fb.button('!![en]Unregister',
                                   hidden='^.tenant_registered?=!#v',
                                   lbl='&nbsp;')
        unregister_btn.dataRpc(self.rpc_unregister_tenant,
                               service_name=service_name,
                               _onResult="""
                                  if(result.getItem('status') === 'ok'){
                                      genro.publish('floating_message', {message: result.getItem('message')});
                                  } else {
                                      genro.publish('floating_message', {
                                          message: result.getItem('message'),
                                          messageType: 'error'
                                      });
                                  }
                                  this.form.reload();
                               """)

    @public_method
    def rpc_check_proxy_status(self, proxy_url=None):
        """Check if proxy server is reachable."""
        if not proxy_url:
            return None
        try:
            response = requests.get(f"{proxy_url.rstrip('/')}/health", timeout=5)
            return True if response.ok else None
        except Exception:
            return None

    @public_method
    def rpc_register_tenant(self, service_name=None):
        """Register tenant on mail proxy via UI."""
        service = self.getService('mailproxy', service_name)
        if not service:
            return Bag(dict(status='error', message='Mailproxy service not found'))

        result = service.activateService()
        self.db.commit()
        return Bag(dict(
            status='ok' if result.get('ok') else 'error',
            message=result.get('message') or result.get('error')
        ))

    @public_method
    def rpc_unregister_tenant(self, service_name=None):
        """Unregister tenant from mail proxy via UI."""
        service = self.getService('mailproxy', service_name)
        if not service:
            return Bag(dict(status='error', message='Mailproxy service not found'))

        result = service.deactivateService()
        self.db.commit()
        return Bag(dict(
            status='ok' if result.get('ok') else 'error',
            message=result.get('message') or result.get('error')
        ))
