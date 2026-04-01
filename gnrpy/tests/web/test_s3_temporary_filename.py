import importlib.util
import os

import pytest

# S3TemporaryFilename lives under projects/gnrcore/ which is not on the
# default test sys.path.  We load it directly from the file system so the
# test can run without requiring a full GenroPy site setup.
_s3_module_path = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, os.pardir,
    'projects', 'gnrcore', 'packages', 'sys', 'resources',
    'services', 'storage', 'aws_s3.py',
)
_s3_module_path = os.path.normpath(_s3_module_path)


def _get_s3_temporary_filename_class():
    """Import S3TemporaryFilename from the aws_s3 module."""
    spec = importlib.util.spec_from_file_location('aws_s3', _s3_module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.S3TemporaryFilename


S3TemporaryFilename = _get_s3_temporary_filename_class()


class FakeS3Client:
    """Minimal fake S3 client for testing S3TemporaryFilename.

    Only the external dependency (boto3 S3 client) is faked.
    S3TemporaryFilename itself runs with real temp files and real fd handling.
    """

    def __init__(self, content=b'hello', fail_download=False, fail_upload=False):
        self.content = content
        self.fail_download = fail_download
        self.fail_upload = fail_upload
        self.uploaded = {}

    def download_file(self, bucket, key, dest):
        if self.fail_download:
            import botocore.exceptions
            raise botocore.exceptions.ClientError(
                {'Error': {'Code': '404', 'Message': 'Not Found'}},
                'GetObject',
            )
        with open(dest, 'wb') as f:
            f.write(self.content)

    def upload_file(self, src, bucket, key):
        if self.fail_upload:
            raise OSError('upload failed')
        with open(src, 'rb') as f:
            self.uploaded[key] = f.read()


def _make_ctx(s3_client, mode='r', keep=False, key='test/file.txt'):
    """Create an S3TemporaryFilename context manager."""
    return S3TemporaryFilename(
        bucket='test-bucket',
        key=key,
        s3_client=s3_client,
        mode=mode,
        keep=keep,
    )


class TestS3TemporaryFilenameFdLeak:
    """Regression tests for issue #759: tempfile.mkstemp() returns an open fd
    that was never closed in __exit__, causing EMFILE errors when processing
    thousands of S3 files (e.g. in zipFiles)."""

    def test_fd_closed_after_normal_exit(self):
        """fd must be closed after a normal with-block exit."""
        client = FakeS3Client(content=b'test data')
        ctx = _make_ctx(client)

        with ctx as local_path:
            fd = ctx.fd
            assert os.path.exists(local_path)
            os.fstat(fd)  # fd is still open during the block

        # After exiting, fd must be closed
        with pytest.raises(OSError):
            os.fstat(fd)

    def test_fd_closed_after_exception_in_block(self):
        """fd must be closed even if an exception occurs inside the with-block."""
        client = FakeS3Client(content=b'test data')
        ctx = _make_ctx(client)

        with pytest.raises(ValueError):
            with ctx as local_path:
                fd = ctx.fd
                raise ValueError('simulated error')

        with pytest.raises(OSError):
            os.fstat(fd)

    def test_fd_closed_when_upload_fails(self):
        """fd must be closed even if upload_file raises during __exit__."""
        client = FakeS3Client(content=b'original', fail_upload=True)
        ctx = _make_ctx(client, mode='w')

        with pytest.raises(OSError, match='upload failed'):
            with ctx as local_path:
                fd = ctx.fd
                with open(local_path, 'wb') as f:
                    f.write(b'modified')

        with pytest.raises(OSError):
            os.fstat(fd)

    def test_temp_file_removed_when_keep_false(self):
        """Temp file must be removed when keep=False (default)."""
        client = FakeS3Client(content=b'data')
        ctx = _make_ctx(client, keep=False)

        with ctx as local_path:
            assert os.path.exists(local_path)

        assert not os.path.exists(local_path)

    def test_temp_file_kept_when_keep_true(self):
        """Temp file must survive when keep=True."""
        client = FakeS3Client(content=b'data')
        ctx = _make_ctx(client, keep=True)

        with ctx as local_path:
            pass

        assert os.path.exists(local_path)
        os.unlink(local_path)

    def test_no_fd_leak_over_many_iterations(self):
        """Simulates the zipFiles loop: many sequential context managers
        must not accumulate open file descriptors."""
        client = FakeS3Client(content=b'x' * 100)
        fds = []

        for i in range(200):
            ctx = _make_ctx(client, key=f'test/file_{i}.txt')
            with ctx as local_path:
                fds.append(ctx.fd)

        for fd in fds:
            with pytest.raises(OSError):
                os.fstat(fd)

    def test_download_failure_still_closes_fd(self):
        """When S3 download fails (ClientError), fd must still be closed on exit."""
        client = FakeS3Client(fail_download=True)
        ctx = _make_ctx(client)

        with ctx as local_path:
            fd = ctx.fd

        with pytest.raises(OSError):
            os.fstat(fd)
