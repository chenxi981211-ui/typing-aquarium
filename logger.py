# this is the logged.py file

import sys
import traceback
import logging
from datetime import datetime
from pathlib import Path


class TypingAquariumLogger:
    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')

        self.setup_logging()

        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def setup_logging(self):
        log_file = self.log_dir / f"aquarium_{self.session_id}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

        sys.excepthook = self.global_exception_handler

    def global_exception_handler(self, exc_type, exc_value, exc_traceback):
        logging.critical("Unhandled exception:", exc_info=(exc_type, exc_value, exc_traceback))

        crash_file = self.log_dir / f"crash_{self.session_id}.txt"
        with open(crash_file, 'w') as f:
            f.write(f"Crash Report - {datetime.now()}\n")
            f.write("=" * 50 + "\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
            f.write("\n" + "=" * 50 + "\n")
            f.write(f"Session ID: {self.session_id}\n")

        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    def start(self):
        self.stdout_log = self.log_dir / f"stdout_{self.session_id}.log"
        self.stderr_log = self.log_dir / f"stderr_{self.session_id}.log"

        sys.stdout = self.TeeStream(self.original_stdout, self.stdout_log, 'stdout')
        sys.stderr = self.TeeStream(self.original_stderr, self.stderr_log, 'stderr')

        logging.info(f"=== Typing Aquarium Session Started ===")
        logging.info(f"Session ID: {self.session_id}")
        logging.info(f"Python version: {sys.version}")

    class TeeStream:
        def __init__(self, original_stream, log_file, name):
            self.original = original_stream
            self.log_file = open(log_file, 'a', encoding='utf-8')
            self.name = name

        def write(self, message):
            self.original.write(message)
            self.log_file.write(message)
            self.log_file.flush()

        def flush(self):
            self.original.flush()
            self.log_file.flush()

    def stop(self):
        logging.info("=== Typing Aquarium Session Ended ===")

        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

        print(f"\n📁 Log files saved in '{self.log_dir}' directory")


logger = TypingAquariumLogger()