import logging
import sys

class HotplotsLogging:
    @staticmethod
    def initialize_logging(logging_config):
        logging.basicConfig(
            handlers=HotplotsLogging.handlers(logging_config),
            level=HotplotsLogging.log_level(logging_config)
        )

    @staticmethod
    def handlers(logging_config):
        handlers = []
        if logging_config["stdout"]:
            handlers.append(logging.StreamHandler(sys.stdout))

        if logging_config["file"]["enabled"] and logging_config["file"]["path"]:
            handlers.append(logging.FileHandler(logging_config["file"]["path"]))

        return handlers

    @staticmethod
    def log_level(logging_config):
        log_level = logging_config["level"]

        if log_level == "CRITICAL":
            return logging.CRITICAL
        if log_level == "ERROR":
            return logging.ERROR
        if log_level == "WARNING":
            return logging.WARNING
        if log_level == "INFO":
            return logging.INFO
        if log_level == "DEBUG":
            return logging.DEBUG

        logging.warning(f"Unsupported log level: {log_level}. Fallback to INFO level.")
        return logging.INFO
