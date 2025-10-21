#  -*- coding: utf-8 -*-
from datetime import datetime, timezone
from collections import defaultdict

from gnr.web import logger
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from webob.exc import HTTPServiceUnavailable
MEDIUM_PRIORITY = 2

class GnrCustomWebPage(object):
    py_requires='gnrcomponents/externalcall:BaseRpc'

    @public_method(tags='_SYSTEM_') #tag di autorizzazione dell'utente 
    def proxy_sync(self,_json_body=None,**kwargs):
        delivery_report = _json_body.get('delivery_report')
        print('proxy_sync',delivery_report)
        proxy_service = self.getService('mailproxy')

        retry_after = self.db.adapter.retryAfter(max_time=proxy_service.db_max_waiting)
        if retry_after>0:
            raise HTTPServiceUnavailable(
                explanation="Site unavailable retry later",
                headers=[('Retry-After', retry_after)]
            )
        self._update_from_delivery_report(delivery_report)

        outgoing_messages_groped_by_store = self.db.table('email.message_to_send').query().fetchGrouped('dbstore')
        for storename,message_pkeys in outgoing_messages_groped_by_store.items():
            with self.db.tempEnv(storename=storename or False):
                self._add_messages_to_proxy_queue(proxy_service,[m['message_id'] for m in message_pkeys])
                self.db.commit()
                
    def _update_from_delivery_report(self,delivery_report):
        print('delivery_report',delivery_report)
        if not delivery_report:
            return
        #[{'id': '_main_db:LjCW5H_OOuqAKeGhjRFLGg', 'account_id': 'nRjo7qViNiShAuDMB63s_w', 'priority': 2, 'sent_ts': 1761049629, 'error_ts': None, 'error': None, 'deferred_ts': None}]
        delivery_report_by_storename = defaultdict(dict)
        for item in delivery_report:
            message_report = dict(item)
            storename, message_id = message_report.pop('id').split(':')
            delivery_report_by_storename[storename][message_id] = message_report
        messagetbl = self.db.table('email.message')
        for storename,store_reports in delivery_report_by_storename.items():
            with self.db.tempEnv(storename=storename):
                messages = messagetbl.query(where='$id IN :message_pkeys',message_pkeys = list(store_reports.keys()),for_update=True).fetch()
                for message in messages:
                    old_message = dict(message)
                    report = dict(store_reports.get(message['id']) or {})
                    send_ts = report.pop('sent_ts', None)
                    if send_ts:
                        try:
                            message['send_date'] = datetime.fromtimestamp(int(send_ts), tz=timezone.utc)
                        except (TypeError, ValueError):
                            logger.warning('Invalid sent_ts in delivery report for message %s: %s', message['id'], send_ts)
                    error_ts = report.get('error_ts')
                    if error_ts:
                        try:
                            report['error_ts'] = datetime.fromtimestamp(int(error_ts), tz=timezone.utc)
                        except (TypeError, ValueError):
                            logger.warning('Invalid error_ts in delivery report for message %s: %s', message['id'], error_ts)
                            report.pop('error_ts', None)
                    message['error_msg'] = report.get('error')
                    messagetbl.update(message,old_message)
                self.db.commit()

    def _adaptedMessages(self,messages):
        for message in messages:
            pass

    def _add_messages_to_proxy_queue(self,proxy_service,message_pkeys):
        message_tbl = self.db.table('email.message')
        messages = message_tbl.query(where='$id IN :message_pkeys',
                                    message_pkeys=message_pkeys,for_update=True,bagFields=True,
                                    order_by=f'COALESCE($proxy_priority,{MEDIUM_PRIORITY}),$__ins_ts',
                                    ).fetchAsDict('id')
        payload = []
        proxy_ids = {}
        for message in messages.values():
            payload_chunk = self._convert_to_proxy_message(message)
            if isinstance(payload_chunk,str):
                oldrec = dict(message)
                message['error_ts'] = message_tbl.newUTCDatetime()
                message['error_msg'] = payload_chunk
                message_tbl.update(message, oldrec)
            elif payload_chunk:
                payload.append(payload_chunk)
                proxy_ids[message['id']] = payload_chunk.get('id')
        if not payload:
            return
        response_data = proxy_service.add_messages(payload) or {}
        if isinstance(response_data, list):
            # Backwards compatibility in case the proxy still returns the legacy format
            response_data = {'ok': True, 'legacy': response_data}
        rejected = {
            item.get('id'): item.get('reason')
            for item in response_data.get('rejected') or []
            if item
        }
        timestamp = message_tbl.newUTCDatetime()
        fallback_error = response_data.get('error') or 'Queueing failed'
        for message_id, message_to_update in messages.items():
            proxy_message_id = proxy_ids.get(message_id)
            if not proxy_message_id:
                continue
            oldrec = dict(message_to_update)
            rejection_reason = rejected.get(proxy_message_id)
            if rejection_reason:
                message_to_update['error_ts'] = timestamp
                message_to_update['error_msg'] = rejection_reason
            elif response_data.get('ok'):
                message_to_update['proxy_ts'] = timestamp
                message_to_update['error_ts'] = None
                message_to_update['error_msg'] = None
            else:
                message_to_update['error_ts'] = timestamp
                message_to_update['error_msg'] = fallback_error
            message_tbl.update(message_to_update,oldrec)
        
    def _convert_to_proxy_message(self, record):
        storename = self.db.currentEnv.get('storename') or self.db.rootstore
        result = {
            'id': f"{storename}:{record['id']}",
            'account_id': record['account_id'],
            'subject': record['subject'] or '',
            'from': record['from_address'],
        }
        
        result['to'] = self._address_list(record.get('to_address'))
        cc_addresses = self._address_list(record.get('cc_address'))
        if cc_addresses:
            result['cc'] = cc_addresses

        bcc_addresses = self._address_list(record.get('bcc_address'))
        if bcc_addresses:
            result['bcc'] = bcc_addresses

        result['body'] = self._message_body(record)
        result['content_type'] = 'html' if record.get('html') else 'plain'

        headers = self._extra_headers(record.get('extra_headers'))
        if headers:
            message_id_header = headers.pop('message_id', None) or headers.pop('Message-ID', None)
            if message_id_header:
                result['message_id'] = message_id_header
            reply_to = headers.pop('Reply-To', None) or headers.pop('reply_to', None)
            if reply_to:
                result['reply_to'] = reply_to
            return_path = headers.pop('Return-Path', None) or headers.pop('return_path', None)
            if return_path:
                result['return_path'] = return_path
            if headers:
                result['headers'] = headers

        attachments = self._attachments_for_message(record)
        if attachments:
            result['attachments'] = attachments
        return result

    def _message_body(self, record):
        if record.get('html') and record.get('body'):
            return record['body']
        return record.get('body') or record.get('body_plain') or ''


    def _address_list(self, value):
        if not value:
            return []
        if isinstance(value, (list, tuple)):
            return [addr for addr in value if addr]
        extractor = self.db.table('email.message')
        return extractor.extractAddresses(value)

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
