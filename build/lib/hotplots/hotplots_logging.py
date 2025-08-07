import logging
import sys

from hotplots.hotplots_config import LoggingConfig


class HotplotsLogging:
    @staticmethod
    def initialize_logging(logging_config: LoggingConfig) -> None:
        logging.basicConfig(
            format="%(asctime)s;%(levelname)s;%(message)s",
            level=logging.getLevelName(logging_config.level),
            handlers=HotplotsLogging.handlers(logging_config)
        )

    @staticmethod
    def handlers(logging_config: LoggingConfig):
        handlers = []
        if logging_config.stdout.enabled:
            handlers.append(logging.StreamHandler(sys.stdout))

        if logging_config.file.enabled and logging_config.file.path:
            handlers.append(logging.FileHandler(logging_config.file.path, encoding="utf-8"))

        return handlers
