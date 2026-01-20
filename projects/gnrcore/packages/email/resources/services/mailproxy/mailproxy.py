#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  Created by Saverio Porcari on 2013-04-06.
#  Copyright (c) 2013 Softwell. All rights reserved.

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
                 **kwargs):
        super().__init__(parent, **kwargs)
        self.proxy_url = proxy_url
        self.proxy_token = proxy_token
        self.db_max_waiting = db_max_waiting
        self.batch_size = batch_size
        self.tenant_id = self.parent.site_name

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

    def register_tenant(self, tenant_id, client_sync_url, client_attachment_url=None,
                        client_sync_user=None, client_sync_password=None):
        """Register or update this genropy instance as a tenant on the mail proxy.

        Args:
            tenant_id: Unique tenant identifier
            client_sync_url: Callback URL for delivery reports
            client_attachment_url: URL for attachment downloads
            client_sync_user: Username for Basic Auth
            client_sync_password: Password for Basic Auth

        Returns:
            dict: Response with 'ok' status from proxy
        """
        payload = {
            "id": tenant_id,
            "client_sync_url": client_sync_url,
        }
        if client_attachment_url:
            payload["client_attachment_url"] = client_attachment_url
        if client_sync_user and client_sync_password:
            payload["client_auth"] = {
                "method": "basic",
                "user": client_sync_user,
                "password": client_sync_password
            }
        return self._post("/tenant", json=payload)

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

class ServiceParameters(BaseComponent):
    def service_parameters(self, pane, datapath=None, service_name=None, **kwargs):
        fb = pane.formlet(datapath=datapath,cols=3)
        fb.textbox('^.proxy_url', lbl='!![en]Proxy url')
        fb.PasswordTextBox('^.proxy_token', lbl='!![en]API Token')
        btn = fb.button('!![en]Register Tenant', iconClass="^.tenant_registered?=#v?'greenLight' : 'redLight'",lbl='&nbsp;')

        btn.dataRpc(self.rpc_register_tenant,
                     service_name=service_name,
                     _onResult="""
                        if(result.getItem('status') === 'ok'){
                            genro.publish('floating_message', {message: result.getItem('message')});
                            this.form.reload();
                        } else {
                            genro.publish('floating_message', {
                                message: result.getItem('message'),
                                messageType: 'error'
                            });
                        }
                     """)


        fb.numberTextbox('^.db_max_waiting', lbl='Db max waiting')
        fb.numberTextBox('^.batch_size', lbl='Batch size')
        fb.div()

    


        # Register tenant button

    @public_method
    def rpc_register_tenant(self, service_name=None):
        """Register tenant on mail proxy and sync accounts."""
        # Get mailproxy service
        service = self.getService('mailproxy', service_name)
        if not service:
            return Bag(dict(status='error', message='Mailproxy service not found'))

        # Verify proxy_url is configured
        if not service.proxy_url:
            return Bag(dict(status='error', message='Proxy URL not configured'))

        # Generate tenant_id from site_name
        tenant_id = self.site.site_name

        # Create/update mailproxy system user with _MAILPROXY_ tag
        username, password = self._ensure_mailproxy_user()

        # Build callback URLs for RPC endpoints
        client_sync_url = self.site.externalUrl('/email/mailproxy/mp_endpoint')
        client_attachment_url = self.site.externalUrl('/email/mailproxy/mp_endpoint/proxy_get_attachments')

        try:
            # Register/update tenant on proxy with Basic Auth credentials
            response = service.register_tenant(
                tenant_id=tenant_id,
                client_sync_url=client_sync_url,
                client_attachment_url=client_attachment_url,
                client_sync_user=username,
                client_sync_password=password
            )

            if not response.get('ok'):
                error_msg = response.get('error') or 'Registration failed'
                return Bag(dict(status='error', message=f'Proxy error: {error_msg}'))

            # Save registration status to service parameters
            service_tbl = self.db.table('sys.service')
            service_record = service_tbl.record(
                service_type='mailproxy',
                service_name=service_name,
                ignoreMissing=True
            ).output('record')

            if service_record:
                params = Bag(service_record.get('parameters') or {})
                params['tenant_registered'] = True

                with service_tbl.recordToUpdate(service_record['service_identifier']) as rec:
                    rec['parameters'] = params
                self.db.commit()

            # Sync accounts with use_mailproxy=true
            synced, failed = self._sync_mailproxy_accounts(service)

            return Bag(dict(
                status='ok',
                message=f'Tenant "{tenant_id}" registered. Accounts: {synced} synced, {failed} failed',
                tenant_id=tenant_id
            ))

        except Exception as e:
            return Bag(dict(status='error', message=f'Error: {str(e)}'))

    def _ensure_mailproxy_user(self):
        """Create or update the mailproxy system user with _MAILPROXY_ tag.

        Returns:
            tuple: (username, password)
        """
        username = 'mailproxy'
        password = secrets.token_urlsafe(32)

        user_tbl = self.db.table('adm.user')
        user_record = user_tbl.record(username=username, ignoreMissing=True).output('dict')

        if user_record:
            # Update existing user with new password
            with user_tbl.recordToUpdate(user_record['id']) as rec:
                rec['md5pwd'] = password
        else:
            # Create new system user
            user_record = user_tbl.newrecord(
                username=username,
                firstname='Mail',
                lastname='Proxy',
                email='mailproxy@system.local',
                status='conf',
                md5pwd=password
            )
            user_tbl.insert(user_record)

        # Ensure user has _MAILPROXY_ tag
        self._ensure_user_tag(user_record['id'], '_MAILPROXY_')
        self.db.commit()

        return username, password

    def _ensure_user_tag(self, user_id, tag_code):
        """Ensure user has the specified tag."""
        htag_tbl = self.db.table('adm.htag')
        user_tag_tbl = self.db.table('adm.user_tag')

        # Find the tag
        tag_record = htag_tbl.record(
            where='$hierarchical_code=:tc OR $__syscode=:tc',
            tc=tag_code,
            ignoreMissing=True
        ).output('dict')

        if not tag_record:
            return

        # Check if user already has this tag
        existing = user_tag_tbl.record(
            user_id=user_id,
            tag_id=tag_record['id'],
            ignoreMissing=True
        ).output('dict')

        if not existing:
            user_tag_tbl.insert(user_tag_tbl.newrecord(
                user_id=user_id,
                tag_id=tag_record['id']
            ))

    def _sync_mailproxy_accounts(self, service):
        """Sync all accounts with use_mailproxy=true to the proxy.

        Returns:
            tuple: (synced_count, failed_count)
        """
        account_tbl = self.db.table('email.account')
        accounts = account_tbl.query(
            where='$use_mailproxy IS TRUE',
            columns='$id'
        ).fetch()

        synced, failed = 0, 0
        for account in accounts:
            try:
                # add_account already handles payload conversion
                response = service.add_account(account['id'])
                if response.get('ok'):
                    synced += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

        return synced, failed
