import logging
import socket
import threading
import queue

class GnrNetPortLoggingHandler(logging.Handler):
    def __init__(self, host='0.0.0.0', port=5000):
        super().__init__()
        self.host = host
        self.port = int(port)
        self.client_socket = None
        self.server_socket = None
        self.running = True
        self.queue = queue.Queue()

        # Start a background thread to handle connections
        self.server_thread = threading.Thread(target=self._start_server, daemon=True)
        self.server_thread.start()

        # Start a background thread to send logs
        self.sender_thread = threading.Thread(target=self._send_logs, daemon=True)
        self.sender_thread.start()

    def _start_server(self):
        """Starts the TCP server and waits for a client to connect."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        print(f"Logging server started on {self.host}:{self.port}")

        while self.running:
            try:
                client, addr = self.server_socket.accept()
                print(f"Client {addr} connected for logging.")
                self.client_socket = client
            except socket.error:
                break

    def _send_logs(self):
        """Continuously sends logs to the connected client."""
        while self.running:
            if self.client_socket:
                try:
                    log_entry = self.queue.get()
                    self.client_socket.sendall((log_entry + "\n").encode("utf-8"))
                except (BrokenPipeError, ConnectionResetError):
                    print("Client disconnected, waiting for new connection...")
                    self.client_socket = None

    def emit(self, record):
        """Formats and queues a log record for sending."""
        log_entry = self.format(record)
        self.queue.put(log_entry)

    def close(self):
        """Cleans up resources when the handler is closed."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        if self.client_socket:
            self.client_socket.close()
        super().close()

# Example Usage
if __name__ == "__main__":
    logger = logging.getLogger("GnrNetPortLogger")
    logger.setLevel(logging.DEBUG)

    tcp_handler = GnrNetPortLoggingHandler(host="0.0.0.0", port=5000)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    tcp_handler.setFormatter(formatter)

    logger.addHandler(tcp_handler)

    # Generate logs
    import time
    counter = 0
    try:
        while True:
            logger.info(f"This is a test log message #{counter}")
            time.sleep(1)
            counter += 1
    except KeyboardInterrupt:
        tcp_handler.close()
