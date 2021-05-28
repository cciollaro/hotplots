import logging
import time

from hotplots import Hotplots
from hotplots_config import HotplotsConfig
from hotplots_logging import HotplotsLogging

if __name__ == '__main__':
    config = HotplotsConfig("config.yaml")
    HotplotsLogging.initialize_logging(config.logging_config())

    hotplots = Hotplots(config)

    while True:
        try:
            hotplots.run()
        except Exception:
            logging.exception("error while running hotplots")

        logging.info("sleeping %s seconds" % config.sleep())
        time.sleep(config.sleep())
