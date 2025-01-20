import platform
import logging

class ColouredFormatter(logging.Formatter):
    """
    A formatter for the python :mod:`logging` module
    that colors the log messages depending on their severity"""

    COLORS = {
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
        log_msg = super().format(record)
        if self.use_colour and record.levelno in self.COLORS:
            # Apply color based on the log level
            color = self.COLORS.get(record.levelno, self.RESET)
            return f"{color}{log_msg}{self.RESET}"
        else:
            return f"{log_msg}"
        

class GnrColourStreamHandler(logging.StreamHandler):
    def __init__(self, stream):
        super().__init__(stream)
        if hasattr(self.stream, 'isatty') and self.stream.isatty():
            self.setFormatter(
                ColouredFormatter(
                    fmt="%(asctime)s: %(levelname)s: %(name)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S"
                )
            )
                

        
