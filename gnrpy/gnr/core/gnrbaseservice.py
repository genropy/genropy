# -*- coding: utf-8 -*-
"""gnrbaseservice - Backward-compatibility alias for GnrBaseService.

This module re-exports :class:`gnr.lib.services.GnrBaseService` to maintain
backward compatibility for code that imports from ``gnr.core.gnrbaseservice``.

The canonical location is :mod:`gnr.lib.services`.
"""

from gnr.lib.services import GnrBaseService  # noqa: F401

__all__ = ["GnrBaseService"]
