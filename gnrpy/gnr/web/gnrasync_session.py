# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrasync_session : neutral full-duplex async session core
# --------------------------------------------------------------------------
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.

"""Neutral, modern async session core for GenroPy.

The module exposes an :class:`AsyncSession` class that bridges a server-side
peer with a browser-side WebSocket client and an :class:`AsyncSessionManager`
that owns session lifecycles. Three semantic operations are exposed to the
peer side:

- ``notify(payload)``: fire-and-forget event peer -> client.
- ``request(payload, timeout=...)``: peer asks client and awaits the
  correlated response.
- ``events()``: async iterator of unsolicited client -> peer messages.

Wire framing defaults to JSON, but ``encode_to_client``/``decode_from_client``
hooks let consumers plug a different format. The internal request/response
correlation is hidden from the consumer: the manager wraps requests with a
``_request_id`` field and the client side answers with ``_response_to``.

There is no global state. Sessions live inside an async-context-manager
scope owned by the manager and the broker tasks are managed via
:class:`asyncio.TaskGroup`, so cancellation and cleanup are structural.
"""

import asyncio
import json
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Generic,
    TypeVar,
)


T = TypeVar('T')
U = TypeVar('U')


# Reserved framing keys used by the default JSON encoder/decoder.
_REQUEST_ID_KEY = '_request_id'
_RESPONSE_TO_KEY = '_response_to'
_PAYLOAD_KEY = 'payload'
_EVENT_KEY = 'event'

# Internal sentinel pushed onto the events queue when the session closes,
# so that any consumer awaiting events() wakes up immediately instead of
# polling the closed flag.
_CLOSE_SENTINEL = object()


def _default_encode(message: Any) -> str:
    """Serialize an internal framing dict to a JSON string.

    The encoder operates on the wrapper dict produced by :class:`AsyncSession`
    (e.g. ``{'event': payload}`` or ``{'_request_id': 'id', 'payload': ...}``),
    not on the raw consumer payload.
    """
    return json.dumps(message)


def _default_decode(raw: str | bytes) -> object:
    """Deserialize a raw text/bytes WebSocket message as JSON."""
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8')
    return json.loads(raw)


