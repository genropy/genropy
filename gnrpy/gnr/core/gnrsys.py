# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrsys : OS and filesystem utilities
# Copyright (c) : 2004 - 2007 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari, Francesco Cavazzana
# --------------------------------------------------------------------------
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
"""gnrsys - OS and filesystem utilities.

This module provides utility functions for interacting with the operating
system and filesystem, including path manipulation, directory creation,
and progress display.

Functions:
    progress: Display a progress bar in the terminal.
    mkdir: Create a directory with specific permissions.
    expandpath: Expand ~ and environment variables in a path.
    listdirs: List all files in a directory tree.
    resolvegenropypath: Resolve paths across different Genro installations.
"""

from __future__ import annotations

import os
import sys
from typing import TextIO


def progress(
    count: int,
    total: int,
    status: str = "",
    fd: TextIO = sys.stdout,
) -> None:
    """Display a progress bar in the terminal.

    Args:
        count: Current progress count.
        total: Total count for 100% completion.
        status: Optional status message to display.
        fd: File descriptor to write to. Defaults to stdout.

    Example:
        >>> for i in range(100):
        ...     progress(i + 1, 100, status='Processing...')
    """
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = "=" * filled_len + "-" * (bar_len - filled_len)

    fd.write("[%s] %s%s ...%s\r" % (bar, percents, "%", status))
    fd.flush()


def mkdir(path: str, privileges: int = 0o777) -> None:
    """Create a directory with the specified permissions.

    Creates the directory and all parent directories as needed.
    Explicitly sets permissions with chmod since some systems
    ignore the mode parameter to os.mkdir.

    Args:
        path: The directory path to create.
        privileges: Numeric permission mode. Defaults to 0o777.
            The current umask is masked out by the system.

    Example:
        >>> mkdir('/tmp/my/nested/directory', 0o755)
    """
    if path and not os.path.isdir(path):
        head, tail = os.path.split(path)

        mkdir(head, privileges)
        # on some systems, privileges are ignored, needs explicit call
        os.chmod(head, privileges)

        os.mkdir(path, privileges)
        # on some systems, privileges are ignored, needs explicit call
        os.chmod(path, privileges)


def expandpath(path: str, full: bool = False) -> str:
    """Expand user home directory (~) and environment variables in a path.

    Args:
        path: The path to expand.
        full: If True, also normalize and resolve to absolute path.

    Returns:
        The expanded path string.

    Example:
        >>> expandpath('~/Documents/$PROJECT/data')
        '/home/user/Documents/myproject/data'
        >>> expandpath('~/relative/../path', full=True)
        '/home/user/path'
    """
    path = os.path.expanduser(os.path.expandvars(path))
    if full:
        path = os.path.realpath(os.path.normpath(path))
    return path


def listdirs(path: str, invisible_files: bool = False) -> list[str]:
    """List all files in a directory tree recursively.

    Args:
        path: The root directory path to traverse.
        invisible_files: If True, include files starting with '.'.
            Defaults to False.

    Returns:
        A list of absolute file paths.

    Note:
        This function uses os.walk incorrectly (passes a callback
        that won't be used). Consider using os.walk directly.
    """
    # REVIEW:BUG — os.walk doesn't accept a callback; this function
    # doesn't work as intended. The callback is never called.

    def callb(files: list[str], top: str, names: list[str]) -> None:
        for name in names:
            file_path = os.path.realpath(os.path.join(top, name))
            if (invisible_files or not name.startswith(".")) and os.path.isfile(
                file_path
            ):
                files.append(file_path)

    files: list[str] = []
    os.walk(path, callb, files)  # type: ignore[call-arg]
    return files


def resolvegenropypath(path: str) -> str | None:
    """Resolve a path across different Genro installations.

    Attempts to find a valid path by checking multiple locations:
    1. Expand ~ if path starts with it
    2. Check absolute paths directly
    3. Try prepending ~ to absolute paths
    4. Try prepending ~/ to relative paths

    Args:
        path: The path to resolve.

    Returns:
        The resolved path if found, None if no valid path exists.

    Note:
        Added by Jeff. Useful for resolving document paths between
        different Genro installations where it may be installed in
        user path or at root.
    """
    if path.find("~") == 0:
        path = expandpath(path)
        if os.path.exists(path):
            return path

    if path.find("/") == 0:
        if os.path.exists(path):
            return path
        else:  # try making it into a user directory path
            path = "%s%s" % ("~", path)
            path = expandpath(path)
            if os.path.exists(path):
                return path
    else:
        if os.path.exists(path):
            return path
        else:
            path = "%s%s" % ("~/", path)
            path = expandpath(path)
            if os.path.exists(path):
                return path

    return None


__all__ = ["progress", "mkdir", "expandpath", "listdirs", "resolvegenropypath"]
