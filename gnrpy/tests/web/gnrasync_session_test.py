# -*- coding: utf-8 -*-
"""Unit tests for the neutral AsyncSession core.

Pure asyncio, no I/O, no framework mocks: the tests exercise the public
API of :mod:`gnr.web.gnrasync_session` against a fake transport that just
captures the bytes/strings written by ``on_send``.
"""

import asyncio
import json

import pytest

from gnr.web.gnrasync_session import AsyncSessionManager


def _make_collector():
    """Return ``(collected, on_send)`` where ``on_send`` appends to ``collected``."""
    collected: list[str | bytes] = []

    async def on_send(message: str | bytes) -> None:
        collected.append(message)

    return collected, on_send


@pytest.mark.asyncio
async def test_session_lifecycle_via_context_manager():
    manager = AsyncSessionManager()
    _, on_send = _make_collector()
    assert manager.get('s1') is None

    async with manager.session('s1', on_send) as sess:
        assert manager.get('s1') is sess
        assert sess.key == 's1'

    assert manager.get('s1') is None

    # No leaked tasks attributable to this manager: every Task currently
    # alive should belong to the test harness, not to the closed session.
    current = asyncio.current_task()
    leftover = [
        t for t in asyncio.all_tasks()
        if t is not current and not t.done()
    ]
    # The pytest-asyncio runner may keep its own tasks; we only care that
    # no task references our session.
    for task in leftover:
        assert 'AsyncSession' not in repr(task)


@pytest.mark.asyncio
async def test_notify_encodes_and_forwards():
    manager = AsyncSessionManager()
    collected, on_send = _make_collector()

    async with manager.session('s1', on_send) as sess:
        await sess.notify({'kind': 'hello', 'text': 'world'})

    assert len(collected) == 1
    decoded = json.loads(collected[0])
    assert decoded == {'event': {'kind': 'hello', 'text': 'world'}}
    assert '_request_id' not in decoded


@pytest.mark.asyncio
async def test_request_response_correlation():
    manager = AsyncSessionManager()
    collected, on_send = _make_collector()

    async with manager.session('s1', on_send) as sess:
        async def respond_when_sent():
            # Wait for the request frame, then synthesize a response.
            for _ in range(50):
                if collected:
                    break
                await asyncio.sleep(0.01)
            sent = json.loads(collected[0])
            request_id = sent['_request_id']
            response = json.dumps({
                '_response_to': request_id,
                'payload': {'answer': 42},
            })
            await sess.feed_from_client(response)

        responder = asyncio.create_task(respond_when_sent())
        try:
            result = await sess.request({'q': 'meaning?'}, timeout=1.0)
        finally:
            await responder

    assert result == {'answer': 42}


@pytest.mark.asyncio
async def test_request_timeout_raises():
    manager = AsyncSessionManager()
    _, on_send = _make_collector()

    async with manager.session('s1', on_send) as sess:
        with pytest.raises(TimeoutError):
            await sess.request({'q': 'no-answer'}, timeout=0.05)
        # The pending dict must be cleaned up after the timeout.
        assert sess._pending == {}


@pytest.mark.asyncio
async def test_events_iterator_yields_in_order():
    manager = AsyncSessionManager()
    _, on_send = _make_collector()

    received: list[object] = []

    async with manager.session('s1', on_send) as sess:
        await sess.feed_from_client(json.dumps({'msg': 'a'}))
        await sess.feed_from_client(json.dumps({'msg': 'b'}))

        async def consume_two():
            count = 0
            async for evt in sess.events():
                received.append(evt)
                count += 1
                if count == 2:
                    return

        await asyncio.wait_for(consume_two(), timeout=1.0)

    assert received == [{'msg': 'a'}, {'msg': 'b'}]


@pytest.mark.asyncio
async def test_response_does_not_leak_into_events():
    manager = AsyncSessionManager()
    collected, on_send = _make_collector()

    received: list[object] = []

    async with manager.session('s1', on_send) as sess:
        async def producer():
            # Wait for the request frame so we can pick up its id.
            for _ in range(50):
                if collected:
                    break
                await asyncio.sleep(0.01)
            request_id = json.loads(collected[0])['_request_id']
            # Feed a non-response, then the response, then another non-response.
            await sess.feed_from_client(json.dumps({'msg': 'before'}))
            await sess.feed_from_client(json.dumps({
                '_response_to': request_id, 'payload': 'OK',
            }))
            await sess.feed_from_client(json.dumps({'msg': 'after'}))

        async def consumer():
            count = 0
            async for evt in sess.events():
                received.append(evt)
                count += 1
                if count == 2:
                    return

        prod = asyncio.create_task(producer())
        cons = asyncio.create_task(consumer())

        result = await sess.request('q', timeout=1.0)
        await prod
        await asyncio.wait_for(cons, timeout=1.0)

    assert result == 'OK'
    assert received == [{'msg': 'before'}, {'msg': 'after'}]


@pytest.mark.asyncio
async def test_multiple_sessions_are_isolated():
    manager = AsyncSessionManager()
    collected_a, on_send_a = _make_collector()
    collected_b, on_send_b = _make_collector()

    async with manager.session('A', on_send_a) as sa:
        async with manager.session('B', on_send_b) as sb:
            await sa.notify('to-A')
            await sb.notify('to-B')
            assert manager.get('A') is sa
            assert manager.get('B') is sb

    assert json.loads(collected_a[0]) == {'event': 'to-A'}
    assert json.loads(collected_b[0]) == {'event': 'to-B'}
    assert manager.get('A') is None
    assert manager.get('B') is None


@pytest.mark.asyncio
async def test_close_for_page_targets_only_matching_page():
    manager = AsyncSessionManager()
    _, send1 = _make_collector()
    _, send2 = _make_collector()
    _, send3 = _make_collector()

    p1_a_done = asyncio.Event()
    p1_b_done = asyncio.Event()
    p2_done = asyncio.Event()

    async def run_session(key, page_id, on_send, done_event):
        async with manager.session(key, on_send, page_id=page_id):
            await done_event.wait()

    t1 = asyncio.create_task(run_session('p1a', 'P1', send1, p1_a_done))
    t2 = asyncio.create_task(run_session('p1b', 'P1', send2, p1_b_done))
    t3 = asyncio.create_task(run_session('p2', 'P2', send3, p2_done))

    # Give the tasks a chance to enter the context.
    for _ in range(50):
        if all(manager.get(k) is not None for k in ('p1a', 'p1b', 'p2')):
            break
        await asyncio.sleep(0.01)

    assert sorted(manager.keys_for_page('P1')) == ['p1a', 'p1b']
    assert manager.keys_for_page('P2') == ['p2']

    await manager.close_for_page('P1')

    assert manager.get('p1a') is None
    assert manager.get('p1b') is None
    assert manager.get('p2') is not None
    assert manager.keys_for_page('P1') == []

    # Release the still-running task contexts so the test exits cleanly.
    p1_a_done.set()
    p1_b_done.set()
    p2_done.set()
    await asyncio.gather(t1, t2, t3)


@pytest.mark.asyncio
async def test_custom_framing_roundtrip():
    """Custom encoder/decoder pair: JSON wrapped with a 'B:' byte prefix."""
    manager = AsyncSessionManager()
    collected, on_send = _make_collector()

    def encode(message):
        return b'B:' + json.dumps(message).encode('utf-8')

    def decode(raw):
        if isinstance(raw, str):
            raw = raw.encode('utf-8')
        assert raw.startswith(b'B:'), f'expected B: prefix, got {raw!r}'
        return json.loads(raw[2:].decode('utf-8'))

    async with manager.session(
        's1', on_send,
        encode_to_client=encode, decode_from_client=decode,
    ) as sess:
        # notify
        await sess.notify({'k': 1})
        assert collected[-1].startswith(b'B:')
        assert json.loads(collected[-1][2:]) == {'event': {'k': 1}}

        # request/response roundtrip with the same custom framing
        async def responder():
            for _ in range(50):
                if len(collected) >= 2:
                    break
                await asyncio.sleep(0.01)
            sent = json.loads(collected[1][2:])
            request_id = sent['_request_id']
            await sess.feed_from_client(
                b'B:' + json.dumps({
                    '_response_to': request_id, 'payload': 'ack',
                }).encode('utf-8')
            )

        task = asyncio.create_task(responder())
        try:
            result = await sess.request({'q': 1}, timeout=1.0)
        finally:
            await task

    assert result == 'ack'


@pytest.mark.asyncio
async def test_send_failure_propagates_and_unregisters():
    """An exception raised inside on_send must surface and clean up state."""
    manager = AsyncSessionManager()

    class Boom(Exception):
        pass

    async def bad_send(_message):
        raise Boom('boom')

    with pytest.raises(BaseExceptionGroup) as excinfo:
        async with manager.session('s1', bad_send) as sess:
            await sess.notify({'x': 1})

    # The TaskGroup wraps any exception escaping the body in an ExceptionGroup;
    # we just verify our underlying error is in there.
    flat = [
        e for e in _flatten_exception_group(excinfo.value)
        if isinstance(e, Boom)
    ]
    assert flat, f'Boom not found in {excinfo.value!r}'

    # Session must be unregistered even on failure.
    assert manager.get('s1') is None


@pytest.mark.asyncio
async def test_events_iterator_returns_immediately_on_close():
    """events() must wake up at once on close, not poll for the closed flag."""
    manager = AsyncSessionManager()
    _, on_send = _make_collector()

    loop = asyncio.get_running_loop()

    async with manager.session('s1', on_send) as sess:
        async def consume():
            collected = []
            async for item in sess.events():
                collected.append(item)
            return collected

        consumer = asyncio.create_task(consume())
        # Give the consumer a chance to suspend on queue.get().
        await asyncio.sleep(0)
        close_started_at = loop.time()

    # The session is now closed (context exited). The iterator must
    # complete promptly via the internal wakeup sentinel; if a polling
    # implementation regressed, this would only complete after the
    # polling tick (>= ~50ms in the original). We assert <10ms.
    result = await asyncio.wait_for(consumer, timeout=0.5)
    elapsed = loop.time() - close_started_at
    assert result == []
    assert elapsed < 0.01, f'events() took {elapsed * 1000:.1f}ms to wake up'


def _flatten_exception_group(exc):
    """Yield every leaf exception inside a (possibly nested) ExceptionGroup."""
    if isinstance(exc, BaseExceptionGroup):
        for inner in exc.exceptions:
            yield from _flatten_exception_group(inner)
    else:
        yield exc