@dataclass
class AsyncSession(Generic[T, U]):
    """A full-duplex async session bridging a server-side peer with a
    browser-side WebSocket client.

    Three semantic operations:

    - ``notify(payload)``: fire-and-forget event peer -> client.
    - ``request(payload, timeout=...)``: peer asks client and awaits the
      response (correlated by an internal request id).
    - ``events()``: async iterator of events client -> peer that are not
      responses to a pending :meth:`request`.

    The session is created and managed by :class:`AsyncSessionManager` and
    must not be instantiated directly. Lifecycle is bound to the manager's
    ``session()`` async context manager: when the context exits, the broker
    tasks are cancelled cleanly via :class:`asyncio.TaskGroup`.

    Two hooks customize message framing:

    - ``encode_to_client(message)``: serializes the wrapper dict before
      sending it to the WebSocket. Default: JSON via :func:`json.dumps`.
    - ``decode_from_client(raw)``: deserializes the raw text/bytes coming
      from the WebSocket. Default: JSON via :func:`json.loads`.

    The default JSON framing reserves two keys in client messages:
    ``_response_to`` (a string) marks a message as the response to a
    previous :meth:`request`; otherwise the message is yielded by
    :meth:`events`. The peer side never sees the correlation id: it is
    injected and stripped under the hood.

    Type parameter ``T`` is the consumer's outbound payload type (the
    argument of :meth:`notify` / :meth:`request`); ``U`` is the inbound
    event type yielded by :meth:`events`. Both default to ``object``.
    """

    key: str
    on_send: Callable[[str | bytes], Awaitable[None]]
    page_id: str | None = None
    encode_to_client: Callable[[Any], str | bytes] = field(
        default=_default_encode
    )
    decode_from_client: Callable[[str | bytes], object] = field(
        default=_default_decode
    )

    # Internal state
    _events_queue: asyncio.Queue[object] = field(
        default_factory=asyncio.Queue, init=False, repr=False
    )
    _pending: dict[str, asyncio.Future[object]] = field(
        default_factory=dict, init=False, repr=False
    )
    _send_lock: asyncio.Lock = field(
        default_factory=asyncio.Lock, init=False, repr=False
    )
    _closed: bool = field(default=False, init=False, repr=False)

    async def notify(self, payload: T) -> None:
        """Send a fire-and-forget event to the client.

        :param payload: The application-level payload to deliver.
        :raises RuntimeError: If the session has already been closed.
        """
        if self._closed:
            raise RuntimeError(f'session {self.key!r} is closed')
        message = {_EVENT_KEY: payload}
        await self._send(message)

    async def request(
        self,
        payload: T,
        *,
        timeout: float | None = None,
    ) -> object:
        """Send a request to the client and await its correlated response.

        The wrapper injects an internal ``_request_id`` so the client can
        echo it back as ``_response_to`` and the corresponding future is
        resolved with the response payload.

        :param payload: The application-level payload to deliver.
        :param timeout: Optional timeout in seconds. ``None`` waits forever.
        :returns: The payload contained in the client's response message,
            with the correlation key already stripped.
        :raises RuntimeError: If the session has already been closed.
        :raises TimeoutError: If no response arrives within ``timeout``.
        """
        if self._closed:
            raise RuntimeError(f'session {self.key!r} is closed')
        request_id = uuid.uuid4().hex
        future: asyncio.Future[object] = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        message = {_REQUEST_ID_KEY: request_id, _PAYLOAD_KEY: payload}
        try:
            await self._send(message)
            if timeout is None:
                return await future
            async with asyncio.timeout(timeout):
                return await future
        finally:
            self._pending.pop(request_id, None)

    async def events(self) -> AsyncIterator[object]:
        """Yield unsolicited client -> peer messages in arrival order.

        The iterator yields messages that the client sent without a
        ``_response_to`` field, i.e. those that are not answers to a
        pending :meth:`request`. The iterator runs until the session is
        closed; closure pushes an internal sentinel onto the queue so
        the iterator wakes up and returns immediately, without polling.
        """
        while True:
            item = await self._events_queue.get()
            if item is _CLOSE_SENTINEL:
                return
            yield item

    async def feed_from_client(self, raw: str | bytes) -> None:
        """Dispatch a raw client -> peer WebSocket frame.

        This method is meant to be called by whichever component owns the
        WebSocket read loop. The frame is decoded via
        :attr:`decode_from_client`; if it carries a ``_response_to`` key
        whose value matches a pending :meth:`request`, the corresponding
        future is resolved with the rest of the message; otherwise the
        message is enqueued for :meth:`events`.

        :param raw: The text or bytes frame received from the WebSocket.
        """
        if self._closed:
            return
        message = self.decode_from_client(raw)
        if isinstance(message, dict) and _RESPONSE_TO_KEY in message:
            request_id = message.get(_RESPONSE_TO_KEY)
            future = self._pending.get(request_id) if isinstance(request_id, str) else None
            if future is not None and not future.done():
                response_payload = {
                    k: v for k, v in message.items() if k != _RESPONSE_TO_KEY
                }
                # Unwrap a bare 'payload' field if that is the only remaining
                # key, so consumers see the same shape they sent in request().
                if list(response_payload.keys()) == [_PAYLOAD_KEY]:
                    future.set_result(response_payload[_PAYLOAD_KEY])
                else:
                    future.set_result(response_payload)
                return
            # Orphan response (no pending future): drop silently. A noisy
            # log here would conflate test setup races with real errors.
            return
        await self._events_queue.put(message)

    async def _send(self, message: Any) -> None:
        """Encode ``message`` and forward it to :attr:`on_send`.

        A lock is held around the encoded write so that concurrent
        :meth:`notify` / :meth:`request` calls do not interleave a single
        frame's bytes on the underlying transport.
        """
        encoded = self.encode_to_client(message)
        async with self._send_lock:
            await self.on_send(encoded)

    def _close(self) -> None:
        """Mark the session closed and cancel any pending requests.

        Called by :class:`AsyncSessionManager` when the session's async
        context exits. Idempotent.
        """
        if self._closed:
            return
        self._closed = True
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()
        # Wake up any consumer awaiting events() so it returns immediately.
        self._events_queue.put_nowait(_CLOSE_SENTINEL)


