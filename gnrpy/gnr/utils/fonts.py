#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# AFM character widths for standard PDF fonts.
# Source: Adobe Font Metrics files (public domain).
# Units are 1/1000 of the font size in points.
# Example: at 10pt, 'A' in Helvetica = 667/1000 * 10 = 6.67 pt wide.
#
# Width data is stored in resources/common/fonts/afm_widths.json and loaded
# at first use.

import json
import os

_AFM_WIDTHS = None

_DEFAULT_CHAR_WIDTH = 556  # fallback for unknown chars (avg lowercase Helvetica)


def _load_afm_widths():
    global _AFM_WIDTHS
    if _AFM_WIDTHS is not None:
        return _AFM_WIDTHS
    json_path = os.path.join(
        os.path.dirname(__file__),
        '..', '..', '..', 'resources', 'common', 'fonts', 'afm_widths.json'
    )
    json_path = os.path.normpath(json_path)
    with open(json_path, 'r', encoding='utf-8') as f:
        _AFM_WIDTHS = json.load(f)
    return _AFM_WIDTHS


def string_width(text, font_name='Helvetica', font_size=10):
    """Return the width in points of *text* rendered in *font_name* at *font_size* pt.

    Uses embedded AFM metrics — no font files or external dependencies needed.
    Falls back to Helvetica widths for unknown font names.
    """
    widths_map = _load_afm_widths()
    widths = widths_map.get(font_name) or widths_map['Helvetica']
    return sum(widths.get(c, _DEFAULT_CHAR_WIDTH) for c in (text or '')) * font_size / 1000.0
