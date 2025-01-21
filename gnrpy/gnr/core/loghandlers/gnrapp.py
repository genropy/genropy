import os

from gnr.core.loghandlers.queuehandler import GnrQueueLoggingHandler
from gnr.app.gnrapp import GnrApp

__all__ = ['GnrAppLoggingHandler']

class GnrAppLoggingHandler(GnrBaseLoggingHandler):
    def initialize(self):
        self.gnrapp = GnrApp(self.settings.get("gnrapp_name"))
        self.table_name = self.settings.get("table_name")

    def _process_record(self, log_entry):
        try:
            user = os.environ.get("USER", "NA")
            to_record = log_entry.__dict__
            to_record['username'] = user
            self.gnrapp.db.table(self.table_name).insert(to_record)
            self.gnrapp.db.commit()
        except Exception as e:
            print(f"Error writing log to database: {e}")
