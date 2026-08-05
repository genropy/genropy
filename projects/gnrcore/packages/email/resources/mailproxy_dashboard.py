# -*- coding: utf-8 -*-

from datetime import datetime

import requests

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrstring import fromJson
from gnr.web.gnrbaseclasses import BaseComponent


class MailProxyDashboard(BaseComponent):

    def mp_proxy_layout(self, bc):
        status_pane = bc.contentPane(region='top', height='40px', datapath='.status', padding='6px')
        shared_on_result = """
            var status = result && result.getItem ? result.getItem('status') : (result ? result.status : null);
            if(!status && result){
                var okValue = result && result.getItem ? result.getItem('ok') : (result ? result.ok : null);
                if(okValue === true){
                    status = 'ok';
                }else if(okValue === false){
                    status = 'error';
                }
            }
            var message = result && result.getItem ? result.getItem('message') : (result ? result.message : null);
            if(status !== 'ok'){
                SET main.status.error = message || null;
                if(message){
                    genro.publish('floating_message', {message: message, messageType: 'error'});
                }
            }else{
                SET main.status.error = null;
                if(message){
                    genro.publish('floating_message', {message: message});
                }
                var overview = result && result.getItem ? result.getItem('overview') : (result ? result.overview : null);
                if(overview){
                    SET main.data = overview;
                }
            }
        """

        controls = status_pane.div(style='display:flex; gap:10px; align-items:center;')
        for lbl, val_path in [
            ('!!Last refresh', '.last_refresh'),
            ('!!Accounts', '.account_count'),
            ('!!Pending', '.pending_count'),
            ('!!Deferred', '.deferred_count'),
            ('!!Errors', '.error_count'),
        ]:
            block = controls.div(style='padding:4px 10px; background:#f4f4f4; border-radius:3px; text-align:center; min-width:80px;')
            block.div(lbl, style='font-size:0.75em; color:#888; white-space:nowrap;')
            block.div('^%s' % val_path, style='font-size:1.3em; font-weight:bold;')
        controls.div(style='flex:1;')
        proxy_status = controls.div()
        proxy_status.div('^.proxy_reachable', dtype='B', format='semaphore')
        proxy_status.dataRpc('.proxy_reachable', self.mp_rpc_check_proxy_status, _onBuilt=1)
        controls.slotButton('!!Run now').dataRpc(
            'main.status.last_command', self.mp_rpc_run_now, _onResult=shared_on_result)
        controls.slotButton('!!Cleanup sent').dataRpc(
            'main.status.last_command',
            self.mp_rpc_cleanup_messages,
            older_than_seconds='=_ask.older_than_seconds',
            _ask=dict(
                title='!!Cleanup reported messages',
                fields=[
                    dict(
                        name='older_than_seconds',
                        lbl='!!Retention (seconds)',
                        tag='numberTextBox',
                        tip='!!Leave empty to use configured retention (7 days). Set to 0 to remove all reported messages.',
                        width='15em',
                        value=1
                    )
                ]
            ),
            _onResult=shared_on_result
        )
        controls.slotButton('!!Refresh').dataRpc(
            'main.data', self.mp_rpc_proxy_overview, _onResult=shared_on_result, _onStart=True)

        status_pane.dataController("""
            if(!overview){
                return;
            }
            SET .account_count = overview.getItem('status.account_count') || 0;
            SET .pending_count = overview.getItem('status.pending_count') || 0;
            SET .deferred_count = overview.getItem('status.deferred_count') || 0;
            SET .error_count = overview.getItem('status.error_count') || 0;
            SET .last_refresh = overview.getItem('status.last_refresh') || null;
            SET .error = overview.getItem('status.error') || null;
        """, overview='^main.data')
        status_pane.div('^.error', margin_top='6px', style='color:#c00000; font-weight:bold;', hidden='^.error?=!#v')

        left_bc = bc.borderContainer(region='left', width='38%', splitter=True)
        left_bc.contentPane(region='center').bagGrid(
            frameCode='mp_accounts',
            title='!!Accounts',
            storepath='main.data.accounts',
            struct=self.mp_accounts_struct,
            pbl_classes=True,
            addrow=False,
            delrow=False,
            margin='6px',
        )

        right_bc = bc.borderContainer(region='center')
        right_bc.contentPane(region='center').bagGrid(
            frameCode='mp_messages',
            title='!!Messages',
            storepath='main.data.messages',
            struct=self.mp_messages_struct,
            pbl_classes=True,
            addrow=False,
            delrow=False,
            margin='6px',
        )

    # -------------------------------------------------------------------------
    # Grid structures
    # -------------------------------------------------------------------------
    def mp_accounts_struct(self, struct):
        rows = struct.view().rows()
        rows.cell('id', name='!!Account', width='12em')
        rows.cell('host', name='!!Host', width='18em')
        rows.cell('port', name='!!Port', width='4em', dtype='I')
        rows.cell('use_tls', name='!!TLS', width='4em', dtype='B')
        rows.cell('limit_per_minute', name='!!/ min', width='5em', dtype='I')
        rows.cell('limit_per_hour', name='!!/ hour', width='5em', dtype='I')
        rows.cell('limit_per_day', name='!!/ day', width='5em', dtype='I')
        rows.cell('created_at', name='!!Created at', width='11em')

    def mp_messages_struct(self, struct):
        rows = struct.view().rows()
        rows.cell('id', name='!!ID', width='8em')
        rows.cell('account_id', name='!!Account', width='12em')
        rows.cell('status', name='!!Status', width='6em')
        rows.cell('priority_label', name='!!Priority', width='6em')
        rows.cell('to_addr', name='!!Recipient', width='14em')
        rows.cell('subject', name='!!Subject', width='16em')
        rows.cell('created_at', name='!!Queued at', width='11em')
        rows.cell('deferred_time', name='!!Deferred until', width='11em')
        rows.cell('sent_ts', name='!!Sent at', width='11em')
        rows.cell('error_ts', name='!!Error at', width='11em')
        rows.cell('reported_ts', name='!!Reported at', width='11em')
        rows.cell('error', name='!!Error message', width='18em')
        rows.cell('retry_count', name='!!Retries', width='5em', dtype='I')

    # -------------------------------------------------------------------------
    # RPC methods
    # -------------------------------------------------------------------------
    @public_method
    def mp_rpc_proxy_overview(self):
        service = self._mp_mailproxy_service()
        errors = []
        accounts = self._mp_safe_service_call(service.list_accounts, 'accounts', 'Accounts', errors)
        messages = self._mp_safe_service_call(service.list_messages, 'messages', 'Messages', errors)
        result = Bag()
        result['accounts'] = self._mp_list_to_bag(accounts, 'id')
        decorated_messages = self._mp_decorate_messages(messages)
        result['messages'] = self._mp_list_to_bag(decorated_messages, 'id')

        status = Bag()
        status['account_count'] = len(accounts)
        status['pending_count'] = len([msg for msg in decorated_messages if msg.get('status') == 'pending'])
        status['deferred_count'] = len([msg for msg in decorated_messages if msg.get('status') == 'deferred'])
        status['error_count'] = len([msg for msg in decorated_messages if msg.get('status') == 'error'])
        status['last_refresh'] = self.db.table('email.account').newUTCDatetime().strftime('%Y-%m-%d %H:%M:%S')
        if errors:
            status['error'] = '\n'.join(errors)
        result['status'] = status
        return result

    @public_method
    def mp_rpc_run_now(self):
        return self._mp_command_wrapper('Run now', lambda svc: svc.run_now(), include_overview=True)

    @public_method
    def mp_rpc_cleanup_messages(self, older_than_seconds=None):
        def cleanup_call(svc):
            payload = {}
            if older_than_seconds is not None:
                try:
                    payload['older_than_seconds'] = int(older_than_seconds)
                except (TypeError, ValueError):
                    pass
            return svc.cleanup_messages(**payload)
        return self._mp_command_wrapper('Cleanup messages', cleanup_call, include_overview=True)

    @public_method
    def mp_rpc_check_proxy_status(self):
        try:
            service = self._mp_mailproxy_service()
            proxy_url = service.proxy_url
            if not proxy_url:
                return None
            response = requests.get(f"{proxy_url.rstrip('/')}/health", timeout=5)
            return True if response.ok else None
        except Exception:
            return None

    # -------------------------------------------------------------------------
    # Internal utilities
    # -------------------------------------------------------------------------
    def _mp_mailproxy_service(self):
        service = self.getService('mailproxy', 'mailproxy')
        if service is None:
            raise RuntimeError('Mail proxy service is not configured')
        return service

    def _mp_safe_service_call(self, func, result_key, label, errors):
        try:
            response = func()
        except Exception as exc:
            errors.append('%s: %s' % (label, exc))
            return []
        if isinstance(response, str):
            try:
                response = fromJson(response)
            except Exception as exc:
                errors.append('%s: invalid JSON response (%s)' % (label, exc))
                return []
        if isinstance(response, Bag):
            response = response.asDict()
        status = self._mp_response_status(response)
        if status == 'error':
            errors.append('%s: %s' % (label, self._mp_response_message(response) or 'Unknown error'))
            return []
        if isinstance(response, dict):
            if status == 'ok':
                return response.get(result_key) or []
            if result_key in response:
                return response.get(result_key) or []
        return response or []

    def _mp_response_status(self, response):
        if response is None:
            return None
        if isinstance(response, Bag):
            status = response.getItem('status')
            if status:
                return status
            ok_value = response.getItem('ok')
        elif isinstance(response, dict):
            status = response.get('status')
            if status:
                return status
            ok_value = response.get('ok')
        else:
            ok_value = None
        if ok_value is True:
            return 'ok'
        if ok_value is False:
            return 'error'
        return None

    def _mp_response_message(self, response):
        if response is None:
            return None
        if isinstance(response, Bag):
            return response.getItem('message') or response.getItem('error')
        if isinstance(response, dict):
            return response.get('message') or response.get('error')
        return None

    def _mp_list_to_bag(self, items, key_field=None):
        if isinstance(items, Bag):
            return items
        if isinstance(items, str):
            bag = Bag()
            bag.fromJson(items)
            return bag
        bag = Bag()
        if not items:
            return bag
        for idx, row in enumerate(items):
            row = row or {}
            entry = Bag(row)
            item_key = row.get(key_field) if key_field and row.get(key_field) else str(idx)
            bag.setItem(item_key, entry)
        return bag

    def _mp_decorate_messages(self, rows):
        result = []
        for row in rows or []:
            data = dict(row or {})
            payload = data.get('message') or {}
            priority = data.get('priority')
            entry = {
                'id': data.get('id'),
                'account_id': data.get('account_id'),
                'priority': priority,
                'priority_label': self._mp_priority_label(priority),
                'to_addr': self._mp_format_recipients(payload.get('to')),
                'subject': payload.get('subject'),
                'created_at': self._mp_format_timestamp(data.get('created_at')),
                'deferred_time': self._mp_format_timestamp(data.get('deferred_ts')),
                'sent_ts': self._mp_format_timestamp(data.get('sent_ts')),
                'error_ts': self._mp_format_timestamp(data.get('error_ts')),
                'reported_ts': self._mp_format_timestamp(data.get('reported_ts')),
                'error': data.get('error'),
                'retry_count': payload.get('retry_count') or 0,
            }
            entry['status'] = self._mp_status_from_entry(entry, data)
            result.append(entry)
        return result

    def _mp_status_from_entry(self, entry, raw):
        if entry.get('error_ts') or raw.get('error'):
            return 'error'
        if entry.get('sent_ts'):
            return 'sent'
        deferred_ts = raw.get('deferred_ts') or raw.get('deferred_until')
        if deferred_ts:
            return 'deferred'
        return 'pending'

    def _mp_priority_label(self, priority):
        label_map = {0: 'immediate', 1: 'high', 2: 'medium', 3: 'low'}
        try:
            priority_int = int(priority)
        except (TypeError, ValueError):
            return None
        return label_map.get(priority_int, str(priority_int))

    def _mp_format_timestamp(self, value):
        if not value:
            return None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                return value
        try:
            return datetime.fromtimestamp(int(value)).strftime('%Y-%m-%d %H:%M:%S')
        except (TypeError, ValueError):
            return None

    def _mp_format_recipients(self, value):
        if not value:
            return None
        if isinstance(value, (list, tuple, set)):
            addresses = [addr for addr in value if addr]
        else:
            addresses = [value]
        return ', '.join(str(addr) for addr in addresses if addr)

    def _mp_command_wrapper(self, label, func, include_overview=False):
        service = self._mp_mailproxy_service()
        try:
            response = func(service)
        except Exception as exc:
            return Bag(dict(status='error', message='%s failed: %s' % (label, exc)))
        if isinstance(response, dict):
            status = response.get('status') or ('ok' if response.get('ok') else None)
            if status == 'ok':
                result = Bag(response)
                result['status'] = 'ok'
                if not result.get('message'):
                    result['message'] = '%s completed successfully' % label
                if include_overview:
                    result['overview'] = self.mp_rpc_proxy_overview()
                return result
            return Bag(dict(status='error', message='%s: %s' % (label, response.get('error', 'Unknown error'))))
        result = Bag(dict(status='ok', message='%s completed successfully' % label))
        if include_overview:
            result['overview'] = self.mp_rpc_proxy_overview()
        return result
