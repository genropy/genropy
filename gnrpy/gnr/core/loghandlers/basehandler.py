import logging
import queue

class GnrBaseLoggingHandler(logging.Handler):
    """
    Base class for thread-based logging handler, don't use this handler directly.
    """

    def __init__(self, **settings):
        queue_size = settings.get("queue_size", 1000)
        self.settings = settings
        self.queue = queue.Queue(queue_size)

        self.initialize()
        
        self.worker_thread = threading.Thread(target=self._process_logs, daemon=True)
        self._stop_event = threading.Event()
        self.worker_thread.start()

    def initialize(self):
        '''
        custom initialization to be overridden, before the worker thread starts
        '''
        pass

    def shutdown(self):
        '''
        custom shutdown to be overridden, before the process ends
        '''
        pass
    
    def emit(self, record):
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            print("Log queue is full; dropping log entry.")

    def _process_logs(self):
        while not self._stop_event.is_set():
            try:
                log_entry = self.queue.get(timeout=1)  # Wait for a log entry
                if log_entry is not None:
                    self._process_record(log_entry)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing log entry: {e}")

    def _process_record(self, log_entry):
        raise NotImplementedError("Please don't use GnrBaseLoggingHandler directly!")

    def close(self):
        self._stop_event.set()
        self.worker_thread.join()
        self.shutdown()
        super().close()
