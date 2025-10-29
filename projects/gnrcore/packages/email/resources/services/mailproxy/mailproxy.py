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


class Main(GnrBaseService):
    def __init__(self, parent=None, proxy_url=None, proxy_token=None, db_max_waiting=None, batch_size=None,**kwargs):
        super().__init__(parent, **kwargs)
        self.proxy_url = proxy_url
        self.proxy_token = proxy_token
        self.db_max_waiting = db_max_waiting
        self.batch_size = batch_size

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

    def add_volumes(self, volumes: List[Dict[str, Any]], storename: Optional[str] = None):
        """Register storage volumes on the proxy.

        Args:
            volumes: List of volume configurations with id, storage_type, and config
            storename: Store name for multitenant environments. If provided, volume IDs
                      will be prefixed with 'storename@' unless already prefixed.
                      If None, uses current store from database environment.

        Returns:
            dict: Response with 'ok' status and 'added' count
        """
        if not isinstance(volumes, list):
            raise ValueError("volumes must be a list")

        # Determine storename from parameter or current database environment
        if storename is None and hasattr(self.parent, 'db'):
            storename = self.parent.db.currentEnv.get('storename') or self.parent.db.rootstore

        # Prefix volume IDs with storename if in multitenant context
        if storename:
            prefixed_volumes = []
            for vol in volumes:
                vol_copy = dict(vol)
                vol_id = vol_copy.get('id', '')
                # Only add prefix if not already present
                if vol_id and '@' not in vol_id:
                    vol_copy['id'] = f"{storename}@{vol_id}"
                prefixed_volumes.append(vol_copy)
            volumes = prefixed_volumes

        return self._post("/volumes", json={"volumes": volumes})

    def add_volume_from_service(self, service_name: str, volume_id: Optional[str] = None,
                                storename: Optional[str] = None):
        """Register a storage volume from a genropy storage service.

        Args:
            service_name: Name of the storage service in genropy
            volume_id: Custom volume ID (defaults to service_name)
            storename: Store name for multitenant environments. If provided, volume_id
                      will be prefixed with 'storename@' to avoid conflicts across stores.
                      If None, uses current store from database environment.

        Returns:
            dict: Response with 'ok' status and 'added' count
        """
        storage_service = self.parent.getService('storage', service_name)
        if not storage_service:
            raise ValueError(f"Storage service '{service_name}' not found")

        # Determine storename from parameter or current database environment
        if storename is None and hasattr(self.parent, 'db'):
            storename = self.parent.db.currentEnv.get('storename') or self.parent.db.rootstore

        # Construct volume_id with storename prefix for multitenant scenarios
        base_volume_id = volume_id or service_name
        if storename:
            full_volume_id = f"{storename}@{base_volume_id}"
        else:
            full_volume_id = base_volume_id

        volume_config = self._convert_service_to_volume_config(storage_service, full_volume_id)
        return self.add_volumes([volume_config])

    def _convert_service_to_volume_config(self, service, volume_id: str) -> Dict[str, Any]:
        """Convert a genropy storage service to genro-storage volume configuration.

        Args:
            service: Genropy storage service instance
            volume_id: Volume identifier

        Returns:
            dict: Volume configuration for genro-mail-proxy API
        """
        implementation = getattr(service, 'service_implementation', None)

        if implementation == 'aws_s3':
            config = {
                'protocol': 's3',
                'base_path': f"{service.bucket}/{service.base_path}" if service.base_path else service.bucket,
                'key': service.aws_access_key_id,
                'secret': service.aws_secret_access_key,
            }
            if service.region_name:
                config['client_kwargs'] = {'region_name': service.region_name}
            if getattr(service, 'endpoint_url', None):
                config['endpoint_url'] = service.endpoint_url
            return {
                'id': volume_id,
                'storage_type': 'fsspec',
                'config': config
            }

        elif implementation == 'local':
            return {
                'id': volume_id,
                'storage_type': 'local',
                'config': {
                    'base_path': service.base_path
                }
            }

        elif implementation == 'sftp':
            return {
                'id': volume_id,
                'storage_type': 'fsspec',
                'config': {
                    'protocol': 'sftp',
                    'base_path': service.base_path,
                    'host': service.host,
                    'port': service.port,
                    'username': service.username,
                    'password': service.password
                }
            }

        elif implementation == 'http':
            return {
                'id': volume_id,
                'storage_type': 'fsspec',
                'config': {
                    'protocol': 'http',
                    'base_path': getattr(service, 'base_url', '')
                }
            }

        else:
            raise ValueError(f"Unsupported storage implementation: {implementation}")

    def list_volumes(self):
        """Return the storage volumes configured on the proxy."""
        return self._get("/volumes")

    def get_volume(self, volume_id: str):
        """Get details for a specific volume.

        Args:
            volume_id: The volume identifier

        Returns:
            dict: Volume configuration details
        """
        if not volume_id:
            raise ValueError("volume_id is required")
        return self._get(f"/volume/{volume_id}")

    def delete_volume(self, volume_id: str):
        """Remove a storage volume from the proxy.

        Args:
            volume_id: The volume identifier

        Returns:
            dict: Response with 'ok' status
        """
        if not volume_id:
            raise ValueError("volume_id is required")
        return self._delete(f"/volume/{volume_id}")

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
    def service_parameters(self,pane,datapath=None,service_name=None,**kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.textbox('^.proxy_url', lbl='!![en]Proxy url',width='30em')
        fb.PasswordTextBox('^.proxy_token', lbl='!![en]Token',width='30em')
        fb.numberTextbox('^.db_max_waiting',lbl='Db max waiting')
        fb.numberTextBox('^.batch_size',lbl='Batch size')
