# Copyright 2026 Softwell S.r.l.
# Licensed under the Apache License, Version 2.0

"""WSGI middleware for gzip compression of HTTP responses.

Compresses responses when all criteria are met:
    - Client accepts gzip (Accept-Encoding header)
    - Response size >= minimum_size
    - Content-Type is compressible (text/*, application/json, etc.)
    - Compressed size < original size

Adds Content-Encoding: gzip and Vary: Accept-Encoding headers.
Updates Content-Length to compressed size.

Enable via siteconfig::

    <wsgi compression="true" compression_min_size="500" compression_level="6"/>
"""

import gzip
import io


COMPRESSIBLE_TYPES = (
    'text/',
    'application/json',
    'application/javascript',
    'application/xml',
    'application/xhtml+xml',
)


class GzipMiddleware:
    """WSGI middleware that applies gzip compression to responses.

    Wraps the WSGI app, intercepts responses, and compresses them
    when beneficial. Non-compressible or small responses pass through
    unchanged.

    Args:
        app: The WSGI application to wrap.
        minimum_size: Minimum response body size in bytes to trigger
            compression. Default 500.
        compression_level: Gzip compression level 1-9. Default 6.
    """

    def __init__(self, app, minimum_size=500, compression_level=6):
        self.app = app
        self.minimum_size = minimum_size
        self.compression_level = min(9, max(1, compression_level))

    def _accepts_gzip(self, environ):
        """Check if the client accepts gzip encoding."""
        accept = environ.get('HTTP_ACCEPT_ENCODING', '')
        return 'gzip' in accept.lower()

    def _is_compressible(self, content_type):
        """Check if the content type should be compressed."""
        if not content_type:
            return False
        content_type = content_type.lower()
        return any(content_type.startswith(ct) for ct in COMPRESSIBLE_TYPES)

    def _compress(self, data):
        """Compress data with gzip. Returns compressed bytes."""
        buf = io.BytesIO()
        with gzip.GzipFile(
            mode='wb', fileobj=buf, compresslevel=self.compression_level
        ) as gz:
            gz.write(data)
        return buf.getvalue()

    def __call__(self, environ, start_response):
        if not self._accepts_gzip(environ):
            return self.app(environ, start_response)

        # Buffer the response to decide whether to compress
        status_and_headers = []
        # write() data must precede iterator data per PEP 3333
        write_parts = []
        iter_parts = []

        def buffered_start_response(status, headers, exc_info=None):
            status_and_headers.append((status, headers, exc_info))
            return write_parts.append

        app_iter = self.app(environ, buffered_start_response)
        try:
            for chunk in app_iter:
                iter_parts.append(chunk)
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()

        if not status_and_headers:
            return []

        status, headers, exc_info = status_and_headers[0]
        body = b''.join(write_parts + iter_parts)

        # Find content type from response headers
        content_type = None
        already_encoded = False
        for name, value in headers:
            lower_name = name.lower()
            if lower_name == 'content-type':
                content_type = value
            elif lower_name == 'content-encoding':
                already_encoded = True

        should_compress = (
            not already_encoded
            and len(body) >= self.minimum_size
            and self._is_compressible(content_type)
        )

        if should_compress:
            compressed = self._compress(body)
            if len(compressed) < len(body):
                body = compressed
                # Rebuild headers: update content-length, add gzip headers
                has_vary = False
                new_headers = []
                for name, value in headers:
                    lower_name = name.lower()
                    if lower_name == 'content-length':
                        new_headers.append(('Content-Length', str(len(body))))
                    elif lower_name == 'content-encoding':
                        continue
                    elif lower_name == 'vary':
                        has_vary = True
                        if 'accept-encoding' not in value.lower():
                            value = value + ', Accept-Encoding'
                        new_headers.append((name, value))
                    else:
                        new_headers.append((name, value))
                new_headers.append(('Content-Encoding', 'gzip'))
                if not has_vary:
                    new_headers.append(('Vary', 'Accept-Encoding'))
                headers = new_headers

        start_response(status, headers, exc_info)
        return [body]
