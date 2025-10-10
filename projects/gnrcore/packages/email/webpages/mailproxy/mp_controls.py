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
        bar = status_pane.slotToolbar('run_now,suspend,activate,*,add_account,refresh,last_message')

        shared_on_result = """
            var status = result && result.getItem ? result.getItem('status') : (result ? result.status : null);
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
        bar.add_account.slotButton('!!Add account').dataRpc(
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
        fb.checkbox(value='^.active', label='!!Scheduler active', disabled=True)
        fb.div('^.error', colspan=4, _class='mp-status-error', hidden='^.error?=!#v')

        left_bc = bc.borderContainer(region='left', width='38%', splitter=True)
        left_bc.contentPane(region='center').bagGrid(
            frameCode='mp_accounts',
            title='!!Accounts',
            storepath='main.data.accounts',
            struct=self.accounts_struct,
            pbl_classes=True,
            addrow=False,
            delrow=False,
            margin='6px',
        )
        left_bc.contentPane(region='bottom', height='45%', splitter=True).bagGrid(
            frameCode='mp_rules',
            title='!!Scheduler rules',
            storepath='main.data.rules',
            struct=self.rules_struct,
            pbl_classes=True,
            addrow=False,
            delrow=False,
            margin='6px',
        )

        right_bc = bc.borderContainer(region='center')
        right_bc.contentPane(region='top', height='50%', splitter=True).bagGrid(
            frameCode='mp_pending',
            title='!!Pending messages',
            storepath='main.data.pending',
            struct=self.pending_struct,
            pbl_classes=True,
            addrow=False,
            delrow=False,
            margin='6px',
        )
        right_bc.contentPane(region='center').bagGrid(
            frameCode='mp_deferred',
            title='!!Deferred messages',
            storepath='main.data.deferred',
            struct=self.deferred_struct,
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

    def rules_struct(self, struct):
        rows = struct.view().rows()
        rows.cell('priority', name='!!Priority', width='6em', dtype='I')
        rows.cell('name', name='!!Name', width='12em')
        rows.cell('enabled', name='!!Enabled', width='7em', dtype='B')
        rows.cell('interval_minutes', name='!!Interval (min)', width='10em', dtype='I')
        rows.cell('time_window', name='!!Time window', width='12em')
        rows.cell('days_label', name='!!Days', width='14em')

    def pending_struct(self, struct):
        rows = struct.view().rows()
        rows.cell('id', name='!!Message ID', width='14em')
        rows.cell('to_addr', name='!!Recipient', width='16em')
        rows.cell('subject', name='!!Subject', width='18em')
        rows.cell('started_at', name='!!Queued at', width='14em')

    def deferred_struct(self, struct):
        rows = struct.view().rows()
        rows.cell('id', name='!!Message ID', width='14em')
        rows.cell('account_id', name='!!Account', width='12em')
        rows.cell('deferred_time', name='!!Deferred until', width='16em')
        rows.cell('retry_count', name='!!Retries', width='8em', dtype='I')

    # -------------------------------------------------------------------------
    # RPC helpers
    # -------------------------------------------------------------------------
    @public_method
    def rpc_proxy_overview(self):
        service = self._mailproxy_service()
        errors = []

        accounts = self._safe_service_call(service.list_accounts, 'accounts', 'Accounts', errors)
        pending = self._safe_service_call(service.pending_messages, 'pending', 'Pending messages', errors)
        deferred = self._safe_service_call(service.list_deferred, 'deferred', 'Deferred messages', errors)
        rules = self._safe_service_call(service.list_rules, 'rules', 'Scheduler rules', errors)

        result = Bag()
        result['accounts'] = self._list_to_bag(accounts, 'id')
        result['pending'] = self._list_to_bag(pending, 'id')
        result['deferred'] = self._list_to_bag(self._decorate_deferred(deferred), 'id')
        result['rules'] = self._list_to_bag(self._decorate_rules(rules), 'id')

        status = Bag()
        status['account_count'] = len(accounts)
        status['pending_count'] = len(pending)
        status['deferred_count'] = len(deferred)
        status['active'] = any(rule.get('enabled') for rule in rules)
        status['last_refresh'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        if errors:
            status['error'] = '\n'.join(errors)
        result['status'] = status
        return result

    @public_method
    def rpc_run_now(self):
        return self._command_wrapper('Run now', lambda svc: svc.run_now(), include_overview=True)

    @public_method
    def rpc_suspend(self):
        return self._command_wrapper('Suspend scheduler', lambda svc: svc.suspend(), include_overview=True)

    @public_method
    def rpc_activate(self):
        return self._command_wrapper('Activate scheduler', lambda svc: svc.activate(), include_overview=True)

    @public_method
    def rpc_add_account(self, account_id=None):
        if not account_id:
            return Bag(dict(ok=False, message='No account selected'))
        try:
            response = self._mailproxy_service().add_account(account_id)
        except Exception as exc:
            return Bag(dict(ok=False, message='Add account failed: %s' % exc))

        if isinstance(response, str):
            try:
                response = fromJson(response)
            except Exception as exc:
                return Bag(dict(status='error', message='Add account: invalid JSON response (%s)' % exc))
        if isinstance(response, dict) and not response.get('status') == 'ok':
            return Bag(dict(status='error', message='Add account: %s' % response.get('error', 'Unknown error')))

        overview = self.rpc_proxy_overview()
        return Bag(dict(status='ok', message='Account registered on mail proxy', overview=overview))

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
        if isinstance(response, dict):
            if response.get('ok'):
                return response.get(result_key) or []
            errors.append('%s: %s' % (label, response.get('error', 'Unknown error')))
            return []
        return response or []

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

    def _decorate_deferred(self, rows):
        result = []
        for row in rows or []:
            row = dict(row)
            deferred_until = row.get('deferred_until')
            if deferred_until:
                row['deferred_time'] = datetime.fromtimestamp(int(deferred_until)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                row['deferred_time'] = None
            row['retry_count'] = row.get('retry_count', 0)
            result.append(row)
        return result

    def _decorate_rules(self, rows):
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        result = []
        for row in rows or []:
            row = dict(row)
            days = row.get('days') or []
            row['days_label'] = ', '.join(day_names[d % 7] for d in days) if days else 'All'
            start_hour = row.get('start_hour')
            end_hour = row.get('end_hour')
            if start_hour is None or end_hour is None:
                row['time_window'] = 'Always'
            else:
                row['time_window'] = '%02d:00-%02d:00' % (int(start_hour), int(end_hour))
            result.append(row)
        return result

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
