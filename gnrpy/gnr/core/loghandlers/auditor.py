import logging
from gnr.core.loghandlers.gnrcolour import ColouredFormatter

class GnrAuditorHandler(logging.StreamHandler):
    def __init__(self, stream=None):
        super().__init__(stream)
        if hasattr(self.stream, 'isatty') and self.stream.isatty():
            self.setFormatter(
                ColouredFormatter(
                    fmt="%(asctime)s: %(levelname)s: %(name)s.%(module)s - %(user)s executed: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S"
                )
            )
                

        
