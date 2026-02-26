#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""gnrgit - Git repository wrapper using dulwich.

This module provides a wrapper class for interacting with Git repositories
using the dulwich library. It supports both HTTP and SSH remote connections.

Warning:
    Skipping testing and coverage since this object assumes a local checked-out
    repository and access to an external one.
"""

from __future__ import annotations

from dulwich.client import HttpGitClient, SSHGitClient
from dulwich.repo import Repo


class GnrGit:  # pragma: no cover
    """Wrapper for Git repository operations using dulwich.

    Provides a simplified interface for working with local Git repositories
    and their remote origins.

    Args:
        repo_path: Path to the local Git repository.
        remote_origin: Name of the remote (e.g., 'origin').
        remote_user: Username for remote authentication.
        remote_password: Password for remote authentication.

    Raises:
        NotImplementedError: If the remote URL schema is not HTTP or SSH.

    Example:
        >>> git = GnrGit('/path/to/repo', remote_origin='origin')
        >>> git.get_refs('/path')
    """

    def __init__(
        self,
        repo_path: str,
        remote_origin: str | None = None,
        remote_user: str | None = None,
        remote_password: str | None = None,
    ) -> None:
        self.repo: Repo = Repo(repo_path)
        self.config = self.repo.get_config()
        self.remote_origin = remote_origin
        self.remote_user = remote_user
        self.remote_password = remote_password
        self.remote_url: str | None = None
        self.remote_client: HttpGitClient | SSHGitClient | None = None

        if self.remote_origin:
            remote_url_bytes = self.config.get(("remote", self.remote_origin), "url")
            self.remote_url = remote_url_bytes.decode("utf-8")
            if self.remote_url.startswith("http"):
                self.remote_client = HttpGitClient(
                    self.remote_url,
                    username=remote_user,
                    password=remote_password,
                )
            elif self.remote_url.startswith("git@"):
                # classic git+ssh url
                # ex. git@github.com:genropy/genropy.git
                user = self.remote_url.split("@")[0]
                hostname = self.remote_url.split(":")[0].split("@")[1]
                self.remote_client = SSHGitClient(host=hostname, username=user)
            else:
                # REVIEW:BUG — was `raise NotImplemented` (wrong: NotImplemented is a
                # singleton for rich comparisons, not an exception)
                raise NotImplementedError("GnrGit supports only http or ssh schemas")

    def get_refs(self, path: str) -> None:
        """Fetch references from the remote repository.

        Args:
            path: Path to fetch refs from.

        Note:
            Currently this method does not return the refs; the return value
            from ``remote_client.get_refs()`` is discarded.
        """
        # REVIEW:SMELL — return value is discarded; should this return the refs?
        self.remote_client.get_refs(path)  # type: ignore[union-attr]


__all__ = ["GnrGit"]
