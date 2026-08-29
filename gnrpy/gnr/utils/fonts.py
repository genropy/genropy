#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# AFM character widths for standard PDF fonts.
# Source: Adobe Font Metrics files (public domain).
# Units are 1/1000 of the font size in points.
# Example: at 10pt, 'A' in Helvetica = 667/1000 * 10 = 6.67 pt wide.
#
# Width data is stored in the shared resources directory
# (common/fonts/afm_widths.json) and loaded at first use.

import json
import os

from gnr.core.gnrsys import expandpath
from gnr.utils import logger

_AFM_WIDTHS = None

_DEFAULT_CHAR_WIDTH = 556  # fallback for unknown chars (avg lowercase Helvetica)


def _afm_widths_candidates():
    """Yield candidate paths of ``afm_widths.json``, most authoritative first.

    The shared ``resources`` directory is declared in environment.xml in both
    checkout and installed layouts, so the gnr_config lookup works everywhere
    (same resolution used by ``resource_name_to_path``). The checkout-relative
    path is kept as fallback for contexts without a configured environment.
    """
    # deferred import: gnr.core.gnrconfig imports gnr.core.gnrstring,
    # which imports this module at load time
    from gnr.core.gnrconfig import getGnrConfig
    relative_path = os.path.join('common', 'fonts', 'afm_widths.json')
    try:
        environment_xml = getGnrConfig()['gnr.environment_xml']
    except Exception:  # getGnrConfig raises a bare Exception when unconfigured
        environment_xml = None
    if environment_xml and 'resources' in environment_xml:
        for path in environment_xml.digest('resources:#a.path'):
            yield expandpath(os.path.join(path, relative_path))
    yield os.path.normpath(os.path.join(os.path.dirname(__file__),
                                        '..', '..', '..', 'resources', relative_path))


def _load_afm_widths():
    global _AFM_WIDTHS
    if _AFM_WIDTHS is not None:
        return _AFM_WIDTHS
    for json_path in _afm_widths_candidates():
        if not os.path.isfile(json_path):
            continue
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                _AFM_WIDTHS = json.load(f)
            return _AFM_WIDTHS
        except (ValueError, OSError):
            logger.warning('Invalid AFM metrics file %s, skipped', json_path)
    logger.warning('AFM metrics file not found: string widths will be approximate')
    _AFM_WIDTHS = {'Helvetica': {}}
    return _AFM_WIDTHS


def string_width(text, font_name='Helvetica', font_size=10):
    """Return the width in points of *text* rendered in *font_name* at *font_size* pt.

    Uses embedded AFM metrics — no font files or external dependencies needed.
    Falls back to Helvetica widths for unknown font names.
    """
    widths_map = _load_afm_widths()
    widths = widths_map.get(font_name) or widths_map['Helvetica']
    return sum(widths.get(c, _DEFAULT_CHAR_WIDTH) for c in (text or '')) * font_size / 1000.0
