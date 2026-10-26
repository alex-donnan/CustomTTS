import os
import sys
import logging
logger = logging.getLogger(__name__)

def setup_logging():
    """Initializes global logging. Call this once at the very start of main.py."""
    # Determine the directory of the actual .exe file
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.abspath(__file__))

    log_file_path = os.path.join(exe_dir, "app_runtime.log")

    # Configure the root logger
    logging.basicConfig(
        filename=log_file_path,
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
        filemode="a"
    )

    # Route all unhandled script crashes to the log file
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.critical("Uncaught exception occurred:", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception
