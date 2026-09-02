"""Benchmark: the legacy storage services against genro-storage.

The same operations, timed in both modes, on a local mount and on an
S3-compatible endpoint. Repetition counts are declared in OPERATIONS and
printed with the table.

Run with:
    cd gnrpy && pytest tests/core/gnrstorage_benchmark.py -s -q
The -s flag is needed to see the printed timing table.

The S3 half needs GNR_TEST_S3_ENDPOINT and friends (see storage_fixtures.py):
    export GNR_TEST_S3_ENDPOINT=http://127.0.0.1:9000
Without it, that half skips with the reason naming the variable.
"""

import sys
import time

import pytest

from core.storage_fixtures import (MODES, S3_ENDPOINT, local_storage,
                                   s3_storage, s3_unavailable_reason)

S3_SKIP_REASON = s3_unavailable_reason()
requires_s3 = pytest.mark.skipif(S3_SKIP_REASON is not None, reason=str(S3_SKIP_REASON))

SMALL = b'x' * 4096
LARGE = b'y' * (4 * 1024 * 1024)
CHILDREN_COUNT = 100


def _out(text):
    sys.stdout.write(text)


def _write(storage, path, payload):
    node = storage.node(path)
    with node.open('wb') as fp:
        fp.write(payload)


def _read(storage, path):
    with storage.node(path).open('rb') as fp:
        fp.read()


def _prepare(storage):
    """Everything the read-side operations need, written once per mode."""
    _write(storage, 'st:bench/small.dat', SMALL)
    _write(storage, 'st:bench/large.dat', LARGE)
    for index in range(CHILDREN_COUNT):
        _write(storage, 'st:bench/listing/file_%03d.dat' % index, b'z')


# (label, repetitions, callable)
OPERATIONS = [
    ('write small (4KB)', 10, lambda st: _write(st, 'st:bench/w_small.dat', SMALL)),
    ('write large (4MB)', 3, lambda st: _write(st, 'st:bench/w_large.dat', LARGE)),
    ('read small (4KB)', 10, lambda st: _read(st, 'st:bench/small.dat')),
    ('read large (4MB)', 3, lambda st: _read(st, 'st:bench/large.dat')),
    ('exists', 50, lambda st: st.node('st:bench/small.dat').exists),
    ('size', 50, lambda st: st.node('st:bench/small.dat').size),
    ('mtime', 50, lambda st: st.node('st:bench/small.dat').mtime),
    ('md5hash', 50, lambda st: st.node('st:bench/small.dat').md5hash),
    ('children (%d files)' % CHILDREN_COUNT, 10,
     lambda st: st.node('st:bench/listing').children()),
    ('copy same mount', 10, lambda st: st.node('st:bench/small.dat').copy(
        st.node('st:bench/copied.dat'))),
    ('internal_url', 50, lambda st: st.node('st:bench/small.dat').internal_url()),
]


def _time_operation(storage, operation, repetitions):
    start = time.perf_counter()
    for _ in range(repetitions):
        operation(storage)
    return (time.perf_counter() - start) * 1000


def _run(mount_label, build):
    """Time every operation in both modes and print one table."""
    timings = {}
    for mode in MODES:
        storage = build(mode)
        try:
            _prepare(storage)
            for label, repetitions, operation in OPERATIONS:
                timings[(label, mode)] = _time_operation(storage, operation, repetitions)
        finally:
            storage.cleanup()

    _out('\n=== storage benchmark: %s ===\n' % mount_label)
    _out('%-26s %5s %12s %12s %8s\n' % ('operation', 'reps', 'legacy_ms', 'genro_ms', 'ratio'))
    for label, repetitions, _operation in OPERATIONS:
        legacy_ms = timings[(label, 'legacy')]
        genro_ms = timings[(label, 'genro')]
        ratio = genro_ms / legacy_ms if legacy_ms else float('inf')
        _out('%-26s %5d %12.2f %12.2f %8.2f\n'
             % (label, repetitions, legacy_ms, genro_ms, ratio))
    _out('ratio > 1 means genro-storage is slower on this operation.\n')
    return timings


def test_local_benchmark(tmp_path):
    def build(mode):
        base = tmp_path / mode
        base.mkdir()
        return local_storage(mode, {'st': str(base)})

    timings = _run('local mount', build)
    assert timings


@requires_s3
def test_s3_benchmark():
    timings = _run('S3 mount (%s)' % S3_ENDPOINT, s3_storage)
    assert timings
