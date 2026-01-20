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
  - attachments -> storage_path format: "storename@volume:path"
    (e.g., "mydb@home:emails/2024/file.pdf")
    Downloaded via proxy_get_attachments RPC method

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

Attachment Downloads (RPC):
---------------------------
Attachments are downloaded via proxy_get_attachments RPC method instead of HTTP endpoints.
The proxy calls this RPC method with a list of storage paths:
  - storage_path format: "storename@volume:path" (same @ separator as message_id)
  - batch support: single RPC call for multiple attachments
  - multi-tenant: storename prefix enables correct DB context switching
  - authentication: @public_method(tags='_SYSTEM_') (same as proxy_sync)
  - no volume registration needed on proxy
  - no public HTTP endpoint needed

Example RPC call:
  proxy_get_attachments(storage_paths=["mydb@home:emails/file.pdf", "mydb@docs:report.xlsx"])

Returns list of file data:
  [{'storage_path': '...', 'content': bytes, 'mimetype': '...', 'filename': '...', 'size': int}, ...]

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

    @public_method(tags='_MAILPROXY_')
    def proxy_sync(self, **kwargs):
        """
        Endpoint called by async-mail-service to deliver batch delivery reports.

        Authentication is handled by genropy via Basic Auth with the mailproxy user
        (created during tenant registration) which has the _MAILPROXY_ tag.

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

    @public_method(tags='_MAILPROXY_')
    def proxy_get_attachments(self, storage_paths=None, **kwargs):
        """
        Download multiple attachment files via RPC or HTTP POST.

        Called by async-mail-service HttpFetcher to retrieve attachment content.
        Authentication is handled by genropy via Basic Auth with the mailproxy user.

        Supports two call modes:
        1. RPC call: storage_paths parameter directly
        2. HTTP POST from HttpFetcher:
           - Single: body contains storage_path string directly
           - Batch: JSON body {"attachments": ["path1", "path2", ...]}

        Args:
            storage_paths: List of storage paths in format "storename@volume:path"
                          Example: ["mydb@home:emails/file.pdf", "mydb@docs:report.xlsx"]
                          The @ separator splits storename from storage path.

        Returns:
            For RPC/single: list of attachment data dictionaries
            For batch HTTP: {"attachments": [...]} format for HttpFetcher

            Each attachment dict contains:
            {
                'storage_path': 'mydb@home:emails/file.pdf',
                'content': bytes,      # File content (base64 encoded in JSON response)
                'mimetype': str,       # MIME type (e.g., 'application/pdf')
                'filename': str,       # Base filename
                'size': int           # File size in bytes
            }
            or in case of error:
            {
                'storage_path': 'mydb@home:missing.pdf',
                'error': 'File not found: home:missing.pdf'
            }

        Notes:
            - Supports batch downloads (multiple attachments in one call)
            - Supports multi-tenant (different storenames in same batch)
            - Errors are returned per-file (doesn't fail entire batch)
            - File content is base64 encoded automatically by JSON serializer
        """
        is_batch_http = False

        # Handle HTTP POST from HttpFetcher if storage_paths not provided via RPC
        if storage_paths is None:
            json_data = self.get_request_body_json()
            if json_data and 'attachments' in json_data:
                # Batch HTTP request: {"attachments": ["path1", "path2", ...]}
                storage_paths = json_data.get('attachments') or []
                is_batch_http = True
            else:
                # Single HTTP request: body contains the storage_path directly
                body = self.get_request_body()
                if body:
                    if isinstance(body, bytes):
                        body = body.decode('utf-8')
                    storage_paths = [body.strip()]

        if not storage_paths:
            raise Exception("Missing required parameter: storage_paths")

        if not isinstance(storage_paths, list):
            storage_paths = [storage_paths]

        results = []
        logger.info('proxy_get_attachments: processing %d attachment(s)', len(storage_paths))

        for full_path in storage_paths:
            # Parse storename from path (format: "storename@volume:path")
            if '@' in full_path:
                storename, storage_path = full_path.split('@', 1)
            else:
                # Fallback if no storename (shouldn't happen in normal operation)
                storename = None
                storage_path = full_path

            try:
                # Switch to correct store context
                with self.db.tempEnv(storename=storename or False):
                    # Get storage node from path
                    storage_node = self.site.storageNode(storage_path)

                    if not storage_node or not storage_node.exists:
                        logger.warning('Attachment not found: %s (storename=%s)', storage_path, storename)
                        results.append({
                            'storage_path': full_path,
                            'error': f'File not found: {storage_path}'
                        })
                        continue

                    # Read file content
                    with storage_node.open('rb') as f:
                        content = f.read()

                    logger.debug('Attachment retrieved: %s (%d bytes)', full_path, len(content))

                    results.append({
                        'storage_path': full_path,
                        'content': content,
                        'mimetype': storage_node.mimetype or 'application/octet-stream',
                        'filename': storage_node.basename or storage_path.split('/')[-1],
                        'size': len(content)
                    })

            except Exception as e:
                logger.error('Error retrieving attachment %s: %s', full_path, e, exc_info=True)
                results.append({
                    'storage_path': full_path,
                    'error': f'Error reading file: {str(e)}'
                })

        # Log summary
        success_count = sum(1 for r in results if 'error' not in r)
        error_count = len(results) - success_count
        total_size = sum(r.get('size', 0) for r in results if 'error' not in r)

        logger.info('proxy_get_attachments: completed %d/%d successful (total %d bytes)',
                   success_count, len(results), total_size)

        # Return format depends on call mode
        if is_batch_http:
            # HttpFetcher expects {"attachments": [...]} for batch
            return {'attachments': results}

        return results

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
        """Convert storage node to attachment payload for HTTP download.

        Returns: {
            "storage_path": "storename@volume:path",
            "filename": "...",
            "fetch_mode": "endpoint",
            "content_md5": "..."
        }

        The storage_path format uses @ separator (same as message_id format) to include
        the storename, enabling multi-tenant support in proxy_get_attachments.
        fetch_mode="endpoint" tells the proxy to use client_attachment_url for fetching.
        content_md5 enables cache lookup on the proxy side.
        """
        if not node:
            return None

        # Get storename for multitenant routing (same as message_id format)
        storename = self.db.currentEnv.get('storename') or self.db.rootstore

        # Format: storename@volume:path (consistent with message_id format)
        # node.fullpath is already in format "volume:path" (e.g., "home:emails/file.pdf")
        storage_path = f'{storename}@{node.fullpath}'

        payload = {
            'storage_path': storage_path,
            'fetch_mode': 'endpoint',
        }
        if filename:
            payload['filename'] = filename

        # MD5 for cache lookup on proxy side
        md5_hash = node.md5hash
        if md5_hash:
            payload['content_md5'] = md5_hash

        return payload