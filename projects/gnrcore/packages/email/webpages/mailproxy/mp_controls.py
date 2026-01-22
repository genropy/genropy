# -*- coding: utf-8 -*-
#
#  Mail proxy dashboard page
#

from datetime import datetime

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrstring import fromJson


class GnrCustomWebPage(object):
    py_requires = 'public:Public,gnrcomponents/framegrid:FrameGrid'
    auth_main = 'admin'

    def windowTitle(self):
        return '!!Mail Proxy Dashboard'

    def main(self, root, **kwargs):
        bc = root.rootBorderContainer(datapath='main', title='!!Mail proxy dashboard')
        bc.css('.mp-status-error', 'color:#c00000; font-weight:bold;')

        status_pane = bc.contentPane(region='top', height='160px', datapath='.status', padding='6px')
        bar = status_pane.slotToolbar('run_now,suspend,activate,*,cleanup_messages,refresh,last_message')

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
            }else{
                SET main.status.error = null;
                var overview = result && result.getItem ? result.getItem('overview') : (result ? result.overview : null);
                if(overview){
                    SET main.data = overview;
                }
            }
        """

        bar.run_now.slotButton('!!Run now').dataRpc(
            'main.status.last_command',
            self.rpc_run_now,
            _onResult=shared_on_result
        )
        bar.suspend.slotButton('!!Suspend').dataRpc(
            'main.status.last_command',
            self.rpc_suspend,
            _onResult=shared_on_result
        )
        bar.activate.slotButton('!!Activate').dataRpc(
            'main.status.last_command',
            self.rpc_activate,
            _onResult=shared_on_result
        )
        bar.cleanup_messages.slotButton('!!Cleanup messages', iconClass='iconbox delete').dataRpc(
            'main.status.last_command',
            self.rpc_cleanup_messages,
            older_than_seconds='=_ask.older_than_seconds',
            _ask=dict(
                title='!!Cleanup reported messages',
                fields=[
                    dict(
                        name='older_than_seconds',
                        lbl='!!Retention (seconds)',
                        tag='numberTextBox',
                        tip='!!Leave empty to use configured retention (7 days). Set to 0 to remove all reported messages.',
                        width='15em'
                    )
                ]
            ),
            _onResult=shared_on_result
        )
        bar.refresh.slotButton('!!Refresh').dataRpc(
            'main.data',
            self.rpc_proxy_overview,
            _onResult=shared_on_result,
            _onStart=True
        )

        status_pane.dataController("""
            if(!overview){
                return;
            }
            SET .account_count = overview.getItem('status.account_count') || 0;
            SET .pending_count = overview.getItem('status.pending_count') || 0;
            SET .deferred_count = overview.getItem('status.deferred_count') || 0;
            SET .error_count = overview.getItem('status.error_count') || 0;
            SET .active = !!overview.getItem('status.active');
            SET .last_refresh = overview.getItem('status.last_refresh') || null;
            SET .error = overview.getItem('status.error') || null;
        """, overview='^main.data')
        bar.last_message.div('^main.status.last_command.message', margin_left='15px', font_style='italic')

        fb = status_pane.formbuilder(cols=4, border_spacing='8px', margin_top='10px', fld_readOnly=True)
        fb.textbox(value='^.last_refresh', lbl='!!Last refresh')
        fb.numberTextbox(value='^.account_count', lbl='!!Accounts')
        fb.numberTextbox(value='^.pending_count', lbl='!!Pending')
        fb.numberTextbox(value='^.deferred_count', lbl='!!Deferred')
        fb.numberTextbox(value='^.error_count', lbl='!!Errors')
        fb.checkbox(value='^.active', label='!!Dispatcher active', disabled=True)
        fb.div('^.error', colspan=4, _class='mp-status-error', hidden='^.error?=!#v')

        left_bc = bc.borderContainer(region='left', width='38%', splitter=True)
        accounts_grid = left_bc.contentPane(region='center').bagGrid(
            frameCode='mp_accounts',
            title='!!Accounts',
            storepath='main.data.accounts',
            struct=self.accounts_struct,
            pbl_classes=True,
            addrow=True,
            delrow=True,
            margin='6px',
        )
        accounts_bar = accounts_grid.top.bar.replaceSlots('addrow', 'add_account')
        accounts_bar.add_account.slotButton('!!Add account', iconClass='iconbox add_row').dataRpc(
            'main.status.last_command',
            self.rpc_add_account,
            account_id='=_ask.account_id',
            _ask=dict(
                title='!!Add account to mail proxy',
                fields=[
                    dict(
                        name='account_id',
                        lbl='!!Account',
                        tag='dbSelect',
                        dbtable='email.account',
                        columns='$account_name,$save_output_message',
                        condition='$save_output_message IS TRUE',
                        hasDownArrow=True,
                        validate_notnull=True
                    )
                ]
            ),
            _onResult=shared_on_result
        )
        accounts_grid.top.bar.replaceSlots('delrow', 'delete_account')
        accounts_grid.top.bar.delete_account.slotButton('!!Delete account', iconClass='iconbox delete_row').dataRpc(
            'main.status.last_command',
            self.rpc_delete_account,
            account_id='=.grid.selectedId',
            _if='account_id',
            _onResult=shared_on_result
        )

        right_bc = bc.borderContainer(region='center')
        right_bc.contentPane(region='center').bagGrid(
            frameCode='mp_messages',
            title='!!Messages',
            storepath='main.data.messages',
            struct=self.messages_struct,
            pbl_classes=True,
            addrow=False,
            delrow=False,
            margin='6px',
        )

    # -------------------------------------------------------------------------
    # Grid structures
    # -------------------------------------------------------------------------
    def accounts_struct(self, struct):
        rows = struct.view().rows()
        rows.cell('id', name='!!Account', width='12em')
        rows.cell('host', name='!!Host', width='12em')
        rows.cell('port', name='!!Port', width='6em', dtype='I')
        rows.cell('use_tls', name='!!TLS', width='6em', dtype='B')
        rows.cell('limit_per_minute', name='!!Per minute', width='7em', dtype='I')
        rows.cell('limit_per_hour', name='!!Per hour', width='7em', dtype='I')
        rows.cell('limit_per_day', name='!!Per day', width='7em', dtype='I')
        rows.cell('created_at', name='!!Created at', width='12em')

    def messages_struct(self, struct):
        rows = struct.view().rows()
        rows.cell('id', name='!!Message ID', width='14em')
        rows.cell('account_id', name='!!Account', width='12em')
        rows.cell('status', name='!!Status', width='10em')
        rows.cell('priority_label', name='!!Priority', width='10em')
        rows.cell('to_addr', name='!!Recipient', width='16em')
        rows.cell('subject', name='!!Subject', width='18em')
        rows.cell('created_at', name='!!Queued at', width='16em')
        rows.cell('deferred_time', name='!!Deferred until', width='16em')
        rows.cell('sent_ts', name='!!Sent at', width='16em')
        rows.cell('error_ts', name='!!Error at', width='16em')
        rows.cell('reported_ts', name='!!Reported at', width='16em')
        rows.cell('error', name='!!Error message', width='24em')
        rows.cell('retry_count', name='!!Retries', width='8em', dtype='I')

    # -------------------------------------------------------------------------
    # RPC helpers
    # -------------------------------------------------------------------------
    @public_method
    def rpc_proxy_overview(self):
        service = self._mailproxy_service()
        errors = []

        accounts = self._safe_service_call(service.list_accounts, 'accounts', 'Accounts', errors)
        messages = self._safe_service_call(service.list_messages, 'messages', 'Messages', errors)

        result = Bag()
        result['accounts'] = self._list_to_bag(accounts, 'id')
        decorated_messages = self._decorate_messages(messages)
        result['messages'] = self._list_to_bag(decorated_messages, 'id')

        status = Bag()
        status['account_count'] = len(accounts)
        status['pending_count'] = len([msg for msg in decorated_messages if msg.get('status') == 'pending'])
        status['deferred_count'] = len([msg for msg in decorated_messages if msg.get('status') == 'deferred'])
        status['error_count'] = len([msg for msg in decorated_messages if msg.get('status') == 'error'])
        status['active'] = True  # Always active, use suspend/activate commands to control
        status['last_refresh'] = self.db.table('email.account').newUTCDatetime()
        if errors:
            status['error'] = '\n'.join(errors)
        result['status'] = status
        return result

    @public_method
    def rpc_run_now(self):
        return self._command_wrapper('Run now', lambda svc: svc.run_now(), include_overview=True)

    @public_method
    def rpc_suspend(self):
        return self._command_wrapper('Suspend dispatcher', lambda svc: svc.suspend(), include_overview=True)

    @public_method
    def rpc_activate(self):
        return self._command_wrapper('Activate dispatcher', lambda svc: svc.activate(), include_overview=True)

    @public_method
    def rpc_cleanup_messages(self, older_than_seconds=None):
        def cleanup_call(svc):
            payload = {}
            if older_than_seconds is not None:
                try:
                    payload['older_than_seconds'] = int(older_than_seconds)
                except (TypeError, ValueError):
                    pass
            return svc.cleanup_messages(**payload)
        return self._command_wrapper('Cleanup messages', cleanup_call, include_overview=True)

    @public_method
    def rpc_add_account(self, account_id=None):
        if not account_id:
            return Bag(dict(ok=False, message='No account selected'))
        response = self._mailproxy_service().add_account(account_id)

        if isinstance(response, str):
            try:
                response = fromJson(response)
            except Exception as exc:
                return Bag(dict(status='error', message='Add account: invalid JSON response (%s)' % exc))
        response_status = self._response_status(response)
        if response_status != 'ok':
            message = self._response_message(response) or 'Unknown error'
            return Bag(dict(status='error', message='Add account: %s' % message))

        overview = self.rpc_proxy_overview()
        return Bag(dict(status='ok', message='Account registered on mail proxy', overview=overview))

    @public_method
    def rpc_delete_account(self, account_id=None):
        """Remove an account from the mail proxy.

        Args:
            account_id: The account ID to remove

        Returns:
            Bag with status, message, and updated overview
        """
        if not account_id:
            return Bag(dict(ok=False, message='No account ID provided'))

        try:
            response = self._mailproxy_service().delete_account(account_id)
        except Exception as exc:
            return Bag(dict(status='error', message='Delete account failed: %s' % exc))

        if isinstance(response, str):
            try:
                response = fromJson(response)
            except Exception as exc:
                return Bag(dict(status='error', message='Delete account: invalid JSON response (%s)' % exc))

        response_status = self._response_status(response)
        if response_status != 'ok':
            message = self._response_message(response) or 'Unknown error'
            return Bag(dict(status='error', message='Delete account: %s' % message))

        overview = self.rpc_proxy_overview()
        return Bag(dict(status='ok', message='Account removed from mail proxy', overview=overview))

    # -------------------------------------------------------------------------
    # Internal utilities
    # -------------------------------------------------------------------------
    def _mailproxy_service(self):
        service = self.getService('mailproxy','mailproxy')
        if service is None:
            raise RuntimeError('Mail proxy service is not configured')
        return service

    def _safe_service_call(self, func, result_key, label, errors):
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
        status = self._response_status(response)
        if status == 'error':
            errors.append('%s: %s' % (label, self._response_message(response) or 'Unknown error'))
            return []
        if isinstance(response, dict):
            if status == 'ok':
                return response.get(result_key) or []
            if result_key in response:
                return response.get(result_key) or []
        return response or []

    def _response_status(self, response):
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

    def _response_message(self, response):
        if response is None:
            return None
        if isinstance(response, Bag):
            return response.getItem('message') or response.getItem('error')
        if isinstance(response, dict):
            return response.get('message') or response.get('error')
        return None

    def _list_to_bag(self, items, key_field=None):
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

    def _decorate_messages(self, rows):
        result = []
        for row in rows or []:
            data = dict(row or {})
            payload = data.get('message') or {}
            priority = data.get('priority')
            entry = {
                'id': data.get('id'),
                'account_id': data.get('account_id'),
                'priority': priority,
                'priority_label': self._priority_label(priority),
                'to_addr': self._format_recipients(payload.get('to')),
                'subject': payload.get('subject'),
                'created_at': self._format_timestamp(data.get('created_at')),
                'deferred_time': self._format_timestamp(data.get('deferred_ts')),
                'sent_ts': self._format_timestamp(data.get('sent_ts')),
                'error_ts': self._format_timestamp(data.get('error_ts')),
                'reported_ts': self._format_timestamp(data.get('reported_ts')),
                'error': data.get('error'),
                'retry_count': payload.get('retry_count') or 0,
            }
            entry['status'] = self._status_from_entry(entry, data)
            result.append(entry)
        return result

    def _status_from_entry(self, entry, raw):
        if entry.get('error_ts') or raw.get('error'):
            return 'error'
        if entry.get('sent_ts'):
            return 'sent'
        deferred_ts = raw.get('deferred_ts') or raw.get('deferred_until')
        if deferred_ts:
            return 'deferred'
        return 'pending'

    def _priority_label(self, priority):
        label_map = {0: 'immediate', 1: 'high', 2: 'medium', 3: 'low'}
        try:
            priority_int = int(priority)
        except (TypeError, ValueError):
            return None
        return label_map.get(priority_int, str(priority_int))

    def _format_timestamp(self, value):
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

    def _format_recipients(self, value):
        if not value:
            return None
        if isinstance(value, (list, tuple, set)):
            addresses = [addr for addr in value if addr]
        else:
            addresses = [value]
        return ', '.join(str(addr) for addr in addresses if addr)

    def _command_wrapper(self, label, func, include_overview=False):
        service = self._mailproxy_service()
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
                    result['overview'] = self.rpc_proxy_overview()
                return result
            return Bag(dict(status='error', message='%s: %s' % (label, response.get('error', 'Unknown error'))))
        result = Bag(dict(status='ok', message='%s completed successfully' % label))
        if include_overview:
            result['overview'] = self.rpc_proxy_overview()
        return result