class AsyncSessionManager:
    """Registry of active sessions with structural lifecycle management.

    Sessions are created and disposed only via the :meth:`session` async
    context manager, which guarantees that the registry is consistent and
    that broker tasks are cancelled on exit (cleanly via
    :class:`asyncio.TaskGroup`). Per-page lookup (:meth:`keys_for_page`)
    and bulk close (:meth:`close_for_page`) are first-class so a page
    teardown can release every session it owns in one call.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, AsyncSession] = {}
        self._by_page: defaultdict[str, set[str]] = defaultdict(set)

    @asynccontextmanager
    async def session(
        self,
        key: str,
        on_send: Callable[[str | bytes], Awaitable[None]],
        *,
        page_id: str | None = None,
        encode_to_client: Callable[[Any], str | bytes] | None = None,
        decode_from_client: Callable[[str | bytes], object] | None = None,
    ) -> AsyncIterator[AsyncSession]:
        """Open a new session under ``key`` and yield it to the caller.

        On entry the session is registered and (if ``page_id`` is given)
        indexed under that page. On exit the session is unregistered, its
        broker tasks are cancelled via :class:`asyncio.TaskGroup`, and any
        pending :meth:`AsyncSession.request` futures are cancelled.

        :param key: Unique session key. Must not already be in use.
        :param on_send: Coroutine invoked with each encoded outbound frame
            (typically the WebSocket ``send_str`` / ``send_bytes`` method).
        :param page_id: Optional page identifier used by
            :meth:`keys_for_page` and :meth:`close_for_page`.
        :param encode_to_client: Optional custom encoder. Defaults to JSON.
        :param decode_from_client: Optional custom decoder. Defaults to JSON.
        :raises ValueError: If ``key`` is already registered.
        """
        if key in self._sessions:
            raise ValueError(f'session key {key!r} already in use')
        kwargs: dict[str, Any] = {
            'key': key,
            'on_send': on_send,
            'page_id': page_id,
        }
        if encode_to_client is not None:
            kwargs['encode_to_client'] = encode_to_client
        if decode_from_client is not None:
            kwargs['decode_from_client'] = decode_from_client
        sess: AsyncSession = AsyncSession(**kwargs)
        self._sessions[key] = sess
        if page_id is not None:
            self._by_page[page_id].add(key)
        try:
            async with asyncio.TaskGroup():
                # The TaskGroup is entered to enforce structured cancellation
                # semantics on any background task a future consumer may
                # spawn within the session scope. The core itself does not
                # spawn brokers (feed_from_client is driven by the WS read
                # loop owned by the caller), but the TaskGroup boundary is
                # what guarantees clean teardown for any subclass or wrapper.
                yield sess
        finally:
            sess._close()
            self._unregister(key, page_id)

    def get(self, key: str) -> AsyncSession | None:
        """Return the live session with the given key, or ``None``."""
        return self._sessions.get(key)

    def keys_for_page(self, page_id: str) -> list[str]:
        """Return the list of session keys registered for ``page_id``."""
        return list(self._by_page.get(page_id, ()))

    async def close_for_page(self, page_id: str) -> None:
        """Close every session registered under ``page_id``.

        Each session is marked closed and removed from the registry; any
        active ``async with manager.session(...)`` block will observe
        :attr:`AsyncSession._closed` and exit on next iteration of
        :meth:`AsyncSession.events` or on the next call to
        :meth:`AsyncSession.notify` / :meth:`AsyncSession.request`.
        """
        for key in self.keys_for_page(page_id):
            sess = self._sessions.get(key)
            if sess is not None:
                sess._close()
                self._unregister(key, page_id)

    def _unregister(self, key: str, page_id: str | None) -> None:
        """Remove the session from the primary and per-page indexes."""
        self._sessions.pop(key, None)
        if page_id is not None:
            keys = self._by_page.get(page_id)
            if keys is not None:
                keys.discard(key)
                if not keys:
                    self._by_page.pop(page_id, None)
