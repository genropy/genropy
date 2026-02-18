# -*- coding: utf-8 -*-
"""gnrenv - Genro environment path constants.

This module defines the default paths for the Genro framework directories:

- ``GNRHOME``: Root directory of the Genro installation
- ``GNRINSTANCES``: Directory containing Genro instances
- ``GNRPACKAGES``: Directory containing Genro packages
- ``GNRSITES``: Directory containing Genro sites

Paths are resolved from environment variables (``GNRHOME``, ``GNRINSTANCES``,
``GNRPACKAGES``, ``GNRSITES``) or fall back to platform-specific defaults.
"""

from __future__ import annotations

import os
import sys

try:
    from gnr.core import gnrhome

    _PLATFORM_DEFAULT_PATH: str = gnrhome.PATH  # pragma: no cover
except Exception:  # REVIEW:COMPAT — bare except catches too broadly
    # FIXME: testing in win32 env?
    if sys.platform == "win32":  # pragma: no cover
        _PLATFORM_DEFAULT_PATH = r"C:\genro"
    else:
        _PLATFORM_DEFAULT_PATH = "/usr/local/genro"

_GNRHOME: tuple[str, ...] = os.path.split(
    os.environ.get("GNRHOME", _PLATFORM_DEFAULT_PATH)
)
GNRHOME: str = os.path.join(*_GNRHOME)

_GNRINSTANCES: tuple[str, ...] = (
    os.environ.get("GNRINSTANCES") and os.path.split(os.environ.get("GNRINSTANCES"))  # type: ignore[arg-type]
) or (_GNRHOME + ("data", "instances"))
GNRINSTANCES: str = os.path.join(*_GNRINSTANCES)

_GNRPACKAGES: tuple[str, ...] = (
    os.environ.get("GNRPACKAGES") and os.path.split(os.environ.get("GNRPACKAGES"))  # type: ignore[arg-type]
) or (_GNRHOME + ("packages",))
GNRPACKAGES: str = os.path.join(*_GNRPACKAGES)

_GNRSITES: tuple[str, ...] = (
    os.environ.get("GNRSITES") and os.path.split(os.environ.get("GNRSITES"))  # type: ignore[arg-type]
) or (_GNRHOME + ("data", "sites"))
GNRSITES: str = os.path.join(*_GNRSITES)

__all__ = ["GNRHOME", "GNRINSTANCES", "GNRPACKAGES", "GNRSITES"]
