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
  - id: message_id (primary key from email.message)
  - account_id: SMTP account identifier
  - from_address -> from
  - to_address/cc_address/bcc_address -> to/cc/bcc (list)
  - subject, body, html -> subject, body, content_type
  - proxy_priority -> priority (0=immediate, 1=high, 2=medium, 3=low)
  - deferred_ts -> deferred_ts (Unix timestamp)
  - extra_headers -> message_id, reply_to, return_path, headers
  - attachments -> storage_path format: "volume:path"
    (e.g., "home:emails/2024/file.pdf")
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
Attachments are downloaded via proxy_get_attachments RPC method.
The proxy calls this RPC method with a list of storage paths:
  - storage_path format: "volume:path" (e.g., "home:emails/file.pdf")
  - batch support: single RPC call for multiple attachments
  - authentication: @public_method(tags='_MAILPROXY_')

Example RPC call:
  proxy_get_attachments(storage_paths=["home:emails/file.pdf", "docs:report.xlsx"])

Returns list of file data:
  [{'storage_path': '...', 'content': bytes, 'mimetype': '...', 'filename': '...', 'size': int}, ...]

For protocol details see:
https://github.com/genropy/gnr-async-mail-service/blob/main/docs/protocol.rst
"""
import json
from datetime import datetime, timezone

from gnr.web import logger
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
#from webob.exc import HTTPServiceUnavailable

MEDIUM_PRIORITY = 2

class GnrCustomWebPage(object):
    py_requires='gnrcomponents/externalcall:BaseRpc'
    convert_result = False  # Return pure JSON without ::JS suffix

    def _json_response(self, data):
        """Return JSON string for pure JSON API responses."""
        self.response.content_type = 'application/json'
        return json.dumps(data)

    def _request_json(self):
        """Parse request body as JSON using Werkzeug."""
        return self.request.get_json(silent=True) or {}

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
        4. Returns ok or categorized response with problematic IDs

        Request format:
            {
                "delivery_report": [
                    {"id": "msg1", "sent_ts": 1234567890},
                    {"id": "msg2", "error_ts": 1234567890, "error": "550 User not found"}
                ]
            }

        Returns:
            {"ok": true} if all reports processed successfully
            {"error": [...], "not_found": [...]} if there are problems (only non-empty lists)

        Note:
            All IDs will be marked as reported by the proxy regardless of response content.
            The response is for logging/debugging purposes.
        """
        json_data = self._request_json()
        delivery_report = json_data.get('delivery_report') or []
        proxy_service = self.getService('mailproxy')

        # Process delivery reports
        report_result = self._update_from_delivery_report(delivery_report)

        # Log delivery report processing if any reports were received
        if delivery_report:
            if report_result.get('ok'):
                logger.info('proxy_sync: processed %d delivery reports - all OK', len(delivery_report))
            else:
                logger.info('proxy_sync: processed %d delivery reports (error=%d, not_found=%d)',
                           len(delivery_report),
                           len(report_result.get('error', [])),
                           len(report_result.get('not_found', [])))

        # Fetch and submit pending outgoing messages to proxy (with batch limit)
        batch_size = proxy_service.batch_size or 1000
        outgoing_messages = self.db.table('email.message_to_send').query(
            limit=batch_size,
            order_by=f'COALESCE($proxy_priority,{MEDIUM_PRIORITY}),$__ins_ts',
        ).fetch()

        if outgoing_messages:
            logger.info('proxy_sync: fetched %d pending messages to submit (limit=%d)',
                       len(outgoing_messages), batch_size)
            message_pkeys = [m['message_id'] for m in outgoing_messages]
            self._add_messages_to_proxy_queue(proxy_service, message_pkeys)
            self.db.commit()

        return self._json_response(report_result)
        
                
    def _update_from_delivery_report(self, delivery_report):
        """
        Process delivery reports from async-mail-service and update local message records.

        Expected format:
        [{'id': 'message_id', 'sent_ts': 1761049629, 'error_ts': None, 'error': None}]

        Args:
            delivery_report: List of delivery report items from async-mail-service

        Returns:
            {"ok": True} if all reports processed successfully
            {"error": [...], "not_found": [...]} if there are problems (only non-empty lists)
        """
        if not delivery_report:
            return {'ok': True}

        # Build lookup dict by message_id
        reports_by_id = {item['id']: item for item in delivery_report}

        # Track problematic IDs only
        error_ids = []
        not_found_ids = []

        messagetbl = self.db.table('email.message')
        messages = messagetbl.query(
            where='$id IN :message_pkeys',
            message_pkeys=list(reports_by_id.keys()),
            for_update=True
        ).fetch()

        # Find IDs not in DB
        found_ids = {m['id'] for m in messages}
        for msg_id in reports_by_id:
            if msg_id not in found_ids:
                not_found_ids.append(msg_id)

        # Process found messages
        for message in messages:
            old_message = dict(message)
            report = reports_by_id.get(message['id']) or {}

            sent_ts = report.get('sent_ts')
            error_ts = report.get('error_ts')

            if sent_ts:
                try:
                    message['send_date'] = datetime.fromtimestamp(int(sent_ts), tz=timezone.utc)
                    message['deferred_ts'] = None
                    message['error_ts'] = None
                    message['error_msg'] = None
                except (TypeError, ValueError):
                    pass

            elif error_ts:
                try:
                    message['error_ts'] = datetime.fromtimestamp(int(error_ts), tz=timezone.utc)
                    message['error_msg'] = report.get('error')
                    error_ids.append(message['id'])
                except (TypeError, ValueError):
                    pass

            messagetbl.update(message, old_message)

        self.db.commit()

        # Return ok:true if no problems, otherwise only non-empty problem lists
        if not error_ids and not not_found_ids:
            return {'ok': True}

        result = {}
        if error_ids:
            result['error'] = error_ids
        if not_found_ids:
            result['not_found'] = not_found_ids
        return result

    @public_method(tags='_MAILPROXY_')
    def proxy_get_attachments(self, **kwargs):
        """
        Download attachment file via HTTP POST.

        Called by async-mail-service HttpFetcher to retrieve attachment content.
        Authentication is handled by genropy via Basic Auth with the mailproxy user.

        Request format (JSON body):
            {"storage_path": "volume:path"}
            Example: {"storage_path": "home:emails/file.pdf"}

        Returns:
            Binary file content directly.

        Raises:
            Exception: If file not found or error reading file.
        """
        json_data = self._request_json()
        storage_path = json_data.get('storage_path')

        if not storage_path:
            raise Exception("Missing required parameter: storage_path")

        logger.info('proxy_get_attachments: fetching %s', storage_path)
        storage_node = self.site.storageNode(storage_path)

        if not storage_node or not storage_node.exists:
            logger.warning('Attachment not found: %s', storage_path)
            raise Exception(f'File not found: {storage_path}')

        # Read and return binary content directly
        with storage_node.open('rb') as f:
            content = f.read()

        logger.debug('Attachment retrieved: %s (%d bytes)', storage_path, len(content))

        # Return binary content - the proxy reads it with response.read()
        self.response.content_type = 'application/octet-stream'
        return content

    def _add_messages_to_proxy_queue(self, proxy_service, message_pkeys):
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
        general_error = response_data.get('error')
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
            elif general_error:
                # General failure affecting all messages
                message_to_update['error_ts'] = timestamp
                message_to_update['error_msg'] = general_error
            else:
                # Message successfully queued in proxy
                message_to_update['proxy_ts'] = timestamp
                message_to_update['error_ts'] = None
                message_to_update['error_msg'] = None
            message_tbl.update(message_to_update,oldrec)
        
    def _convert_to_proxy_message(self, record):
        """
        Convert a Genropy email.message record to async-mail-service message format.

        Args:
            record: Message record from email.message table

        Returns:
            dict: Message payload compatible with async-mail-service API
        """
        result = {
            'id': record['id'],
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
        try:
            attachments = self._attachments_for_message(record)
            if attachments:
                result['attachments'] = attachments
        except FileNotFoundError as e:
            return str(e)  # Return error string to mark message as failed

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
        """Collect attachments for a message. Raises FileNotFoundError if any attachment is missing."""
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
            attachments.append(entry)

        weak_attachments = record.get('weak_attachments') or ''
        for path in [p.strip() for p in weak_attachments.split(',') if p.strip()]:
            entry = self._attachment_entry_from_path(path)
            attachments.append(entry)

        return attachments

    def _attachment_entry_from_row(self, row):
        if hasattr(row, 'asDict'):
            row = row.asDict(ascii=True)
        filepath = row.get('filepath')

        node = self.site.storageNode(filepath)
        if not node:
            raise FileNotFoundError(f'Attachment not found: {filepath}')
        # Always use node.basename as filename (includes extension)
        return self._attachment_payload_from_node(node, filename=node.basename)

    def _attachment_entry_from_path(self, path):
        node = self._storage_node(path)
        if not node:
            raise FileNotFoundError(f'Attachment not found: {path}')
        return self._attachment_payload_from_node(node, filename=node.basename or path.split('/')[-1])

    def _attachment_payload_from_node(self, node, filename=None):
        """Convert storage node to attachment payload for HTTP download.

        Returns: {
            "storage_path": "volume:path",
            "filename": "...",
            "fetch_mode": "endpoint",
            "content_md5": "..."
        }

        fetch_mode="endpoint" tells the proxy to use client_attachment_url for fetching.
        content_md5 enables cache lookup on the proxy side.
        """
        if not node:
            return None

        payload = {
            'storage_path': node.fullpath,
            'fetch_mode': 'endpoint',
        }
        if filename:
            payload['filename'] = filename

        # MD5 for cache lookup on proxy side
        md5_hash = node.md5hash
        if md5_hash:
            payload['content_md5'] = md5_hash

        return payload