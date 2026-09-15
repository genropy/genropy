"""Select the Bag implementation before importing framework consumers.

The instance switch is process-wide. A dedicated daemon and a full service
restart are required when changing it; live class replacement is unsupported.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


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
        root = ET.parse(environment).getroot()
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
        for root in roots:
            matches = sorted(root.glob(f"*/instances/{name}/instanceconfig.xml"))
            if len(matches) > 1:
                raise RuntimeError(
                    f"Ambiguous instance {name!r}; set GNR_INSTANCE_CONFIG explicitly"
                )
            if matches:
                return matches[0].resolve()
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


def configure_bag_mode():
    """Activate only when the resolved instance explicitly opts in."""
    path = _config_path()
    implementation = bag_implementation(path)
    if path is not None:
        # Children and dedicated daemon workers resolve the same instance.
        os.environ["GNR_INSTANCE_CONFIG"] = str(path)
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
