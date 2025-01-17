# -*- coding: utf-8 -*-
from gnr.core.cli import GnrCliArgParse

description = "Testing log infrastructure"



def main():
    p = GnrCliArgParse(
        description=description
    )
    options = p.parse_args()

    levels = [
        "critical",
        "debug",
        "error",
        "info",
        "warning"
    ]

    from gnr.dev import logger

    for l in levels:
        getattr(logger, l)(f"This is a {l} level message")
