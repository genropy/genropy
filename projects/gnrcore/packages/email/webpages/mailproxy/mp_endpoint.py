#  -*- coding: utf-8 -*-
from gnr.web import logger
from collections import defaultdict

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from webob.exc import HTTPServiceUnavailable

class GnrCustomWebPage(object):
    py_requires='gnrcomponents/externalcall:BaseRpc'
    PRIORITY_LABELS = ['immediate', 'high', 'medium', 'low']
    PRIORITY_LOOKUP = {label: idx for idx, label in enumerate(PRIORITY_LABELS)}

    @public_method(tags='_async_scheduler_') #tag di autorizzazione dell'utente 
    def proxy_sync(self,delivery_report=None):
        proxy_service = self.getService('mailproxy')

        retry_after = self.db.adapter.retryAfter(max_time=proxy_service.db_max_waiting)
        if retry_after>0:
            raise HTTPServiceUnavailable(
                explanation="Site unavailable retry later",
                headers=[('Retry-After', retry_after)]
            )
        self._update_from_delivery_report(delivery_report)
        messages_to_dispatch = self._get_messages_to_dispatch(batch_size=proxy_service.batch_size)
        records_by_id = {}
        message_payloads = []
        has_immediate = False
        for record,payload in messages_to_dispatch:
            if not record:
                continue
            records_by_id[record['id']] = record
            message_payloads.append(payload)
            if payload.get('priority') == 'immediate':
                has_immediate = True
        if not message_payloads:
            return []
        proxy_response = proxy_service.add_messages(message_payloads) or {}
        response_ok = True
        if isinstance(proxy_response, dict):
            response_ok = proxy_response.get('ok', True)
            response_items = proxy_response.get('messages') or []
        else:
            response_items = proxy_response
        if not response_items:
            response_items = []
        response_by_store = defaultdict(list)
        for response_row in response_items:
            outgoing_message_id = response_row.get('id')
            if not outgoing_message_id:
                logger.warning('wrong response from add_messages:missing id')
                continue
            if ':' in outgoing_message_id:
                storename, outgoing_message_id = outgoing_message_id.split(':',1)
            else:
                storename = self.db.rootstore
                logger.warning('missing storename in add_messages response id')
            item = dict(response_row)
            item['id'] = outgoing_message_id
            response_by_store[storename].append(item)

        for storename,outgoing_messages in response_by_store.items():
            with self.db.tempEnv(storename=storename):
                self._update_messages_from_response(outgoing_messages,records_by_id)
        self.db.commit()
        if has_immediate and response_ok:
            try:
                proxy_service.run_now()
            except Exception:
                logger.exception('mailproxy run_now failed')

    def _update_messages_from_response(self,result,records):
        """Apply the proxy response values to the corresponding email messages."""
        message_tbl = self.db.table('email.message')
        for r in result:
            record_to_upd = records.get(r['id'])
            if not record_to_upd:
                logger.warning('wrong response from add_messages:id mismatch')
                continue
            old_rec = dict(record_to_upd)
            record_to_upd.update(r)
            message_tbl.update(record_to_upd,old_rec)

    def _update_from_delivery_report(self,delivery_report):
        if not delivery_report:
            return
        delivery_map = {}
        for entry in delivery_report:
            composite_id = entry.get('id')
            storename, plain_id = self._split_message_id(composite_id)
            if not plain_id:
                continue
            entry_copy = dict(entry)
            entry_copy['id'] = plain_id
            delivery_map[plain_id] = entry_copy
            status = (entry_copy.get('status') or '').lower()
            if status == 'sent':
                target_store = storename or self.db.rootstore
                with self.db.tempEnv(storename=target_store):
                    self.db.table('email.message_to_send').removeMessageFromQueue(plain_id)
        if not delivery_map:
            return
        def updater(row):
            row.update(delivery_map.get(row['id'],{}))
        self.db.table('email.message').batchUpdate(
            updater,
            _pkeys=list(delivery_map.keys())
        )

    def _get_messages_to_dispatch(self,batch_size=None):
        queue_tbl = self.db.table('email.message_to_send')
        return queue_tbl.applyOnMessages(self._convert_message_for_proxy_json,limit=batch_size)

    def _convert_message_for_proxy_json(self, message_id):
        message_tbl = self.db.table('email.message')
        record = message_tbl.record(pkey=message_id,for_update=True, bagFields=True, ignoreMissing=True).output('dict')
        if not record:
            return (None,None)
        old_record = dict(record)
        storename = self.db.currentEnv.get('storename') or self.db.rootstore
        payload = dict(
            id=f"{storename}:{record['id']}",
            account_id=record.get('account_id'),
            subject=record.get('subject') or '',
        )
        priority_label, _ = self._message_priority(record)
        if priority_label:
            payload['priority'] = priority_label
        account_id = record.get('account_id')
        if not account_id:
            record['error_msg'] = 'missing_account'
            record['error_ts'] = message_tbl.newUTCDatetime()
            message_tbl.update(record,old_record)
            return (None,None)
        


        from_address = record.get('from_address') or self._default_from_address(record.get('account_id'))
        if not from_address:
            record['error_msg'] = 'missing_from_address'
            record['error_ts'] = message_tbl.newUTCDatetime()
            message_tbl.update(record,old_record)
            return (None,None)
        payload['from'] = from_address

        to_addresses = self._address_list(record.get('to_address'))
        if not to_addresses:
            record['error_msg'] = 'missing_to_address'
            record['error_ts'] = message_tbl.newUTCDatetime()
            message_tbl.update(record,old_record)
            return (None,None)
        payload['to'] = to_addresses

        cc_addresses = self._address_list(record.get('cc_address'))
        if cc_addresses:
            payload['cc'] = cc_addresses

        bcc_addresses = self._address_list(record.get('bcc_address'))
        if bcc_addresses:
            payload['bcc'] = bcc_addresses

        payload['body'] = self._message_body(record)
        payload['content_type'] = 'html' if record.get('html') else 'plain'

        headers = self._extra_headers(record.get('extra_headers'))
        if headers:
            message_id_header = headers.pop('message_id', None) or headers.pop('Message-ID', None)
            if message_id_header:
                payload['message_id'] = message_id_header
            reply_to = headers.pop('Reply-To', None) or headers.pop('reply_to', None)
            if reply_to:
                payload['reply_to'] = reply_to
            return_path = headers.pop('Return-Path', None) or headers.pop('return_path', None)
            if return_path:
                payload['return_path'] = return_path
            if headers:
                payload['headers'] = headers

        attachments = self._attachments_for_message(record)
        if attachments:
            payload['attachments'] = attachments

        return (record,payload)

    def _message_body(self, record):
        if record.get('html') and record.get('body'):
            return record['body']
        return record.get('body') or record.get('body_plain') or ''

    def _message_priority(self, record):
        value = record.get('priority')
        if value is None:
            value = record.get('priority_level') or record.get('priority_code') or record.get('priority_label')
        if isinstance(value, str):
            lower = value.lower()
            if lower in self.PRIORITY_LOOKUP:
                idx = self.PRIORITY_LOOKUP[lower]
                return self.PRIORITY_LABELS[idx], idx
            try:
                value = int(value)
            except ValueError:
                return self.PRIORITY_LABELS[2], 2
        try:
            idx = int(value)
        except (TypeError, ValueError):
            idx = 2
        idx = max(0, min(idx, len(self.PRIORITY_LABELS) - 1))
        return self.PRIORITY_LABELS[idx], idx

    def _address_list(self, value):
        if not value:
            return []
        if isinstance(value, (list, tuple)):
            return [addr for addr in value if addr]
        extractor = self.db.table('email.message')
        return extractor.extractAddresses(value)

    def _default_from_address(self, account_id):
        if not account_id:
            return None
        account_tbl = self.db.table('email.account')
        account_pref = account_tbl.getSmtpAccountPref(account_id)
        return account_pref.get('from_address')

    def _extra_headers(self, extra_headers):
        if not extra_headers:
            return {}
        if isinstance(extra_headers, Bag):
            headers = extra_headers.asDict(ascii=True)
        elif isinstance(extra_headers, dict):
            headers = dict(extra_headers)
        else:
            headers = {}
        normalized = {}
        for key, value in headers.items():
            if value in (None, '', False):
                continue
            if isinstance(value, str):
                normalized[str(key)] = value
            elif isinstance(value, (int, float)):
                normalized[str(key)] = value
            elif isinstance(value, bool):
                normalized[str(key)] = 'true' if value else 'false'
            else:
                normalized[str(key)] = str(value)
        return normalized

    def _attachments_for_message(self, record):
        attachments = []
        message_id = record['id']
        atc_tbl = self.db.table('email.message_atc')
        attachment_rows = atc_tbl.query(
            where='$maintable_id=:mid',
            mid=message_id,
            columns='$description,$filepath,$external_url,$full_external_url,$filepath_original_name',
            addPkeyColumn=False
        ).fetch()
        for row in attachment_rows:
            entry = self._attachment_entry_from_row(row)
            if entry:
                attachments.append(entry)

        weak_attachments = record.get('weak_attachments') or ''
        for path in [p.strip() for p in weak_attachments.split(',') if p.strip()]:
            entry = self._attachment_entry_from_path(path)
            if entry:
                attachments.append(entry)

        return attachments

    def _attachment_entry_from_row(self, row):
        if hasattr(row, 'asDict'):
            row = row.asDict(ascii=True)
        filepath = row.get('filepath')
        filename = row.get('filepath_original_name') or row.get('description')

        # External URLs take precedence over storage resolution
        url = row.get('full_external_url') or row.get('external_url')
        if url:
            entry = dict(url=url)
            if filename:
                entry['filename'] = filename
            return entry

        node = self._storage_node(filepath)
        if not node:
            return None
        filename = filename or node.basename
        return self._attachment_payload_from_node(node, filename=filename)

    def _attachment_entry_from_path(self, path):
        node = self._storage_node(path)
        if not node:
            return None
        return self._attachment_payload_from_node(node, filename=node.basename or path.split('/')[-1])

    def _attachment_payload_from_node(self, node, filename=None):
        if not node:
            return None

        if self._node_is_s3(node):
            bucket = getattr(node.service, 'bucket', None)
            key = node.internal_path()
            if not bucket or not key:
                return None
            payload = dict(s3=dict(bucket=bucket, key=key))
        else:
            try:
                url = node.url()
            except Exception:
                url = None
            if not url:
                return None
            payload = dict(url=url)

        if filename:
            payload['filename'] = filename
        return payload

    def _node_is_s3(self, node):
        service = getattr(node, 'service', None)
        if not service:
            return False
        location = getattr(service, 'location_identifier', None)
        if not location:
            return False
        return str(location).startswith('s3/')

    def _storage_node(self, path):
        if not path:
            return None
        site = self.db.application.site
        try:
            storage_path = path if ':' in path else f'home:{path}'
            node = site.storageNode(storage_path)
        except Exception:
            return None
        if not node or not node.exists:
            return None
        return node

    def _split_message_id(self, composite_id):
        if not composite_id:
            return None, None
        if ':' in composite_id:
            storename, message_id = composite_id.split(':', 1)
            return storename or self.db.rootstore, message_id
        return self.db.rootstore, composite_id
