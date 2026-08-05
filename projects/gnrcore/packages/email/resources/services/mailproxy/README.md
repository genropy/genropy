# Mail Proxy Service

## Overview
The mail proxy bridges Genropy applications with the Async Mail Service. It centralises SMTP account management, queues outbound messages, and delegates delivery to the asynchronous dispatcher. By decoupling message composition from transport, the proxy improves reliability, enables scaling of the delivery backend, and simplifies operational control through a single API surface.

## Capabilities
- **SMTP account management** — create, update, and delete accounts through `POST /account`, `GET /accounts`, and `DELETE /account/{account_id}`.
- **Scheduler control** — activate, suspend, or trigger an immediate dispatch cycle using `POST /commands/activate`, `POST /commands/suspend`, and `POST /commands/run-now`.
- **Message queue operations** — enqueue batches via `POST /commands/add-messages`, remove entries with `POST /commands/delete-messages`, inspect queue state with `GET /messages`, and expose metrics with `GET /metrics`.
- **Scheduling rules** — configure polling priorities and windows through `POST`, `GET`, `DELETE`, and `PATCH` requests on `/commands/rules`.
- **Authentication** — optionally secure every endpoint with the `X-API-Token` header configured at application start.

## When It Helps
- Workloads that generate large volumes of email and require throttling, retries, or deferred delivery.
- Multi-tenant environments where several stores share the same delivery infrastructure.
- Integrations that benefit from isolating message authoring from transport infrastructure to absorb spikes or route through multiple SMTP accounts.

## Workflow
1. Genropy prepares outgoing messages and forwards them to the mail proxy.
2. The proxy normalises payloads and pushes them to the Async Mail Service with `POST /commands/add-messages`.
3. Rejected entries surface in the `rejected` field and are persisted as errors in `email.message` for user feedback.
4. Accepted messages receive a `proxy_ts` timestamp and are delivered according to the scheduler’s active rules.
5. Admin pages under `/webpages/mailproxy` call `GET /messages` and scheduler endpoints to present live queue status and allow rule maintenance.

## Configuration
Set the service parameters (`ServiceParameters` component):
- `proxy_url` — base URL of the Async Mail Service, e.g. `https://mail.example.com`.
- `proxy_token` — optional API token that the proxy attaches as `X-API-Token`.
- `db_max_waiting` / `batch_size` — local limits used by the proxy when coordinating database access and enqueue batches.

Ensure the Async Mail Service is running with reachable storage and that any configured token matches the proxy settings.
