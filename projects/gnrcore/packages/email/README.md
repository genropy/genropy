# Email Package

The `email` package provides full email capabilities for Genropy applications: IMAP inbox management, outgoing message composition, and — optionally — asynchronous delivery via the **Mail Proxy** service.

---

## Table of Contents

1. [Architecture overview](#architecture-overview)
2. [Data model](#data-model)
3. [Sending emails from code](#sending-emails-from-code)
4. [Mail Proxy integration](#mail-proxy-integration)
   - [How it works](#how-it-works)
   - [Authentication](#authentication)
   - [Message lifecycle](#message-lifecycle)
   - [Attachment delivery](#attachment-delivery)
   - [Fallback mode](#fallback-mode)
5. [Configuration guide](#configuration-guide)
   - [Prerequisites](#prerequisites)
   - [Step 1 — instance config](#step-1--instance-config)
   - [Step 2 — add the service in the application](#step-2--add-the-service-in-the-application)
   - [Step 3 — register the tenant](#step-3--register-the-tenant)
   - [Step 4 — configure email accounts](#step-4--configure-email-accounts)
6. [Operations dashboard](#operations-dashboard)
7. [Troubleshooting](#troubleshooting)

---

## Architecture overview

```
┌─────────────────────────────────────┐
│            Genropy app              │
│                                     │
│  newMessage() ──► email.message     │
│                       │             │
│               trigger_onInserted    │
│                       │             │
│               email.message_to_send │
│                       │             │
│               proxyRunNow()  ───────┼──► POST /commands/run-now
│                                     │
│  ◄── proxy_sync() ◄─────────────────┼──► genro-mail-proxy
│       (webhook)                     │          │
│          │                          │          ▼
│  update email.message               │       SMTP delivery
└─────────────────────────────────────┘
```

When the Mail Proxy service is active:

1. A new outgoing message is inserted in `email.message`.
2. A database trigger enqueues it in `email.message_to_send` and notifies the proxy via `run_now`.
3. The proxy calls back the `proxy_sync` endpoint, which:
   - processes any delivery reports (updating message status),
   - fetches pending messages from the queue, converts them, and submits the batch.
4. The proxy delivers via SMTP and calls back again with the final status.

Without the proxy, messages are dispatched directly via SMTP through the `send_mail` batch action.

---

## Data model

### `email.account`
Represents an email account (IMAP + SMTP). Key fields:

| Column | Type | Description |
|---|---|---|
| `host` / `port` | string/int | IMAP connection |
| `smtp_host` / `smtp_port` | string/int | SMTP connection |
| `smtp_username` / `smtp_password` | string | SMTP credentials |
| `smtp_tls` / `smtp_ssl` | bool | Transport security |
| `save_output_message` | bool | Enables outgoing message tracking and proxy sync |
| `proxy_ttl` | int | Message TTL on the proxy (seconds, default 300) |
| `proxy_limit_per_minute/hour/day` | int | Rate limiting |
| `proxy_limit_behavior` | string | `defer` (default) or `drop` when limit is reached |
| `proxy_batch_size` | int | Max messages per batch sent to the proxy |

Accounts with `save_output_message=true` and a configured `smtp_host` are automatically registered on (and removed from) the proxy when the service is active.

### `email.message`
Stores every email: incoming and outgoing.

| Column | Type | Description |
|---|---|---|
| `account_id` | FK | Sending/receiving account |
| `to_address` / `cc_address` / `bcc_address` | string | Recipients (comma-separated) |
| `subject` / `body` / `body_plain` | string | Content |
| `html` | bool | Whether body is HTML |
| `send_date` | datetime | When the message was delivered |
| `error_msg` / `error_ts` | string/datetime | Error state |
| `proxy_ts` | datetime | When the message was submitted to the proxy queue |
| `proxy_priority` | int | 0=immediate, 1=high, 2=medium, 3=low |
| `batch_code` | string | Groups circular emails for optimised delivery |
| `deferred_ts` | datetime | Schedule delivery at a future time |
| `weak_attachments` | string | Comma-separated storage paths for inline/external attachments |

Formula columns:
- `message_to_send` — `true` if the message is outgoing and not yet sent.
- `sent` — `true` if `send_date` is set.

### `email.message_to_send`
Lightweight outgoing queue. Contains one row per pending message. Populated and cleared automatically by triggers on `email.message`.

---

## Sending emails from code

### Basic usage

```python
pkg = self.db.package('email')
msg = pkg.table('message').newMessage(
    account_id='my-account-pkey',
    to_address='recipient@example.com',
    subject='Hello',
    body='<p>Hello world</p>',
    html=True,
)
```

`newMessage()` inserts the record and the triggers handle the rest — queueing and proxy notification happen automatically.

### With attachments

```python
msg = pkg.table('message').newMessage(
    account_id='my-account-pkey',
    to_address='recipient@example.com',
    subject='Report',
    body='Please find the report attached.',
    attachments=[
        'home:reports/q1.pdf',     # storage path
        '/tmp/export.xlsx',        # absolute local path
    ],
)
```

### With deferred delivery

```python
from datetime import datetime, timedelta

msg = pkg.table('message').newMessage(
    account_id='my-account-pkey',
    to_address='recipient@example.com',
    subject='Scheduled',
    body='This was sent at a scheduled time.',
    deferred_ts=datetime.now() + timedelta(hours=2),
)
```

### With priority

```python
msg = pkg.table('message').newMessage(
    account_id='my-account-pkey',
    to_address='urgent@example.com',
    subject='Urgent notice',
    body='...',
    proxy_priority=0,   # 0=immediate, 1=high, 2=medium, 3=low (default)
)
```

### With batch code (circular emails)

```python
import uuid
batch = str(uuid.uuid4())

for recipient in mailing_list:
    pkg.table('message').newMessage(
        account_id='my-account-pkey',
        to_address=recipient,
        subject='Newsletter',
        body=body_html,
        html=True,
        batch_code=batch,
    )
```

The proxy groups messages with the same `batch_code` for optimised delivery.

### Checking proxy availability from code

```python
pkg = self.db.package('email')
proxy = pkg.getMailProxy()   # returns None if not configured/active

if proxy:
    # async delivery via proxy
    pass
else:
    # direct SMTP fallback
    pass
```

`getMailProxy(raise_if_missing=True)` raises an exception instead of returning `None` when the proxy is not available.

### Retrying failed messages

```python
pkg.table('message').clearErrors(message_id)
```

Resets `error_msg`, `error_ts`, `send_date`, and `proxy_ts`, so the message is re-enqueued automatically.

---

## Mail Proxy integration

### How it works

The proxy is an independent service (`genro-mail-proxy`) that Genropy communicates with via REST API. The two sides interact through:

- **`POST /commands/run-now`** — Genropy notifies the proxy that new messages are waiting (called after every commit that adds to the queue).
- **`proxy_sync` endpoint** (on Genropy) — The proxy calls this to deliver reports and request the next batch of outgoing messages. This endpoint is registered at `/mailproxy/proxy_sync` and is authenticated with the `_MAILPROXY_` tag.
- **`proxy_get_attachments` endpoint** (on Genropy) — The proxy calls this to fetch attachment binary content on demand, avoiding the need to pre-upload files.

### Authentication

Two tokens are in play:

| Token | Origin | Used for |
|---|---|---|
| `admin_token` | `instanceconfig` → `api_keys.private.genro_mail_proxy.token` | Administrative operations: tenant registration, `run_now`, account management |
| `tenant_token` | Returned by proxy at registration, stored in service parameters | Message operations: `add_messages`, `list_messages`, delivery callbacks |

The `proxy_sync` and `proxy_get_attachments` endpoints use Genropy's standard Basic Auth with a dedicated system user tagged `_MAILPROXY_`. This user is created automatically when the service is activated.

### Message lifecycle

```
newMessage() inserted
      │
      ▼
trigger_onInserted → message_to_send queue added
      │
      ▼ (after commit)
proxyRunNow() → POST /commands/run-now
      │
      ▼
proxy calls proxy_sync:
  1. delivery_report processed → message.send_date or error_msg updated
  2. pending messages fetched from message_to_send
  3. converted to proxy format and submitted via add_messages()
  4. accepted: message.proxy_ts set, removed from queue
     rejected: message.error_ts set with reason
      │
      ▼
proxy delivers via SMTP
      │
      ▼
proxy calls proxy_sync again with delivery confirmation
      │
      ▼
message.send_date set → message_to_send row deleted
```

### Attachment delivery

Attachments are NOT uploaded to the proxy upfront. Instead:

1. When converting a message, Genropy includes a `storage_path` reference (`volume:path`) for each attachment.
2. The proxy calls `proxy_get_attachments` to download the binary content just before sending.
3. The proxy caches attachments using the MD5 hash included in the payload to avoid repeated downloads.

This approach avoids storing attachments externally and handles token rotation automatically.

### Fallback mode

When the proxy is not configured or is disabled:

- `send_mail` batch action iterates accounts with `save_output_message=true` and sends messages directly via SMTP.
- This can be triggered manually from the account table or scheduled as a daemon task.
- No changes to `newMessage()` are needed — the code path is transparent.

---

## Configuration guide

### Prerequisites

- A running instance of `genro-mail-proxy` reachable from the Genropy server.
- The admin API token for the proxy instance.
- The external URL of the Genropy instance (needed for the proxy to call back).

### Step 1 — instance config

Add the admin token to `instanceconfig.xml` (or equivalent):

```xml
<api_keys>
  <private>
    <genro_mail_proxy token="YOUR_ADMIN_TOKEN"/>
  </private>
</api_keys>
```

This token is read at runtime and never stored in the database.

### Step 2 — add the service in the application

In the Genropy admin interface, go to **System → Services** and add a new service of type `mailproxy`. Fill in:

| Parameter | Description |
|---|---|
| `proxy_url` | Base URL of the proxy, e.g. `https://mail.example.com` |
| `client_base_url` | External URL of this Genropy instance, e.g. `https://app.example.com` |
| `tenant_id` | Identifier for this instance on the proxy (defaults to the database name) |
| `batch_size` | Number of messages per sync batch (default: 50) |
| `db_max_waiting` | Max messages fetched from DB per sync cycle |
| `disabled` | Check to temporarily suspend proxy use without removing the configuration |

### Step 3 — register the tenant

Open the **Mail Proxy Dashboard** (Email → Proxy dashboard in the menu).

Click **Register** in the service configuration panel. Genropy will:

1. Call `POST /tenants/register` on the proxy with the `client_base_url`.
2. Receive and store the `tenant_token` in the service parameters.
3. Create the internal `_MAILPROXY_` system user for webhook authentication.
4. Sync all existing accounts with `save_output_message=true` to the proxy.

The tenant status indicator in the toolbar will turn green when registration is successful.

To undo, click **Unregister** — this removes the tenant from the proxy and deletes the local system user.

### Step 4 — configure email accounts

In **Email → Accounts**, for each account that should use the proxy:

1. Ensure `smtp_host` and SMTP credentials are set.
2. Enable **Save output message** (`save_output_message`). This is the switch that routes outgoing messages through the proxy.
3. Optionally configure rate limits (`proxy_limit_per_minute`, etc.) and `proxy_batch_size`.

The account is synced to the proxy automatically when saved. No manual action is needed.

---

## Operations dashboard

The dashboard at **Email → Proxy dashboard** shows the live state of the proxy integration:

- **Proxy status** (toolbar indicator): green = reachable, red = unreachable.
- **Accounts grid**: lists accounts registered on the proxy with their rate limit configuration.
- **Messages grid**: shows all messages on the proxy queue with status:
  - `pending` — queued, not yet sent
  - `deferred` — scheduled for future delivery
  - `sent` — delivered successfully
  - `error` — delivery failed (error message shown)

**Available actions:**

| Button | Effect |
|---|---|
| Run now | Triggers an immediate dispatch cycle on the proxy |
| Cleanup sent | Removes delivered messages from the proxy older than a configurable threshold |
| Refresh | Reloads dashboard data |

For messages in error state, use `clearErrors()` from code or from the message detail view to re-enqueue.

---

## Troubleshooting

### Proxy is unreachable

- Verify `proxy_url` is correct and the proxy service is running.
- Check that the Genropy server can reach the proxy network address.
- The `admin_token` in `instanceconfig` must match the proxy's configured API key.

### Tenant not registered / red indicator

- Re-click **Register** from the dashboard.
- If registration fails, check the proxy logs for the error reason.
- Ensure `client_base_url` is reachable from the proxy (the proxy must be able to call back).

### Messages stuck in queue (proxy_ts set, send_date never set)

- The proxy may not be able to reach the `proxy_sync` endpoint.
- Verify the `_MAILPROXY_` system user exists and has the correct tag.
- Check Genropy server logs for authentication errors on `/mailproxy/proxy_sync`.

### Messages rejected (error_ts set immediately)

- The proxy rejected the message (e.g. unknown account, malformed address).
- The error reason is stored in `error_msg` on the message record.
- Fix the underlying issue (e.g. re-sync the account) then call `clearErrors()`.

### Attachments not delivered

- The proxy calls `proxy_get_attachments` — check that the storage paths in `weak_attachments` and in `email.message_atc` are valid and accessible.
- Verify the `_MAILPROXY_` user has read access to the relevant storage volumes.
