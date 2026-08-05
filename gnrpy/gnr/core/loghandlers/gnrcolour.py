import platform
import logging
import os.path

class ColouredFormatter(logging.Formatter):
    """
    A formatter for the python :mod:`logging` module
    that colors the log messages depending on their severity"""
    COLOURS = {
        logging.DEBUG: "\033[94m",    # Blue
        logging.INFO: "\033[92m",     # Green
        logging.WARNING: "\033[93m",  # Yellow
        logging.ERROR: "\033[91m",    # Red
        logging.CRITICAL: "\033[95m", # Magenta
    }

    RESET = "\033[0m"  # Reset color

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.use_colour = platform.system() in ['Linux', 'Darwin']
        
    def format(self, record):
        splitter = f"{os.path.sep}packages{os.path.sep}"
        if splitter in record.pathname:
            record.module = record.pathname.split(splitter)[-1]

        log_msg = super().format(record)
        if self.use_colour and record.levelno in self.COLOURS:
            # Apply color based on the log level
            color = self.COLOURS.get(record.levelno, self.RESET)
            return f"{color}{log_msg}{self.RESET}"
        else:
            return f"{log_msg}"
        

class GnrColourStreamHandler(logging.StreamHandler):
    _fmt = "%(asctime)s: %(levelname)s: %(name)s/%(module)s - %(message)s"
    def __init__(self, stream=None):
        super().__init__(stream)
        if hasattr(self.stream, 'isatty') and self.stream.isatty():
            self.setFormatter(
                ColouredFormatter(
                    fmt=self._fmt,
                    datefmt="%Y-%m-%d %H:%M:%S"
                )
            )
        else:
            self.setFormatter(
                logging.Formatter(
                    self._fmt,
                    datefmt="%Y-%m-%d %H:%M:%S"
                )
            )

class GnrInstanceColourStreamHandler(GnrColourStreamHandler):
    def __init__(self, stream=None, instance_name=None):
        self.instance_name = instance_name
        self._fmt = f"%(asctime)s: {self.instance_name} - %(levelname)s: %(name)s/%(module)s - %(message)s"
        super().__init__(stream)



        
