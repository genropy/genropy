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

_NARROW_FACTOR = 0.82  # Adobe Helvetica-Narrow is Helvetica condensed to 82%

# common CSS font-family names -> AFM metrics key (matched case-insensitively)
_FONT_ALIASES = {
    'arial': 'Helvetica',
    'liberation sans': 'Helvetica',
    'sans-serif': 'Helvetica',
    'arial narrow': 'Helvetica-Narrow',
    'helvetica narrow': 'Helvetica-Narrow',
    'liberation sans narrow': 'Helvetica-Narrow',
    'times': 'Times-Roman',
    'times new roman': 'Times-Roman',
    'liberation serif': 'Times-Roman',
    'serif': 'Times-Roman',
    'courier new': 'Courier',
    'liberation mono': 'Courier',
    'monospace': 'Courier',
}


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


def _get_widths(font_name):
    """Return the char-width map for *font_name*, or ``None`` if unavailable.

    ``*-Narrow`` variants missing from the metrics file are derived from the
    base font scaled by ``_NARROW_FACTOR`` (Adobe's Helvetica-Narrow is a
    linearly condensed Helvetica) and cached for later lookups.
    """
    widths_map = _load_afm_widths()
    widths = widths_map.get(font_name)
    if widths is None and font_name and font_name.endswith('-Narrow'):
        base = widths_map.get(font_name[:-len('-Narrow')])
        if base is not None:
            widths = {c: w * _NARROW_FACTOR for c, w in base.items()}
            widths_map[font_name] = widths
    return widths


def resolve_font_name(font_family, default='Helvetica'):
    """Resolve a CSS font-family stack to the name of a font with AFM metrics.

    Walks the comma-separated stack and returns the first entry with known
    metrics, either directly (e.g. ``'Courier-Bold'``) or through the alias
    table (e.g. ``'Arial Narrow'`` -> ``'Helvetica-Narrow'``). Returns
    *default* when nothing matches.
    """
    for name in str(font_family or '').split(','):
        name = name.strip().strip('"\'').strip()
        if not name:
            continue
        if _get_widths(name) is not None:
            return name
        alias = _FONT_ALIASES.get(name.lower())
        if alias is not None and _get_widths(alias) is not None:
            return alias
    return default


def font_size_pt(value, default=10):
    """Return a CSS font-size value (``9``, ``'9pt'``, ``'12px'``) in points."""
    if isinstance(value, (int, float)):
        return float(value)
    v = str(value or '').strip().lower()
    factor = 1.0
    if v.endswith('pt'):
        v = v[:-2]
    elif v.endswith('px'):
        v = v[:-2]
        factor = 0.75  # CSS reference pixel: 1px = 3/4pt
    try:
        return float(v) * factor
    except ValueError:
        return float(default)


def string_width(text, font_name='Helvetica', font_size=10):
    """Return the width in points of *text* rendered in *font_name* at *font_size* pt.

    Uses embedded AFM metrics — no font files or external dependencies needed.
    Falls back to Helvetica widths for unknown font names.
    """
    widths = _get_widths(font_name)
    if widths is None:
        widths = _load_afm_widths()['Helvetica']
    return sum(widths.get(c, _DEFAULT_CHAR_WIDTH) for c in (text or '')) * font_size / 1000.0
