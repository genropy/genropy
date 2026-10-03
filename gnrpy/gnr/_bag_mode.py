"""Select the Bag implementation before importing framework consumers.

The instance switch is process-wide. A dedicated daemon and a full service
restart are required when changing it; live class replacement is unsupported.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

# Reloading configuration code must not reopen process-wide selection.
_selected_implementation = globals().get('_selected_implementation')


def selected_bag_mode():
    """Return the process selection, independently of the public gnr.BAG_MODE label."""
    return _selected_implementation


def assert_legacy_bag_allowed():
    """Guard direct file loads as well as ordinary imports of the legacy module."""
    if selected_bag_mode() != "legacy":
        raise ImportError(
            "Historical gnrbag.py is disabled in genro-bag mode; "
            "import classes from the genro-bag gnr.core.gnrbag facade"
        )


def _config_path():
    explicit = os.environ.get("GNR_INSTANCE_CONFIG")
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise RuntimeError(f"Instance configuration does not exist: {path}")
        return path

    roots = []
    local = os.environ.get("GNR_LOCAL_PROJECTS")
    if local:
        roots.append(Path(local).expanduser())
    folder = Path(os.environ.get("GENRO_GNRFOLDER", "~/.gnr")).expanduser()
    environment = folder / "environment.xml"
    if environment.is_file():
        try:
            root = ET.parse(environment).getroot()
        except (ET.ParseError, OSError):
            # Opportunistic discovery must not validate legacy configuration.
            root = ET.Element("environment")
        for entry in root.findall("./projects/*"):
            path = entry.get("path")
            if path:
                roots.append(Path(os.path.expandvars(path)).expanduser())

    names = [os.environ.get("GNR_CURRENT_SITE", ""), *sys.argv[1:]]
    script_config = Path(sys.argv[0]).expanduser().parent / "instanceconfig.xml"
    if script_config.is_file():
        return script_config.resolve()
    for name in names:
        if not name or name.startswith("-") or "/" in name or "\\" in name:
            continue
        name = name.split(":", 1)[0]
        matches = sorted({path.resolve() for root in roots
                          for path in root.glob(f"*/instances/{name}/instanceconfig.xml")})
        if len(matches) > 1:
            if any(_discovered_implementation(path) != "legacy" for path in matches):
                raise RuntimeError(
                    f"Ambiguous instance {name!r}; set GNR_INSTANCE_CONFIG explicitly"
                )
            # No native opt-in: leave instance resolution to the normal startup.
            return None
        if matches:
            return matches[0]
    return None


def bag_implementation(path):
    """Read experimental/bag@implementation before importing Bag classes."""
    if path is None:
        return "legacy"
    node = ET.parse(path).getroot().find("./experimental/bag")
    if node is None:
        return "legacy"
    if "native" in node.attrib:
        raise ValueError(
            'Replace experimental/bag@native with implementation="genro-bag" '
            'or implementation="legacy"'
        )
    value = node.get("implementation", "legacy").strip()
    if value.endswith("::T"):
        value = value[:-3]
    if value not in {"legacy", "genro-bag"}:
        raise ValueError(f"Invalid experimental/bag implementation: {value!r}")
    return value


def _discovered_implementation(path):
    """Defer unreadable implicit configuration to the regular startup loader."""
    try:
        return bag_implementation(path)
    except (ET.ParseError, OSError):
        return "legacy"


def configure_bag_mode():
    """Activate only when the resolved instance explicitly opts in."""
    global _selected_implementation
    if _selected_implementation is not None:
        return _selected_implementation
    path = _config_path()
    implementation = (bag_implementation(path) if os.environ.get("GNR_INSTANCE_CONFIG")
                      else _discovered_implementation(path))
    if path is not None and implementation == "genro-bag":
        # Children and dedicated daemon workers resolve the same instance.
        os.environ["GNR_INSTANCE_CONFIG"] = str(path)
    _selected_implementation = implementation
    if implementation == "genro-bag":
        from gnr.core.nativebag import activate

        try:
            activate()
        except ModuleNotFoundError as error:
            if error.name == "genro_bag":
                raise ImportError(
                    'Bag implementation "genro-bag" requires genropy[genro-bag]; '
                    'install the compatible genro-bag package before starting'
                ) from error
            raise
    return implementation
