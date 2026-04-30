import logging
from datetime import datetime
from typing import Dict, Any
import json
import os

# I created this logger to track idempotency-related events in my payment gateway.
# It helps me monitor requests, cache hits/misses, and conflicts for debugging.
class IdempotencyLogger:
    def __init__(self):
        # I start by setting up the log file in the project root directory.
        # This ensures logs are stored in a predictable location.
        self.project_root = os.getcwd()
        self.log_file = os.path.join(self.project_root, 'idempotency.log')

        # I configure the logger with a descriptive name and INFO level.
        # This captures all relevant events without being too verbose.
        self.logger = logging.getLogger('idempotency-gateway')
        self.logger.setLevel(logging.INFO)

        # I clear any existing handlers to avoid duplicate logs.
        # This prevents issues if the logger is initialized multiple times.
        self.logger.handlers.clear()

        # I set up a file handler to write logs to disk.
        # The 'a' mode appends logs to the file instead of overwriting it.
        file_handler = logging.FileHandler(self.log_file, mode='a')
        file_handler.setLevel(logging.INFO)

        # I also add a console handler to print logs to the terminal.
        # This helps me monitor the system in real-time during development.
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # I define a consistent format for all logs, including timestamps and log levels.
        # This makes it easier to read and parse the logs later.
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # I attach both handlers to the logger.
        # Now logs will go to both the file and the console.
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # I verify that the log file was created successfully.
        # If not, I try to create it manually.
        if os.path.exists(self.log_file):
            self.logger.info(f"Log file ready: {self.log_file}")
        else:
            try:
                with open(self.log_file, 'w') as f:
                    f.write("")  # I create an empty file to start fresh.
                self.logger.info(f"Log file created: {self.log_file}")
            except Exception as e:
                print(f"Could not create log file: {e}")

    def log_request(self, idempotency_key: str, request_body: dict, cache_status: str):
        # I log every incoming request with its idempotency key, body, and cache status.
        # This helps me track whether requests are being processed or served from cache.
        log_entry = {
            "event": "request_received",
            "idempotency_key": idempotency_key,
            "request_body": request_body,
            "cache_status": cache_status,
            "timestamp": datetime.now().isoformat()
        }
        self.logger.info(json.dumps(log_entry))

    def log_cache_hit(self, idempotency_key: str):
        # I log cache hits to monitor how often requests are served from cache.
        # A high number of hits means the idempotency system is working well.
        log_entry = {
            "event": "cache_hit",
            "idempotency_key": idempotency_key,
            "timestamp": datetime.now().isoformat()
        }
        self.logger.info(json.dumps(log_entry))

    def log_cache_miss(self, idempotency_key: str):
        # I log cache misses to track when a request is processed for the first time.
        # This helps me understand how many unique payments are being made.
        log_entry = {
            "event": "cache_miss",
            "idempotency_key": idempotency_key,
            "timestamp": datetime.now().isoformat()
        }
        self.logger.info(json.dumps(log_entry))

    def log_conflict(self, idempotency_key: str, old_body: dict, new_body: dict):
        # I log conflicts when someone tries to reuse an idempotency key with a different request.
        # This is a security measure to prevent accidental or malicious double-charging.
        log_entry = {
            "event": "conflict_detected",
            "idempotency_key": idempotency_key,
            "original_request": old_body,
            "conflicting_request": new_body,
            "timestamp": datetime.now().isoformat()
        }
        self.logger.warning(json.dumps(log_entry))

    def get_stats(self):
        # I calculate statistics from the log file to monitor system performance.
        # This gives me insights into cache efficiency and potential issues.
        stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "conflicts": 0
        }

        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    for line in f:
                        try:
                            # I parse each log line to extract the event type.
                            # The JSON data is usually at the end of the line.
                            if ' - ' in line:
                                parts = line.split(' - ')
                                json_part = parts[-1]
                                log_entry = json.loads(json_part)
                            else:
                                log_entry = json.loads(line)

                            # I update the stats based on the event type.
                            event = log_entry.get("event")
                            if event == "request_received":
                                stats["total_requests"] += 1
                            elif event == "cache_hit":
                                stats["cache_hits"] += 1
                            elif event == "cache_miss":
                                stats["cache_misses"] += 1
                            elif event == "conflict_detected":
                                stats["conflicts"] += 1
                        except:
                            # I skip lines that can't be parsed to avoid crashes.
                            pass
        except Exception as e:
            print(f"Error reading log: {e}")

        return stats

# I create a global logger instance so it can be used across the entire application.
logger = IdempotencyLogger()
