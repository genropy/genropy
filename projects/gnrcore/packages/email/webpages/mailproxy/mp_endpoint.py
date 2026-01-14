#  -*- coding: utf-8 -*-
"""
Genropy Mail Proxy Endpoint
============================

This endpoint integrates Genropy with async-mail-service (gnr-async-mail-service).

Integration Flow:
-----------------
1. Genropy stores outbound emails in email.message table
2. This endpoint converts messages to async-mail-service format and submits them
3. async-mail-service queues and delivers messages via SMTP
4. async-mail-service calls back to proxy_sync with delivery reports
5. This endpoint updates local email.message records with delivery status

Key Fields Mapping:
-------------------
Genropy -> async-mail-service:
  - id: "storename@message_id" (unique across all stores, @ separator avoids conflicts with storage paths)
  - account_id: SMTP account identifier
  - from_address -> from
  - to_address/cc_address/bcc_address -> to/cc/bcc (list)
  - subject, body, html -> subject, body, content_type
  - proxy_priority -> priority (0=immediate, 1=high, 2=medium, 3=low)
  - deferred_ts -> deferred_ts (Unix timestamp)
  - extra_headers -> message_id, reply_to, return_path, headers
  - attachments -> storage_path format: "storename@volume:path/to/file"
    (e.g., "mydb@home:emails/2024/file.pdf")

async-mail-service -> Genropy (delivery reports):
  - sent_ts -> send_date (UTC datetime)
  - error_ts -> error_ts (UTC datetime)
  - error -> error_msg
  - deferred_ts -> deferred_ts (UTC datetime, for rate-limited messages)

Database Fields Used:
---------------------
email.message:
  - proxy_ts: When message was successfully queued in proxy
  - send_date: When message was delivered by SMTP
  - error_ts: When delivery failed
  - error_msg: Error description
  - deferred_ts: When message is scheduled for later delivery
  - proxy_priority: Delivery priority (0-3)

Storage Volumes (Multitenant):
------------------------------
Both client and proxy have the same volumes registered. In multitenant environments,
volume names are prefixed with storename when registering on the proxy:
  - volume_name on proxy: "storename@volume" (e.g., "mydb@home", "mydb@docs")
  - storage_path format: "storename@volume:path" (e.g., "mydb@home:emails/file.pdf")

The client uses node.fullpath (format "volume:path") and adds the storename@ prefix
for multitenant scenarios. This allows different stores to use the same logical volume
names while pointing to different storage locations on the proxy.

For protocol details see:
https://github.com/genropy/gnr-async-mail-service/blob/main/docs/protocol.rst
"""
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
    def proxy_sync(self, **kwargs):
        """
        Endpoint called by async-mail-service to deliver batch delivery reports.

        This method:
        1. Receives delivery_report array with sent/error status
        2. Updates local email.message records with delivery status
        3. Fetches pending messages and submits them to the proxy service
        4. Returns a summary of processed delivery reports

        Returns:
            dict: Summary of processed reports (sent, error, deferred counts)
        """
        json_data = self.get_request_body_json() or {}
        delivery_report = json_data.get('delivery_report') or []
        proxy_service = self.getService('mailproxy')

        # Check database availability before processing
        retry_after = self.db.adapter.retryAfter(max_time=proxy_service.db_max_waiting)
        if retry_after>0:
            raise HTTPServiceUnavailable(
                explanation="Site unavailable retry later",
                headers=[('Retry-After', retry_after)]
            )
        # Process delivery reports from async-mail-service
        report_summary = self._update_from_delivery_report(delivery_report)

        # Log delivery report processing if any reports were received
        if delivery_report:
            logger.info('proxy_sync: processed %d delivery reports (sent=%d, error=%d, deferred=%d)',
                       len(delivery_report),
                       report_summary.get('sent', 0),
                       report_summary.get('error', 0),
                       report_summary.get('deferred', 0))

        # Fetch and submit pending outgoing messages to proxy (with batch limit)
        batch_size = proxy_service.batch_size or 1000  # Default to 1000 if not configured
        outgoing_messages_groped_by_store = self.db.table('email.message_to_send').query(
            limit=batch_size,
            order_by=f'COALESCE($proxy_priority,{MEDIUM_PRIORITY}),$__ins_ts',
        ).fetchGrouped('dbstore')

        total_queued = sum(len(messages) for messages in outgoing_messages_groped_by_store.values())
        if total_queued > 0:
            logger.info('proxy_sync: fetched %d pending messages to submit (limit=%d)', total_queued, batch_size)

        for storename,message_pkeys in outgoing_messages_groped_by_store.items():
            with self.db.tempEnv(storename=storename or False):
                self._add_messages_to_proxy_queue(proxy_service,[m['message_id'] for m in message_pkeys])
                self.db.commit()

        # Return summary for async-mail-service to mark reports as acknowledged
        return report_summary
        
                
    def _update_from_delivery_report(self,delivery_report):
        """
        Process delivery reports from async-mail-service and update local message records.

        Expected format:
        [{'id': 'storename:message_id', 'account_id': '...', 'priority': 2,
          'sent_ts': 1761049629, 'error_ts': None, 'error': None, 'deferred_ts': None}]

        Args:
            delivery_report: List of delivery report items from async-mail-service

        Returns:
            dict: Summary with counts of sent/error/deferred messages
        """
        if not delivery_report:
            return {'sent': 0, 'error': 0, 'deferred': 0}

        # Group reports by storename for batch processing
        delivery_report_by_storename = defaultdict(dict)
        for item in delivery_report:
            message_report = dict(item)
            storename, message_id = message_report.pop('id').split('@', 1)
            delivery_report_by_storename[storename][message_id] = message_report

        # Track summary statistics
        sent_count = 0
        error_count = 0
        deferred_count = 0

        messagetbl = self.db.table('email.message')
        for storename,store_reports in delivery_report_by_storename.items():
            with self.db.tempEnv(storename=storename):
                messages = messagetbl.query(where='$id IN :message_pkeys',
                                          message_pkeys = list(store_reports.keys()),
                                          for_update=True).fetch()
                for message in messages:
                    old_message = dict(message)
                    report = dict(store_reports.get(message['id']) or {})

                    # Process sent_ts timestamp
                    send_ts = report.pop('sent_ts', None)
                    if send_ts:
                        try:
                            message['send_date'] = datetime.fromtimestamp(int(send_ts), tz=timezone.utc)
                            message['deferred_ts'] = None
                            message['error_ts'] = None
                            message['error_msg'] = None
                            sent_count += 1
                        except (TypeError, ValueError):
                            logger.warning('Invalid sent_ts in delivery report for message %s: %s', message['id'], send_ts)

                    # Process error_ts timestamp
                    error_ts = report.get('error_ts')
                    if error_ts:
                        try:
                            message['error_ts'] = datetime.fromtimestamp(int(error_ts), tz=timezone.utc)
                            error_count += 1
                        except (TypeError, ValueError):
                            logger.warning('Invalid error_ts in delivery report for message %s: %s', message['id'], error_ts)
                            report.pop('error_ts', None)

                    # Process deferred_ts timestamp (if message was deferred by rate limiter)
                    deferred_ts = report.get('deferred_ts')
                    if deferred_ts and not send_ts and not error_ts:
                        try:
                            message['deferred_ts'] = datetime.fromtimestamp(int(deferred_ts), tz=timezone.utc)
                            deferred_count += 1
                        except (TypeError, ValueError):
                            logger.warning('Invalid deferred_ts in delivery report for message %s: %s', message['id'], deferred_ts)

                    # Update error message if present
                    message['error_msg'] = report.get('error')

                    messagetbl.update(message,old_message)
                self.db.commit()

        return {'sent': sent_count, 'error': error_count, 'deferred': deferred_count}

    def _adaptedMessages(self,messages):
        for message in messages:
            pass

    def _add_messages_to_proxy_queue(self,proxy_service,message_pkeys):
        """
        Fetch pending messages and submit them to async-mail-service.

        This method:
        1. Queries messages ordered by priority and insertion time
        2. Converts each message to async-mail-service format
        3. Submits batch to proxy service
        4. Updates local records based on response (queued/rejected/error)

        Args:
            proxy_service: The mailproxy service instance
            message_pkeys: List of message IDs to process
        """
        message_tbl = self.db.table('email.message')
        messages = message_tbl.query(where='$id IN :message_pkeys',
                                    message_pkeys=message_pkeys,for_update=True,bagFields=True,
                                    order_by=f'COALESCE($proxy_priority,{MEDIUM_PRIORITY}),$__ins_ts',
                                    ).fetchAsDict('id')
        payload = []
        proxy_ids = {}

        # Convert messages to proxy format
        for message in messages.values():
            payload_chunk = self._convert_to_proxy_message(message)
            # If conversion returns a string, it's an error message
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

        # Submit batch to async-mail-service
        response_data = proxy_service.add_messages(payload) or {}
        if isinstance(response_data, list):
            # Backwards compatibility in case the proxy still returns the legacy format
            response_data = {'ok': True, 'legacy': response_data}

        # Extract rejected message IDs and reasons
        rejected = {
            item.get('id'): item.get('reason')
            for item in response_data.get('rejected') or []
            if item
        }

        # Update local message records based on response
        timestamp = message_tbl.newUTCDatetime()
        fallback_error = response_data.get('error') or 'Queueing failed'
        for message_id, message_to_update in messages.items():
            proxy_message_id = proxy_ids.get(message_id)
            if not proxy_message_id:
                continue
            oldrec = dict(message_to_update)
            rejection_reason = rejected.get(proxy_message_id)
            if rejection_reason:
                # Message was rejected by proxy service
                message_to_update['error_ts'] = timestamp
                message_to_update['error_msg'] = rejection_reason
            elif response_data.get('ok'):
                # Message successfully queued in proxy
                message_to_update['proxy_ts'] = timestamp
                message_to_update['error_ts'] = None
                message_to_update['error_msg'] = None
            else:
                # General failure
                message_to_update['error_ts'] = timestamp
                message_to_update['error_msg'] = fallback_error
            message_tbl.update(message_to_update,oldrec)
        
    def _convert_to_proxy_message(self, record):
        """
        Convert a Genropy email.message record to async-mail-service message format.

        Args:
            record: Message record from email.message table

        Returns:
            dict: Message payload compatible with async-mail-service API
        """
        storename = self.db.currentEnv.get('storename') or self.db.rootstore
        result = {
            'id': f"{storename}@{record['id']}",
            'account_id': record['account_id'],
            'subject': record['subject'] or '',
            'from': record['from_address'],
        }

        # Priority: 0=immediate, 1=high, 2=medium (default), 3=low
        result['priority'] = record.get('proxy_priority', MEDIUM_PRIORITY)

        # Recipient addresses
        result['to'] = self._address_list(record.get('to_address'))
        cc_addresses = self._address_list(record.get('cc_address'))
        if cc_addresses:
            result['cc'] = cc_addresses

        bcc_addresses = self._address_list(record.get('bcc_address'))
        if bcc_addresses:
            result['bcc'] = bcc_addresses

        # Message body and content type
        result['body'] = self._message_body(record)
        result['content_type'] = 'html' if record.get('html') else 'plain'

        # Optional: Deferred delivery timestamp (Unix epoch)
        deferred_ts = record.get('deferred_ts')
        if deferred_ts:
            try:
                result['deferred_ts'] = int(deferred_ts.timestamp())
            except (AttributeError, TypeError):
                pass

        # Extract special headers (Message-ID, Reply-To, Return-Path)
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
            # Additional custom headers
            if headers:
                result['headers'] = headers

        # Attachments (inline/base64, URLs, or S3 references)
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
            where='$maintable_id=:mid AND $filepath IS NOT NULL',
            mid=message_id,
            columns='$filepath',
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

        node = self.site.storageNode(filepath)
        if not node:
            return None
        # Always use node.basename as filename (includes extension)
        return self._attachment_payload_from_node(node, filename=node.basename)

    def _attachment_entry_from_path(self, path):
        node = self._storage_node(path)
        if not node:
            return None
        return self._attachment_payload_from_node(node, filename=node.basename or path.split('/')[-1])

    def _attachment_payload_from_node(self, node, filename=None):
        """Convert storage node to attachment payload.

        Uses genro-storage format with storage_path: 'storename@volume:path'
        The proxy server has the same volumes registered, so we just need to
        adapt the path with the storename prefix for multitenant support.
        """
        if not node:
            return None

        storage_path = self._adapt_path_to_proxy_volume(node)
        payload = dict(storage_path=storage_path)
        if filename:
            payload['filename'] = filename
        return payload

    def _adapt_path_to_proxy_volume(self, node):
        """Adapt node path to match proxy volume naming.

        Since volumes are registered on the proxy with storename@ prefix in multitenant
        environments, we need to adapt the node's fullpath by adding the same prefix.
        This ensures the proxy can locate the file using its registered volumes.

        Args:
            node: Storage node with fullpath in format 'volume:path'

        Returns:
            str: Adapted path in format 'storename@volume:path' (multitenant)
                 or 'volume:path' (single tenant)
        """
        # node.fullpath is already in format 'volume:path'
        # e.g., 'home:alfa/beta/gamma' or 'docs:alfa/beta/gamma'
        fullpath = node.fullpath

        # Get current storename for multitenant support
        storename = self.db.currentEnv.get('storename') or self.db.rootstore

        # Add storename prefix to match how volumes are registered on the proxy
        # Format: storename@volume:path (e.g., "mydb@home:alfa/beta/gamma")
        if storename:
            return f"{storename}@{fullpath}"

        return fullpath