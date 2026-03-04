# -*- coding: utf-8 -*-
from gnr.core.cli import GnrCliArgParse

description = "Testing log infrastructure"



def main():
    p = GnrCliArgParse(
        description=description
    )
    p.add_argument("-l", "--logger", dest="logger_name",
                       default="gnr.dev",
                       help='The logger name to test')
    
    options = p.parse_args()

    levels = [
        "debug",
        "info",
        "warning",
        "error",
        "exception",
        "critical",
    ]
    import logging
    logger = logging.getLogger(options.logger_name)

    for l in levels:
        getattr(logger, l)(f"This is a {l} level message")

    try:
        raise Exception("This is a text exception")
    except Exception as e:
        logger.exception("Something wrong happened")
